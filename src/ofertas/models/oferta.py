from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class Oferta(Base):
    __tablename__ = "ofertas"

    __table_args__ = (
        UniqueConstraint(
            "plataforma_id",
            "id_item_plataforma",
            name="uq_oferta_plataforma_item_externo",
        ),
        CheckConstraint(
            "preco_atual > 0",
            name="ck_oferta_preco_atual_positivo",
        ),
        CheckConstraint(
            "preco_original IS NULL OR preco_original >= 0",
            name="ck_oferta_preco_original_nao_negativo",
        ),
        CheckConstraint(
            "percentual_desconto IS NULL OR "
            "(percentual_desconto >= 0 AND percentual_desconto <= 100)",
            name="ck_oferta_desconto_valido",
        ),
        CheckConstraint(
            "expira_em > coletada_em",
            name="ck_oferta_expiracao_posterior_coleta",
        ),
        ForeignKeyConstraint(
            ["categoria_id", "plataforma_id"],
            ["plataforma_categoria.id", "plataforma_categoria.plataforma_id"],
            name="fk_oferta_categoria_mesma_plataforma",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    plataforma_id: Mapped[int] = mapped_column(
        ForeignKey("plataformas.id"),
        nullable=False,
        index=True,
    )

    categoria_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
    )

    id_item_plataforma: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    titulo: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    descricao: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    affiliate_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    imagem_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    preco_atual: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    preco_original: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    percentual_desconto: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    status_oferta: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    coletada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    expira_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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
