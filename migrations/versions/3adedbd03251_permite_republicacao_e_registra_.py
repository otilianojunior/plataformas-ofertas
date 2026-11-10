
"""permite republicacao e registra desconto divulgado

Revision ID: 3adedbd03251
Revises: 825e650031c8
Create Date: 2026-11-06 16:29:07.530812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3adedbd03251"
down_revision: Union[str, Sequence[str], None] = "825e650031c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "publicacoes",
        sa.Column(
            "percentual_desconto_divulgado",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_publicacao_desconto_divulgado_valido",
        "publicacoes",
        "percentual_desconto_divulgado IS NULL OR "
        "(percentual_desconto_divulgado >= 0 AND "
        "percentual_desconto_divulgado <= 100)",
    )

    op.drop_index(
        "uq_publicacao_ativa_por_destino",
        table_name="publicacoes",
    )

    op.create_index(
        "uq_publicacao_pendente_por_destino",
        "publicacoes",
        ["produto_id", "destino_divulgacao_id"],
        unique=True,
        postgresql_where=sa.text(
            "status_publicacao = 'pendente'"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "uq_publicacao_pendente_por_destino",
        table_name="publicacoes",
    )

    op.create_index(
        "uq_publicacao_ativa_por_destino",
        "publicacoes",
        ["produto_id", "destino_divulgacao_id"],
        unique=True,
        postgresql_where=sa.text(
            "status_publicacao IN ('pendente', 'publicada')"
        ),
    )

    op.drop_constraint(
        "ck_publicacao_desconto_divulgado_valido",
        "publicacoes",
        type_="check",
    )

    op.drop_column(
        "publicacoes",
        "percentual_desconto_divulgado",
    )
