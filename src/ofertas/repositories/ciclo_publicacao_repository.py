from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ofertas.models.ciclo_publicacao import CicloPublicacao


class CicloPublicacaoRepository:
    """Acesso aos registros de ciclos de publicação por destino."""

    def iniciar(
        self,
        session: Session,
        destino_id: int,
        quantidade_candidatos: int,
    ) -> CicloPublicacao:
        ciclo = CicloPublicacao(
            destino_divulgacao_id=destino_id,
            status="em_andamento",
            quantidade_candidatos=quantidade_candidatos,
        )
        session.add(ciclo)
        session.flush()
        return ciclo

    def marcar_interrompidos(
        self,
        session: Session,
        destino_id: int,
    ) -> int:
        """Fecha ciclos deixados em andamento (ex.: API encerrada no meio).

        Só deve ser chamado com o lock exclusivo do destino adquirido,
        quando nenhum outro ciclo do destino pode estar ativo.
        """

        resultado = session.execute(
            update(CicloPublicacao)
            .where(
                CicloPublicacao.destino_divulgacao_id == destino_id,
                CicloPublicacao.status == "em_andamento",
            )
            .values(
                status="interrompido",
                finalizado_em=datetime.now(timezone.utc),
                erro="Ciclo interrompido antes da finalização.",
            )
        )
        session.flush()
        return resultado.rowcount or 0

    def atualizar(
        self,
        session: Session,
        ciclo_id: int,
        **valores,
    ) -> None:
        session.execute(
            update(CicloPublicacao)
            .where(CicloPublicacao.id == ciclo_id)
            .values(**valores)
        )
        session.flush()

    def buscar_ultimo(
        self,
        session: Session,
        destino_id: int,
    ) -> CicloPublicacao | None:
        return session.scalar(
            select(CicloPublicacao)
            .where(CicloPublicacao.destino_divulgacao_id == destino_id)
            .order_by(
                CicloPublicacao.iniciado_em.desc(),
                CicloPublicacao.id.desc(),
            )
            .limit(1)
        )

    def listar(
        self,
        session: Session,
        *,
        destino_id: int | None = None,
        status: str | None = None,
        limite: int = 20,
    ) -> list[CicloPublicacao]:
        consulta = select(CicloPublicacao)

        if destino_id is not None:
            consulta = consulta.where(
                CicloPublicacao.destino_divulgacao_id == destino_id
            )

        if status is not None:
            consulta = consulta.where(CicloPublicacao.status == status)

        return list(
            session.scalars(
                consulta.order_by(
                    CicloPublicacao.iniciado_em.desc(),
                    CicloPublicacao.id.desc(),
                ).limit(limite)
            ).all()
        )
