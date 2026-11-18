"""validade do preço para publicar

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18 13:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'configuracoes_sistema',
        sa.Column('validade_preco_minutos', sa.Integer(), server_default=sa.text('120'), nullable=False),
    )
    op.create_check_constraint(
        'ck_config_sistema_validade_preco_minima',
        'configuracoes_sistema',
        'validade_preco_minutos >= 10',
    )


def downgrade() -> None:
    op.drop_constraint('ck_config_sistema_validade_preco_minima', 'configuracoes_sistema', type_='check')
    op.drop_column('configuracoes_sistema', 'validade_preco_minutos')
