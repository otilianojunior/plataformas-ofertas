"""adiciona status parcial nas coletas e ciclos de publicacao

Revision ID: a3c91e5f2b17
Revises: 775b36d8a1bc
Create Date: 2026-11-17 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c91e5f2b17'
down_revision: Union[str, Sequence[str], None] = '775b36d8a1bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        'ck_execucao_status_valido',
        'execucoes_coleta',
        type_='check',
    )
    op.create_check_constraint(
        'ck_execucao_status_valido',
        'execucoes_coleta',
        "status IN ('em_andamento', 'concluida', 'parcial', 'falhou')",
    )

    op.create_table(
        'ciclos_publicacao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('destino_divulgacao_id', sa.Integer(), nullable=False),
        sa.Column('iniciado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finalizado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), server_default=sa.text("'em_andamento'"), nullable=False),
        sa.Column('quantidade_candidatos', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('quantidade_publicada', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('quantidade_falha', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('quantidade_ignorada', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('erro', sa.Text(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "status IN ('em_andamento', 'concluido', 'pausado', 'falhou', 'interrompido')",
            name='ck_ciclo_publicacao_status_valido',
        ),
        sa.CheckConstraint(
            'quantidade_candidatos >= 0 AND quantidade_publicada >= 0 '
            'AND quantidade_falha >= 0 AND quantidade_ignorada >= 0',
            name='ck_ciclo_publicacao_quantidades_nao_negativas',
        ),
        sa.CheckConstraint(
            'finalizado_em IS NULL OR finalizado_em >= iniciado_em',
            name='ck_ciclo_publicacao_finalizacao_valida',
        ),
        sa.ForeignKeyConstraint(
            ['destino_divulgacao_id'],
            ['destinos_divulgacao.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_ciclos_publicacao_destino_iniciado',
        'ciclos_publicacao',
        ['destino_divulgacao_id', 'iniciado_em'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_ciclos_publicacao_destino_iniciado',
        table_name='ciclos_publicacao',
    )
    op.drop_table('ciclos_publicacao')

    op.execute(
        "UPDATE execucoes_coleta SET status = 'falhou' "
        "WHERE status = 'parcial'"
    )
    op.drop_constraint(
        'ck_execucao_status_valido',
        'execucoes_coleta',
        type_='check',
    )
    op.create_check_constraint(
        'ck_execucao_status_valido',
        'execucoes_coleta',
        "status IN ('em_andamento', 'concluida', 'falhou')",
    )
