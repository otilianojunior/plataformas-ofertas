"""categoria prioritária (favorita)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-18 16:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'plataforma_categoria',
        sa.Column('prioritaria', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('plataforma_categoria', 'prioritaria')
