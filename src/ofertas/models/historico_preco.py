from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class HistoricoPreco(Base):
    __tablename__ = "historico_precos"

    __table_args__ = (
        CheckConstraint(
            "preco > 0",
            name="ck_historico_preco_positivo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    oferta_id: Mapped[int] = mapped_column(
        ForeignKey("ofertas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    preco: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    registrado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    origem: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="coleta_api",
        server_default="coleta_api",
    )
