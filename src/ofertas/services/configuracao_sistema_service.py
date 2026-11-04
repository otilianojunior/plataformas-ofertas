from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.models.execucao_coleta import ExecucaoColeta
from ofertas.repositories.configuracao_sistema_repository import (
    ConfiguracaoSistemaRepository,
)


class ConfiguracaoSistemaService:
    TEMPO_LIMITE_AGENDADOR_MINUTOS = 3

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

    def iniciar_coleta_automatica(
        self,
        session: Session,
    ) -> ConfiguracaoSistema:
        configuracao = self.buscar(session)

        return self.repository.atualizar_status_coleta(
            session,
            configuracao,
            True,
        )

    def pausar_coleta_automatica(
        self,
        session: Session,
    ) -> ConfiguracaoSistema:
        configuracao = self.buscar(session)

        return self.repository.atualizar_status_coleta(
            session,
            configuracao,
            False,
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

        ultima_execucao = session.scalar(
            select(ExecucaoColeta)
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

        if not configuracao.coleta_automatica_ativa:
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
            "coleta_automatica_ativa": (
                configuracao.coleta_automatica_ativa
            ),
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
