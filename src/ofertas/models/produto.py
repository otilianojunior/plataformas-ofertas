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


class Produto(Base):
    __tablename__ = "produtos"

    __table_args__ = (
        UniqueConstraint(
            "plataforma_id",
            "id_item_plataforma",
            name="uq_produto_plataforma_item_externo",
        ),
        CheckConstraint(
            "preco_atual > 0",
            name="ck_produto_preco_atual_positivo",
        ),
        CheckConstraint(
            "preco_original IS NULL OR preco_original >= 0",
            name="ck_produto_preco_original_nao_negativo",
        ),
        CheckConstraint(
            "percentual_desconto IS NULL OR "
            "(percentual_desconto >= 0 AND percentual_desconto <= 100)",
            name="ck_produto_desconto_valido",
        ),
        CheckConstraint(
            "status_monitoramento IN ('ativo', 'pausado', 'encerrado')",
            name="ck_produto_status_monitoramento_valido",
        ),
        CheckConstraint(
            "status_link_afiliado IN ('pendente', 'gerado', 'erro')",
            name="ck_produto_status_link_afiliado_valido",
        ),
        CheckConstraint(
            "metodo_geracao_link_afiliado IS NULL OR "
            "metodo_geracao_link_afiliado IN ('manual', 'api')",
            name="ck_produto_metodo_link_afiliado_valido",
        ),
        ForeignKeyConstraint(
            ["categoria_id", "plataforma_id"],
            [
                "plataforma_categoria.id",
                "plataforma_categoria.plataforma_id",
            ],
            name="fk_produto_categoria_mesma_plataforma",
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

    # Identificador do produto no catálogo do marketplace.
    # Exemplo no Mercado Livre: MLB...
    id_produto_plataforma: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    # Identificador do anúncio/oferta específica no marketplace.
    # Exemplo no Mercado Livre: MLB...
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

    disponivel: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    status_monitoramento: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ativo",
        server_default=text("'ativo'"),
    )

    elegivel_divulgacao: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # Link de afiliado pertence ao produto, não ao destino.
    url_afiliada: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status_link_afiliado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pendente",
        server_default=text("'pendente'"),
    )

    metodo_geracao_link_afiliado: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    identificador_rastreamento: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    erro_geracao_link_afiliado: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    link_afiliado_gerado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    primeira_coleta_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    ultima_coleta_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    proxima_coleta_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
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