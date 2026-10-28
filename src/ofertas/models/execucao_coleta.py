from datetime import datetime

from sqlalchemy import (
    DateTime,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class ExecucaoColeta(Base):
    __tablename__ = "execucoes_coleta"

    __table_args__ = (
        CheckConstraint(
            "quantidade_encontrada >= 0",
            name="ck_execucao_quantidade_encontrada_nao_negativa",
        ),
        CheckConstraint(
            "quantidade_processada >= 0",
            name="ck_execucao_quantidade_processada_nao_negativa",
        ),
        CheckConstraint(
            "status IN ('em_andamento', 'concluida', 'falhou')",
            name="ck_execucao_status_valido",
        ),
        CheckConstraint(
            "finalizada_em IS NULL OR finalizada_em >= iniciada_em",
            name="ck_execucao_finalizacao_valida",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    plataforma_id: Mapped[int] = mapped_column(
        ForeignKey("plataformas.id"),
        nullable=False,
        index=True,
    )

    iniciada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    finalizada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="em_andamento",
        server_default=text("'em_andamento'"),
    )

    quantidade_encontrada: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    quantidade_processada: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    erro: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
