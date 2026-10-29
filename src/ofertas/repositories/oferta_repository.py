from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.oferta import Oferta


class OfertaRepository:
    """Centraliza o acesso aos dados das ofertas."""

    def listar(self, session: Session) -> list[Oferta]:
        """Retorna as ofertas mais recentes primeiro."""
        consulta = select(Oferta).order_by(Oferta.created_at.desc(), Oferta.id.desc())
        return list(session.scalars(consulta).all())

    def buscar_por_id(self, session: Session, oferta_id: int) -> Oferta | None:
        """Busca uma oferta pelo identificador interno."""
        consulta = select(Oferta).where(Oferta.id == oferta_id)
        return session.scalars(consulta).one_or_none()

    def buscar_por_item(
        self,
        session: Session,
        plataforma_id: int,
        id_item_plataforma: str,
    ) -> Oferta | None:
        """Busca um item externo dentro de uma plataforma."""
        consulta = select(Oferta).where(
            Oferta.plataforma_id == plataforma_id,
            Oferta.id_item_plataforma == id_item_plataforma,
        )
        return session.scalars(consulta).one_or_none()

    def criar(self, session: Session, dados: dict) -> Oferta:
        """Adiciona uma oferta à sessão atual."""
        oferta = Oferta(**dados)
        session.add(oferta)
        session.flush()
        return oferta
