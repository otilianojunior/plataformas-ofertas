
"""adiciona controles independentes de automacao

Revision ID: 825e650031c8
Revises: f863dd17f60b
Create Date: 2026-11-06 15:43:51.940282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "825e650031c8"
down_revision: Union[str, Sequence[str], None] = "f863dd17f60b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Preserva os dados existentes ao renomear a coluna.
    op.alter_column(
        "configuracoes_sistema",
        "coleta_automatica_ativa",
        new_column_name="coleta_mercado_livre_ativa",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("false"),
    )

    op.add_column(
        "configuracoes_sistema",
        sa.Column(
            "coleta_shopee_ativa",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.add_column(
        "configuracoes_sistema",
        sa.Column(
            "publicacao_telegram_ativa",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.add_column(
        "configuracoes_sistema",
        sa.Column(
            "publicacao_whatsapp_ativa",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column(
        "configuracoes_sistema",
        "publicacao_whatsapp_ativa",
    )

    op.drop_column(
        "configuracoes_sistema",
        "publicacao_telegram_ativa",
    )

    op.drop_column(
        "configuracoes_sistema",
        "coleta_shopee_ativa",
    )

    # Restaura o nome antigo preservando o valor.
    op.alter_column(
        "configuracoes_sistema",
        "coleta_mercado_livre_ativa",
        new_column_name="coleta_automatica_ativa",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        existing_server_default=sa.text("false"),
    )
