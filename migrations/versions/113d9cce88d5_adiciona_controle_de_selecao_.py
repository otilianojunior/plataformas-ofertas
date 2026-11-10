
"""adiciona controle de selecao progressiva por categoria

Revision ID: 113d9cce88d5
Revises: 3adedbd03251
Create Date: 2026-11-06 19:28:44.202457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "113d9cce88d5"
down_revision: Union[str, Sequence[str], None] = "3adedbd03251"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "plataforma_categoria",
        sa.Column(
            "limite_produtos_selecao",
            sa.Integer(),
            server_default=sa.text("10"),
            nullable=False,
        ),
    )

    op.add_column(
        "plataforma_categoria",
        sa.Column(
            "selecao_renovada_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_categoria_limite_selecao_minimo",
        "plataforma_categoria",
        "limite_produtos_selecao >= 10",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "ck_categoria_limite_selecao_minimo",
        "plataforma_categoria",
        type_="check",
    )

    op.drop_column(
        "plataforma_categoria",
        "selecao_renovada_em",
    )

    op.drop_column(
        "plataforma_categoria",
        "limite_produtos_selecao",
    )
