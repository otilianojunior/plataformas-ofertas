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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class PlataformaCategoria(Base):
    __tablename__ = "plataforma_categoria"

    __table_args__ = (
        UniqueConstraint(
            "plataforma_id",
            "id_categoria_plataforma",
            name="uq_categoria_plataforma_id_externo",
        ),
        UniqueConstraint(
            "id",
            "plataforma_id",
            name="uq_categoria_id_plataforma",
        ),
        CheckConstraint(
            "desconto_minimo_percentual >= 10 AND "
            "desconto_minimo_percentual <= 100",
            name="ck_categoria_desconto_minimo_valido",
        ),
        CheckConstraint(
            "limite_produtos_selecao >= 10",
            name="ck_categoria_limite_selecao_minimo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    plataforma_id: Mapped[int] = mapped_column(
        ForeignKey("plataformas.id"),
        nullable=False,
        index=True,
    )

    destino_divulgacao_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "destinos_divulgacao.id",
            ondelete="SET NULL",
            name="fk_plataforma_categoria_destino_divulgacao",
        ),
        nullable=True,
        index=True,
    )

    id_categoria_plataforma: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    nome_categoria: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    etiqueta_afiliado: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    desconto_minimo_percentual: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    limite_produtos_selecao: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default=text("10"),
    )

    selecao_renovada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status_categoria: Mapped[bool] = mapped_column(
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
