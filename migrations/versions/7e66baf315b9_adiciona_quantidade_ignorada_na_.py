"""adiciona quantidade ignorada na execucao de coleta

Revision ID: 7e66baf315b9
Revises: 1e63d09abe47
Create Date: 2026-11-03 16:50:10.091899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e66baf315b9'
down_revision: Union[str, Sequence[str], None] = '1e63d09abe47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "execucoes_coleta",
        sa.Column(
            "quantidade_ignorada",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_execucao_quantidade_ignorada_nao_negativa",
        "execucoes_coleta",
        "quantidade_ignorada >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_execucao_quantidade_ignorada_nao_negativa",
        "execucoes_coleta",
        type_="check",
    )
    op.drop_column("execucoes_coleta", "quantidade_ignorada")
