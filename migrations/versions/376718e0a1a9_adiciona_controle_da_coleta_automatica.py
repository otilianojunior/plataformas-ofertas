
"""adiciona controle da coleta automatica

Revision ID: 376718e0a1a9
Revises: c84f2a91d7e3
Create Date: 2026-11-04 13:51:57.604617
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "376718e0a1a9"
down_revision: Union[str, Sequence[str], None] = "c84f2a91d7e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "configuracoes_sistema",
        sa.Column(
            "coleta_automatica_ativa",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "configuracoes_sistema",
        "coleta_automatica_ativa",
    )
