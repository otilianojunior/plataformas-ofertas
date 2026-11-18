from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


PERFIS_USUARIO = ("admin", "operador")


class Usuario(Base):
    """Usuário do painel. A senha fica só como hash (scrypt), nunca em texto."""

    __tablename__ = "usuarios"

    __table_args__ = (
        CheckConstraint(
            "perfil IN ('admin', 'operador')",
            name="ck_usuario_perfil",
        ),
        # Login único sem diferenciar maiúsculas.
        Index(
            "ix_usuarios_login_minusculo",
            func.lower(text("login")),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    login: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        unique=True,
    )

    nome: Mapped[str] = mapped_column(String(120), nullable=False)

    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    perfil: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="operador",
        server_default=text("'operador'"),
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    ultimo_login_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
