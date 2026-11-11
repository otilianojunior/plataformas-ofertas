from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.models.execucao_coleta import ExecucaoColeta
from ofertas.models.plataforma import Plataforma
from ofertas.repositories.configuracao_sistema_repository import (
    ConfiguracaoSistemaRepository,
)


class ConfiguracaoSistemaService:
    TEMPO_LIMITE_AGENDADOR_MINUTOS = 3

    AUTOMACOES_VALIDAS = {
        "coleta_mercado_livre",
        "coleta_shopee",
        "publicacao_telegram",
        "publicacao_whatsapp",
    }

    def __init__(self) -> None:
        self.repository = ConfiguracaoSistemaRepository()

    def buscar(self, session: Session) -> ConfiguracaoSistema:
        configuracao = self.repository.buscar(session)

        if configuracao is None:
            raise LookupError(
                "Configuração global do sistema não encontrada."
            )

        return configuracao

    def atualizar(
        self,
        session: Session,
        intervalo_coleta_minutos: int,
    ) -> ConfiguracaoSistema:
        if intervalo_coleta_minutos <= 0:
            raise ValueError(
                "O intervalo de coleta deve ser maior que zero."
            )

        configuracao = self.buscar(session)

        return self.repository.atualizar(
            session,
            configuracao,
            intervalo_coleta_minutos,
        )

    def atualizar_status_automacao(
        self,
        session: Session,
        automacao: str,
        ativa: bool,
    ) -> ConfiguracaoSistema:
        """Atualiza o estado de uma automação específica."""

        if automacao not in self.AUTOMACOES_VALIDAS:
            raise ValueError("Automação não reconhecida.")

        configuracao = self.buscar(session)

        return self.repository.atualizar_status_automacao(
            session,
            configuracao,
            automacao,
            ativa,
        )

    def ativar_automacao(
        self,
        session: Session,
        automacao: str,
    ) -> ConfiguracaoSistema:
        return self.atualizar_status_automacao(
            session,
            automacao,
            True,
        )

    def pausar_automacao(
        self,
        session: Session,
        automacao: str,
    ) -> ConfiguracaoSistema:
        return self.atualizar_status_automacao(
            session,
            automacao,
            False,
        )

    def iniciar_coleta_automatica(
        self,
        session: Session,
    ) -> ConfiguracaoSistema:
        """Mantido temporariamente para compatibilidade com a API atual."""
        return self.ativar_automacao(
            session,
            "coleta_mercado_livre",
        )

    def pausar_coleta_automatica(
        self,
        session: Session,
    ) -> ConfiguracaoSistema:
        """Mantido temporariamente para compatibilidade com a API atual."""
        return self.pausar_automacao(
            session,
            "coleta_mercado_livre",
        )

    def registrar_sinal(
        self,
        session: Session,
    ) -> ConfiguracaoSistema:
        configuracao = self.buscar(session)

        return self.repository.registrar_sinal(
            session,
            configuracao,
            datetime.now(timezone.utc),
        )

    def consultar_status_coleta(
        self,
        session: Session,
    ) -> dict:
        configuracao = self.buscar(session)

        agora = datetime.now(timezone.utc)
        ultimo_sinal = configuracao.agendador_ultimo_sinal_em

        agendador_online = (
            ultimo_sinal is not None
            and agora - ultimo_sinal
            <= timedelta(
                minutes=self.TEMPO_LIMITE_AGENDADOR_MINUTOS
            )
        )

        plataforma_mercado_livre = session.scalar(
            select(Plataforma).where(
                Plataforma.codigo == "mercado_livre"
            )
        )

        ultima_execucao = None

        if (
            plataforma_mercado_livre is not None
            and plataforma_mercado_livre.status_plataforma
        ):
            ultima_execucao = session.scalar(
                select(ExecucaoColeta)
                .where(
                    ExecucaoColeta.plataforma_id
                    == plataforma_mercado_livre.id
                )
                .order_by(
                    ExecucaoColeta.iniciada_em.desc(),
                    ExecucaoColeta.id.desc(),
                )
                .limit(1)
            )

        proxima_execucao = None

        if ultima_execucao is None:
            if agendador_online:
                proxima_execucao = agora

        elif ultima_execucao.status != "em_andamento":
            referencia = (
                ultima_execucao.finalizada_em
                or ultima_execucao.iniciada_em
            )

            proxima_execucao = referencia + timedelta(
                minutes=configuracao.intervalo_coleta_minutos
            )

        if (
            plataforma_mercado_livre is None
            or not plataforma_mercado_livre.status_plataforma
            or not configuracao.automacoes_ativas
            or not configuracao.coleta_mercado_livre_ativa
        ):
            status_coleta = "pausada"
            proxima_execucao = None

        elif (
            ultima_execucao is not None
            and ultima_execucao.status == "em_andamento"
        ):
            status_coleta = "executando"

        elif (
            ultima_execucao is not None
            and ultima_execucao.status == "falhou"
        ):
            status_coleta = "falhou"

        else:
            status_coleta = "aguardando_execucao"

        if not agendador_online:
            proxima_execucao = None

        return {
            "status_agendador": (
                "online" if agendador_online else "offline"
            ),
            "status_coleta": status_coleta,
            "coleta_mercado_livre_ativa": (
                configuracao.coleta_mercado_livre_ativa
            ),
            "automacoes_ativas": configuracao.automacoes_ativas,
            "agendador_ultimo_sinal_em": ultimo_sinal,
            "ultima_execucao_id": (
                ultima_execucao.id
                if ultima_execucao is not None
                else None
            ),
            "ultima_execucao_status": (
                ultima_execucao.status
                if ultima_execucao is not None
                else None
            ),
            "ultima_execucao_iniciada_em": (
                ultima_execucao.iniciada_em
                if ultima_execucao is not None
                else None
            ),
            "ultima_execucao_finalizada_em": (
                ultima_execucao.finalizada_em
                if ultima_execucao is not None
                else None
            ),
            "proxima_execucao_em": proxima_execucao,
        }

    def atualizar_status_geral(
        self,
        session: Session,
        ativa: bool,
    ) -> ConfiguracaoSistema:
        """Ativa ou pausa globalmente as automações."""

        configuracao = self.buscar(session)

        return self.repository.atualizar_status_geral(
            session,
            configuracao,
            ativa,
        )

    def ativar_automacoes(self, session: Session) -> ConfiguracaoSistema:
        return self.atualizar_status_geral(session, True)

    def pausar_automacoes(self, session: Session) -> ConfiguracaoSistema:
        return self.atualizar_status_geral(session, False)
