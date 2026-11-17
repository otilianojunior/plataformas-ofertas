from datetime import time

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ofertas.models.janela_execucao import JanelaExecucao


class JanelaExecucaoRepository:
    """Acesso às janelas diárias permitidas para as automações."""

    LOCK_NAMESPACE = 20261117
    LOCK_RECURSO = 1

    def bloquear_alteracoes(self, session: Session) -> None:
        """Serializa alterações para validar conflitos sem condições de corrida."""
        session.execute(
            text(
                "SELECT pg_advisory_xact_lock(:namespace, :recurso)"
            ),
            {
                "namespace": self.LOCK_NAMESPACE,
                "recurso": self.LOCK_RECURSO,
            },
        )

    def listar(self, session: Session) -> list[JanelaExecucao]:
        return list(
            session.scalars(
                select(JanelaExecucao).order_by(
                    JanelaExecucao.hora_inicio,
                    JanelaExecucao.id,
                )
            ).all()
        )

    def listar_ativas(self, session: Session) -> list[JanelaExecucao]:
        return list(
            session.scalars(
                select(JanelaExecucao)
                .where(JanelaExecucao.ativa.is_(True))
                .order_by(JanelaExecucao.hora_inicio)
            ).all()
        )

    def buscar(
        self,
        session: Session,
        janela_id: int,
    ) -> JanelaExecucao | None:
        return session.get(JanelaExecucao, janela_id)

    def existe_conflito(
        self,
        session: Session,
        hora_inicio: time,
        hora_fim: time,
        ignorar_id: int | None = None,
    ) -> bool:
        consulta = select(JanelaExecucao.id).where(
            JanelaExecucao.ativa.is_(True),
            JanelaExecucao.hora_inicio < hora_fim,
            JanelaExecucao.hora_fim > hora_inicio,
        )

        if ignorar_id is not None:
            consulta = consulta.where(
                JanelaExecucao.id != ignorar_id
            )

        return session.scalar(consulta.limit(1)) is not None

    def criar(
        self,
        session: Session,
        hora_inicio: time,
        hora_fim: time,
        ativa: bool,
    ) -> JanelaExecucao:
        janela = JanelaExecucao(
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            ativa=ativa,
        )
        session.add(janela)
        session.flush()
        return janela

    def atualizar(
        self,
        session: Session,
        janela: JanelaExecucao,
        dados: dict,
    ) -> JanelaExecucao:
        for campo, valor in dados.items():
            setattr(janela, campo, valor)

        session.flush()
        return janela

    def excluir(
        self,
        session: Session,
        janela: JanelaExecucao,
    ) -> None:
        session.delete(janela)
        session.flush()
