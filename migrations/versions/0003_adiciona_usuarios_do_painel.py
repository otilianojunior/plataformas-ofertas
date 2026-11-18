"""adiciona usuários do painel e tira de divulgação descontos inflados

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('login', sa.String(length=60), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('senha_hash', sa.String(length=255), nullable=False),
        sa.Column('perfil', sa.String(length=20), server_default=sa.text("'operador'"), nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('ultimo_login_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("perfil IN ('admin', 'operador')", name='ck_usuario_perfil'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('login'),
    )
    op.create_index('ix_usuarios_login_minusculo', 'usuarios', [sa.text('lower(login)')], unique=True)

    # Teto padrão de DESCONTO_MAXIMO_PERCENTUAL: preço "de" inflado pela loja.
    op.execute(
        "UPDATE produtos SET elegivel_divulgacao = false "
        "WHERE percentual_desconto > 90 AND elegivel_divulgacao"
    )


def downgrade() -> None:
    op.drop_index('ix_usuarios_login_minusculo', table_name='usuarios')
    op.drop_table('usuarios')
