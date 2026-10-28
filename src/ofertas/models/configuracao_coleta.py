from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class ConfiguracaoColeta(Base):
    __tablename__ = "configuracoes_coleta"

    __table_args__ = (
        ForeignKeyConstraint(
            ["categoria_id", "plataforma_id"],
            ["plataforma_categoria.id", "plataforma_categoria.plataforma_id"],
            name="fk_config_coleta_categoria_mesma_plataforma",
        ),
        CheckConstraint(
            "desconto_minimo_percentual >= 0 "
            "AND desconto_minimo_percentual <= 100",
            name="ck_config_coleta_desconto_valido",
        ),
        CheckConstraint(
            "preco_minimo IS NULL OR preco_minimo >= 0",
            name="ck_config_coleta_preco_minimo_nao_negativo",
        ),
        CheckConstraint(
            "preco_maximo IS NULL OR preco_maximo >= 0",
            name="ck_config_coleta_preco_maximo_nao_negativo",
        ),
        CheckConstraint(
            "preco_minimo IS NULL OR preco_maximo IS NULL "
            "OR preco_maximo >= preco_minimo",
            name="ck_config_coleta_faixa_preco_valida",
        ),
        CheckConstraint(
            "intervalo_coleta_minutos > 0",
            name="ck_config_coleta_intervalo_positivo",
        ),
        Index(
            "uq_config_coleta_plataforma_geral",
            "plataforma_id",
            unique=True,
            postgresql_where=text("categoria_id IS NULL"),
        ),
        Index(
            "uq_config_coleta_plataforma_categoria",
            "plataforma_id",
            "categoria_id",
            unique=True,
            postgresql_where=text("categoria_id IS NOT NULL"),
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

    desconto_minimo_percentual: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    preco_minimo: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    preco_maximo: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    intervalo_coleta_minutos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        server_default=text("60"),
    )

    status_coleta: Mapped[bool] = mapped_column(
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
