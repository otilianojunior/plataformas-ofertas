from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class LinkAfiliado(Base):
    __tablename__ = "links_afiliados"

    __table_args__ = (
        UniqueConstraint(
            "oferta_id",
            "destino_divulgacao_id",
            name="uq_link_afiliado_oferta_destino",
        ),
        CheckConstraint(
            "metodo_geracao IN ('manual', 'api')",
            name="ck_link_afiliado_metodo_valido",
        ),
        CheckConstraint(
            "status_link IN ('ativo', 'inativo', 'erro')",
            name="ck_link_afiliado_status_valido",
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

    url_afiliada: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    metodo_geracao: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="manual",
        server_default=text("'manual'"),
    )

    identificador_rastreamento: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    status_link: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ativo",
        server_default=text("'ativo'"),
    )

    gerado_em: Mapped[datetime | None] = mapped_column(
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
