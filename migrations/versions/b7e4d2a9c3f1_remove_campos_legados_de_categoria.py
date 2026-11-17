"""remove destino principal e selecao antiga da categoria

O destino principal (destino_divulgacao_id) foi substituído pela tabela
plataforma_categoria_destino (vários grupos por categoria) e a seleção por
categoria (limite_produtos_selecao/selecao_renovada_em) pelo limite global
configuracoes_sistema.limite_produtos_por_categoria.

Revision ID: b7e4d2a9c3f1
Revises: a3c91e5f2b17
Create Date: 2026-11-17 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e4d2a9c3f1'
down_revision: Union[str, Sequence[str], None] = 'a3c91e5f2b17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Garante que nenhum destino principal se perca antes de remover a coluna.
    op.execute(
        """
        INSERT INTO plataforma_categoria_destino (categoria_id, destino_divulgacao_id)
        SELECT id, destino_divulgacao_id
        FROM plataforma_categoria
        WHERE destino_divulgacao_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )
    op.drop_index(
        'ix_plataforma_categoria_destino_divulgacao_id',
        table_name='plataforma_categoria',
    )
    op.drop_constraint(
        'fk_plataforma_categoria_destino_divulgacao',
        'plataforma_categoria',
        type_='foreignkey',
    )
    op.drop_column('plataforma_categoria', 'destino_divulgacao_id')

    op.drop_constraint(
        'ck_categoria_limite_selecao_minimo',
        'plataforma_categoria',
        type_='check',
    )
    op.drop_column('plataforma_categoria', 'limite_produtos_selecao')
    op.drop_column('plataforma_categoria', 'selecao_renovada_em')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'plataforma_categoria',
        sa.Column('selecao_renovada_em', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'plataforma_categoria',
        sa.Column(
            'limite_produtos_selecao',
            sa.Integer(),
            server_default=sa.text('10'),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        'ck_categoria_limite_selecao_minimo',
        'plataforma_categoria',
        'limite_produtos_selecao >= 10',
    )

    op.add_column(
        'plataforma_categoria',
        sa.Column('destino_divulgacao_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_plataforma_categoria_destino_divulgacao',
        'plataforma_categoria',
        'destinos_divulgacao',
        ['destino_divulgacao_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_plataforma_categoria_destino_divulgacao_id',
        'plataforma_categoria',
        ['destino_divulgacao_id'],
    )
    # Restaura como principal o menor grupo associado.
    op.execute(
        """
        UPDATE plataforma_categoria pc
        SET destino_divulgacao_id = (
            SELECT min(x.destino_divulgacao_id)
            FROM plataforma_categoria_destino x
            WHERE x.categoria_id = pc.id
        )
        """
    )
