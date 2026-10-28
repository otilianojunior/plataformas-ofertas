from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class CredencialPlataforma(Base):
    __tablename__ = "credenciais_plataforma"

    __table_args__ = (
        CheckConstraint(
            "status_credencial IN ('ativa', 'inativa')",
            name="ck_credencial_plataforma_status_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    plataforma_id: Mapped[int] = mapped_column(
        ForeignKey("plataformas.id"),
        nullable=False,
        index=True,
    )

    tipo_credencial: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    valor_criptografado: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status_credencial: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ativa",
        server_default=text("'ativa'"),
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
