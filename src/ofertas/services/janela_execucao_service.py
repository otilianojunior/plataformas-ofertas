from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ofertas.models.janela_execucao import JanelaExecucao
from ofertas.repositories.janela_execucao_repository import (
    JanelaExecucaoRepository,
)


FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")


class JanelaExecucaoService:
    """Gerencia as janelas diárias permitidas para as automações."""

    def __init__(
        self,
        repository: JanelaExecucaoRepository | None = None,
    ) -> None:
        self.repository = repository or JanelaExecucaoRepository()

    def listar(self, session: Session) -> list[JanelaExecucao]:
        return self.repository.listar(session)

    def buscar(
        self,
        session: Session,
        janela_id: int,
    ) -> JanelaExecucao:
        janela = self.repository.buscar(session, janela_id)

        if janela is None:
            raise LookupError("Janela de execução não encontrada.")

        return janela

    @staticmethod
    def _validar_intervalo(
        hora_inicio: time,
        hora_fim: time,
    ) -> None:
        if hora_inicio >= hora_fim:
            raise ValueError(
                "O horário de início deve ser anterior ao horário de fim. "
                "Janelas que atravessam a meia-noite não são permitidas."
            )

    def criar(
        self,
        session: Session,
        hora_inicio: time,
        hora_fim: time,
        ativa: bool = True,
    ) -> JanelaExecucao:
        self._validar_intervalo(hora_inicio, hora_fim)

        self.repository.bloquear_alteracoes(session)

        if ativa and self.repository.existe_conflito(
            session,
            hora_inicio,
            hora_fim,
        ):
            raise ValueError(
                "A janela informada se sobrepõe a outra janela ativa."
            )

        return self.repository.criar(
            session,
            hora_inicio,
            hora_fim,
            ativa,
        )

    def atualizar(
        self,
        session: Session,
        janela_id: int,
        dados: dict,
    ) -> JanelaExecucao:
        self.repository.bloquear_alteracoes(session)
        janela = self.buscar(session, janela_id)

        hora_inicio = dados.get("hora_inicio", janela.hora_inicio)
        hora_fim = dados.get("hora_fim", janela.hora_fim)
        ativa = dados.get("ativa", janela.ativa)

        self._validar_intervalo(hora_inicio, hora_fim)

        if ativa and self.repository.existe_conflito(
            session,
            hora_inicio,
            hora_fim,
            ignorar_id=janela.id,
        ):
            raise ValueError(
                "A alteração se sobrepõe a outra janela ativa."
            )

        return self.repository.atualizar(
            session,
            janela,
            dados,
        )

    def excluir(
        self,
        session: Session,
        janela_id: int,
    ) -> None:
        self.repository.bloquear_alteracoes(session)
        janela = self.buscar(session, janela_id)
        self.repository.excluir(session, janela)

    def esta_em_horario_permitido(
        self,
        session: Session,
        agora: datetime | None = None,
    ) -> bool:
        """Verifica se o horário atual está dentro de uma janela ativa.

        Sem janelas ativas, a execução fica liberada durante 24 horas.
        O horário é interpretado no fuso America/Sao_Paulo.
        """

        janelas = self.repository.listar_ativas(session)

        if not janelas:
            return True

        horario_local = (
            agora.astimezone(FUSO_HORARIO)
            if agora is not None
            else datetime.now(FUSO_HORARIO)
        ).time().replace(tzinfo=None)

        return any(
            janela.hora_inicio <= horario_local < janela.hora_fim
            for janela in janelas
        )
