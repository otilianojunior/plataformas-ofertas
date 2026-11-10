
"""adiciona posicao do produto na selecao da categoria

Revision ID: 3808449fa126
Revises: 113d9cce88d5
Create Date: 2026-11-10 12:40:11.660239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3808449fa126"
down_revision: Union[str, Sequence[str], None] = "113d9cce88d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "produtos",
        sa.Column(
            "posicao_selecao_categoria",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_produto_posicao_selecao_valida",
        "produtos",
        "posicao_selecao_categoria IS NULL OR "
        "posicao_selecao_categoria >= 1",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "ck_produto_posicao_selecao_valida",
        "produtos",
        type_="check",
    )

    op.drop_column(
        "produtos",
        "posicao_selecao_categoria",
    )
