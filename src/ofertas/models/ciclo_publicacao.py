from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class CicloPublicacao(Base):
    """Registro de cada ciclo automático de publicação de um destino."""

    __tablename__ = "ciclos_publicacao"

    STATUS = (
        "em_andamento",
        "concluido",
        "pausado",
        "falhou",
        "interrompido",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('em_andamento', 'concluido', 'pausado', "
            "'falhou', 'interrompido')",
            name="ck_ciclo_publicacao_status_valido",
        ),
        CheckConstraint(
            "quantidade_candidatos >= 0 AND quantidade_publicada >= 0 "
            "AND quantidade_falha >= 0 AND quantidade_ignorada >= 0",
            name="ck_ciclo_publicacao_quantidades_nao_negativas",
        ),
        CheckConstraint(
            "finalizado_em IS NULL OR finalizado_em >= iniciado_em",
            name="ck_ciclo_publicacao_finalizacao_valida",
        ),
        Index(
            "ix_ciclos_publicacao_destino_iniciado",
            "destino_divulgacao_id",
            "iniciado_em",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    destino_divulgacao_id: Mapped[int] = mapped_column(
        ForeignKey("destinos_divulgacao.id", ondelete="CASCADE"),
        nullable=False,
    )

    iniciado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    finalizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="em_andamento",
        server_default=text("'em_andamento'"),
    )

    quantidade_candidatos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"),
    )

    quantidade_publicada: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"),
    )

    quantidade_falha: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"),
    )

    quantidade_ignorada: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0"),
    )

    erro: Mapped[str | None] = mapped_column(Text, nullable=True)

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
