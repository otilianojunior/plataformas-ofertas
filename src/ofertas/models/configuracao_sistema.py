from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ofertas.db.base import Base


class ConfiguracaoSistema(Base):
    __tablename__ = "configuracoes_sistema"

    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="ck_config_sistema_registro_unico",
        ),
        CheckConstraint(
            "intervalo_coleta_minutos > 0",
            name="ck_config_sistema_intervalo_positivo",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        default=1,
        server_default=text("1"),
    )

    intervalo_coleta_minutos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    coleta_mercado_livre_ativa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    coleta_shopee_ativa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    publicacao_telegram_ativa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    publicacao_whatsapp_ativa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    agendador_ultimo_sinal_em: Mapped[datetime | None] = mapped_column(
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
