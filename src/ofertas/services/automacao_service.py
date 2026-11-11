import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.db.session import SessionLocal
from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.models.execucao_coleta import ExecucaoColeta
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.repositories.configuracao_divulgacao_repository import (
    ConfiguracaoDivulgacaoRepository,
)
from ofertas.repositories.destino_divulgacao_repository import (
    DestinoDivulgacaoRepository,
)
from ofertas.services.configuracao_sistema_service import (
    ConfiguracaoSistemaService,
)
from ofertas.services.execucao_coleta_service import ExecucaoColetaService


logger = logging.getLogger(__name__)


class AutomacaoService:
    """Coordena as automações executadas dentro da API."""

    CODIGO_MERCADO_LIVRE = "mercado_livre"
    CODIGO_TELEGRAM = "telegram"

    def __init__(
        self,
        configuracao_sistema_service: ConfiguracaoSistemaService | None = None,
        execucao_coleta_service: ExecucaoColetaService | None = None,
        configuracao_divulgacao_repository: ConfiguracaoDivulgacaoRepository | None = None,
        destino_repository: DestinoDivulgacaoRepository | None = None,
    ) -> None:
        self.configuracao_sistema_service = (
            configuracao_sistema_service or ConfiguracaoSistemaService()
        )
        self.execucao_coleta_service = (
            execucao_coleta_service or ExecucaoColetaService()
        )
        self.configuracao_divulgacao_repository = (
            configuracao_divulgacao_repository
            or ConfiguracaoDivulgacaoRepository()
        )
        self.destino_repository = (
            destino_repository or DestinoDivulgacaoRepository()
        )

    @staticmethod
    def _normalizar_horario(horario: datetime) -> datetime:
        if horario.tzinfo is None:
            return horario.replace(tzinfo=timezone.utc)
        return horario

    @classmethod
    def _intervalo_concluido(
        cls,
        ultima_execucao: datetime | None,
        intervalo_minutos: int,
        agora: datetime,
    ) -> bool:
        if ultima_execucao is None:
            return True

        referencia = cls._normalizar_horario(ultima_execucao)

        return agora >= referencia + timedelta(
            minutes=intervalo_minutos
        )

    def registrar_sinal(self) -> None:
        """Atualiza o sinal de vida mesmo quando as automações estão pausadas."""

        with SessionLocal() as session:
            try:
                self.configuracao_sistema_service.registrar_sinal(session)
                session.commit()
            except Exception:
                session.rollback()
                logger.exception(
                    "Erro ao atualizar o sinal de vida das automações."
                )

    def executar_coletas_liberadas(self) -> None:
        """Executa as coletas do Mercado Livre quando o intervalo vencer."""

        with SessionLocal() as session:
            try:
                configuracao = self.configuracao_sistema_service.buscar(
                    session
                )

                if not configuracao.automacoes_ativas or not configuracao.coleta_mercado_livre_ativa:
                    return

                intervalo_minutos = (
                    configuracao.intervalo_coleta_minutos
                )

                plataforma_ids = session.scalars(
                    select(Plataforma.id).where(
                        Plataforma.codigo == self.CODIGO_MERCADO_LIVRE,
                        Plataforma.status_plataforma.is_(True),
                    )
                ).all()

            except Exception:
                logger.exception(
                    "Erro ao consultar as plataformas para coleta."
                )
                return

        if not plataforma_ids:
            logger.warning(
                "Nenhuma plataforma Mercado Livre ativa para coleta."
            )
            return

        for plataforma_id in plataforma_ids:
            with SessionLocal() as session:
                try:
                    configuracao_atual = (
                        self.configuracao_sistema_service.buscar(session)
                    )

                    if not configuracao_atual.automacoes_ativas or not configuracao_atual.coleta_mercado_livre_ativa:
                        logger.info(
                            "Coleta do Mercado Livre pausada."
                        )
                        break

                    plataforma = session.get(
                        Plataforma,
                        plataforma_id,
                    )

                    if (
                        plataforma is None
                        or not plataforma.status_plataforma
                    ):
                        continue

                    ultima_execucao = session.scalar(
                        select(ExecucaoColeta)
                        .where(
                            ExecucaoColeta.plataforma_id == plataforma_id
                        )
                        .order_by(
                            ExecucaoColeta.iniciada_em.desc(),
                            ExecucaoColeta.id.desc(),
                        )
                        .limit(1)
                    )

                    if (
                        ultima_execucao is not None
                        and ultima_execucao.status == "em_andamento"
                    ):
                        continue

                    referencia = None

                    if ultima_execucao is not None:
                        referencia = (
                            ultima_execucao.finalizada_em
                            or ultima_execucao.iniciada_em
                        )

                    agora = datetime.now(timezone.utc)

                    if not self._intervalo_concluido(
                        referencia,
                        intervalo_minutos,
                        agora,
                    ):
                        continue

                    execucao = self.execucao_coleta_service.executar(
                        session,
                        plataforma_id,
                    )

                    session.commit()

                    self.execucao_coleta_service.gerar_afiliados_pendentes(
                        plataforma_id
                    )

                    logger.info(
                        "Coleta automática finalizada. "
                        "Execução: %s | Plataforma: %s | Status: %s | "
                        "Processados: %s | Ignorados: %s",
                        execucao.id,
                        plataforma_id,
                        execucao.status,
                        execucao.quantidade_processada,
                        execucao.quantidade_ignorada,
                    )

                except ValueError as erro:
                    session.rollback()
                    logger.info(
                        "Coleta da plataforma %s não iniciada: %s",
                        plataforma_id,
                        erro,
                    )

                except Exception:
                    session.rollback()
                    logger.exception(
                        "Erro na coleta automática da plataforma %s.",
                        plataforma_id,
                    )

    def listar_destinos_publicacao_liberados(self) -> list[int]:
        """Retorna os destinos Telegram cujo intervalo de ciclo venceu."""

        agora = datetime.now(timezone.utc)
        destinos_liberados = []

        with SessionLocal() as session:
            configuracao_sistema = (
                self.configuracao_sistema_service.buscar(session)
            )

            if not configuracao_sistema.automacoes_ativas or not configuracao_sistema.publicacao_telegram_ativa:
                return []

            configuracoes = (
                self.configuracao_divulgacao_repository.listar(session)
            )

            for configuracao in configuracoes:
                if not configuracao.status_configuracao:
                    continue

                destino = self.destino_repository.buscar_por_id(
                    session,
                    configuracao.destino_divulgacao_id,
                )

                if destino is None or not destino.status_destino:
                    continue

                plataforma_destino = session.get(
                    PlataformaDivulgacao,
                    destino.plataforma_divulgacao_id,
                )

                if (
                    plataforma_destino is None
                    or not plataforma_destino.status_plataforma
                    or plataforma_destino.codigo != self.CODIGO_TELEGRAM
                ):
                    continue

                if not self._intervalo_concluido(
                    configuracao.ultima_execucao_publicacao_em,
                    configuracao.intervalo_publicacao_minutos,
                    agora,
                ):
                    continue

                destinos_liberados.append(
                    configuracao.destino_divulgacao_id
                )

        return destinos_liberados
