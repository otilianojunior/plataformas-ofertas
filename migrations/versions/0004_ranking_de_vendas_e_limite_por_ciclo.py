"""ranking de vendas do produto e limite de publicações por ciclo

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 09:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('produtos', sa.Column('quantidade_vendida', sa.Integer(), nullable=True))
    op.add_column(
        'configuracoes_sistema',
        sa.Column('limite_publicacoes_por_ciclo', sa.Integer(), server_default=sa.text('20'), nullable=False),
    )
    op.create_check_constraint(
        'ck_config_sistema_limite_ciclo_positivo',
        'configuracoes_sistema',
        'limite_publicacoes_por_ciclo >= 1',
    )


def downgrade() -> None:
    op.drop_constraint('ck_config_sistema_limite_ciclo_positivo', 'configuracoes_sistema', type_='check')
    op.drop_column('configuracoes_sistema', 'limite_publicacoes_por_ciclo')
    op.drop_column('produtos', 'quantidade_vendida')
