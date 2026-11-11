from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class PlataformaCategoriaDestino(Base):
    """Associa uma categoria a um destino de divulgação."""

    __tablename__ = "plataforma_categoria_destino"

    __table_args__ = (
        Index(
            "ix_plataforma_categoria_destino_destino_id",
            "destino_divulgacao_id",
        ),
    )

    categoria_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "plataforma_categoria.id",
            ondelete="CASCADE",
            name="fk_categoria_destino_categoria",
        ),
        primary_key=True,
    )

    destino_divulgacao_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "destinos_divulgacao.id",
            ondelete="CASCADE",
            name="fk_categoria_destino_destino",
        ),
        primary_key=True,
    )
