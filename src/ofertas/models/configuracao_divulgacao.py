from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class ConfiguracaoDivulgacao(Base):
    __tablename__ = "configuracoes_divulgacao"

    __table_args__ = (
        CheckConstraint(
            "desconto_minimo_percentual >= 0 "
            "AND desconto_minimo_percentual <= 100",
            name="ck_config_divulgacao_desconto_valido",
        ),
        CheckConstraint(
            "preco_minimo IS NULL OR preco_minimo >= 0",
            name="ck_config_divulgacao_preco_minimo_nao_negativo",
        ),
        CheckConstraint(
            "preco_maximo IS NULL OR preco_maximo >= 0",
            name="ck_config_divulgacao_preco_maximo_nao_negativo",
        ),
        CheckConstraint(
            "preco_minimo IS NULL OR preco_maximo IS NULL "
            "OR preco_maximo >= preco_minimo",
            name="ck_config_divulgacao_faixa_preco_valida",
        ),
        CheckConstraint(
            "intervalo_publicacao_minutos >= 0",
            name="ck_config_divulgacao_intervalo_nao_negativo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    destino_divulgacao_id: Mapped[int] = mapped_column(
        ForeignKey("destinos_divulgacao.id"),
        nullable=False,
        unique=True,
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

    intervalo_publicacao_minutos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    identificador_rastreamento: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    status_configuracao: Mapped[bool] = mapped_column(
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
