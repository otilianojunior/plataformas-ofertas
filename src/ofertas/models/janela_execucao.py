from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class JanelaExecucao(Base):
    """Intervalo diário permitido para execução das automações."""

    __tablename__ = "janelas_execucao"

    __table_args__ = (
        CheckConstraint(
            "hora_inicio < hora_fim",
            name="ck_janela_execucao_horario_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    hora_inicio: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    hora_fim: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    ativa: Mapped[bool] = mapped_column(
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
