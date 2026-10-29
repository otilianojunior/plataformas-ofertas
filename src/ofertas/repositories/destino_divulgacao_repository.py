from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.destino_divulgacao import DestinoDivulgacao


class DestinoDivulgacaoRepository:
    def listar(
        self,
        session: Session,
    ) -> list[DestinoDivulgacao]:
        consulta = select(DestinoDivulgacao).order_by(
            DestinoDivulgacao.id
        )
        return list(session.scalars(consulta).all())

    def buscar_por_id(
        self,
        session: Session,
        destino_id: int,
    ) -> DestinoDivulgacao | None:
        return session.get(DestinoDivulgacao, destino_id)

    def buscar_por_identificador(
        self,
        session: Session,
        plataforma_id: int,
        identificador_destino: str,
    ) -> DestinoDivulgacao | None:
        consulta = select(DestinoDivulgacao).where(
            DestinoDivulgacao.plataforma_divulgacao_id == plataforma_id,
            DestinoDivulgacao.identificador_destino
            == identificador_destino,
        )
        return session.scalars(consulta).one_or_none()

    def criar(
        self,
        session: Session,
        *,
        plataforma_id: int,
        credencial_id: int,
        identificador_destino: str,
        nome_destino: str,
        status_destino: bool,
    ) -> DestinoDivulgacao:
        destino = DestinoDivulgacao(
            plataforma_divulgacao_id=plataforma_id,
            credencial_divulgacao_id=credencial_id,
            identificador_destino=identificador_destino,
            nome_destino=nome_destino,
            status_destino=status_destino,
        )
        session.add(destino)
        session.flush()
        return destino

    def atualizar_status(
        self,
        session: Session,
        destino: DestinoDivulgacao,
        status_destino: bool,
    ) -> DestinoDivulgacao:
        destino.status_destino = status_destino
        session.flush()
        return destino
