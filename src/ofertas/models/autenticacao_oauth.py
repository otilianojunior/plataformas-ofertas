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


class AutenticacaoOAuth(Base):
    __tablename__ = "autenticacoes_oauth"

    __table_args__ = (
        CheckConstraint(
            "status_autenticacao IN ('ativa', 'inativa')",
            name="ck_autenticacao_oauth_status_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    plataforma_id: Mapped[int] = mapped_column(
        ForeignKey("plataformas.id"),
        nullable=False,
        index=True,
    )

    access_token_criptografado: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    refresh_token_criptografado: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tipo_token: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    expira_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    escopos: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status_autenticacao: Mapped[str] = mapped_column(
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
