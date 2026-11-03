"""integra desconto minimo na categoria

Revision ID: 1e63d09abe47
Revises: bc92a9ce4afe
Create Date: 2026-11-03 13:59:37.495669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e63d09abe47'
down_revision: Union[str, Sequence[str], None] = 'bc92a9ce4afe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "plataforma_categoria",
        sa.Column(
            "desconto_minimo_percentual",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
        ),
    )

    op.create_check_constraint(
        "ck_categoria_desconto_minimo_valido",
        "plataforma_categoria",
        "desconto_minimo_percentual >= 10 AND "
        "desconto_minimo_percentual <= 100",
    )

    op.drop_table("configuracoes_coleta")


def downgrade() -> None:
    op.drop_constraint(
        "ck_categoria_desconto_minimo_valido",
        "plataforma_categoria",
        type_="check",
    )

    op.drop_column(
        "plataforma_categoria",
        "desconto_minimo_percentual",
    )
