from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class DestinoDivulgacao(Base):
    __tablename__ = "destinos_divulgacao"

    __table_args__ = (
        UniqueConstraint(
            "plataforma_divulgacao_id",
            "identificador_destino",
            name="uq_destino_plataforma_identificador",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    plataforma_divulgacao_id: Mapped[int] = mapped_column(
        ForeignKey("plataformas_divulgacao.id"),
        nullable=False,
        index=True,
    )

    credencial_divulgacao_id: Mapped[int | None] = mapped_column(
        ForeignKey("credenciais_divulgacao.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    identificador_destino: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    nome_destino: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    status_destino: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
