from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class Publicacao(Base):
    __tablename__ = "publicacoes"

    __table_args__ = (
        CheckConstraint(
            "preco_divulgado > 0",
            name="ck_publicacao_preco_positivo",
        ),
        CheckConstraint(
            "tentativas >= 0",
            name="ck_publicacao_tentativas_nao_negativas",
        ),
        CheckConstraint(
            "status_publicacao IN ('pendente', 'publicada', 'falhou')",
            name="ck_publicacao_status_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    oferta_id: Mapped[int] = mapped_column(
        ForeignKey("ofertas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    destino_divulgacao_id: Mapped[int] = mapped_column(
        ForeignKey("destinos_divulgacao.id"),
        nullable=False,
        index=True,
    )

    preco_divulgado: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    status_publicacao: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pendente",
        server_default=text("'pendente'"),
    )

    tentativas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    publicada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
