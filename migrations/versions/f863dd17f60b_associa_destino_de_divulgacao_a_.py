
"""associa destino de divulgacao a categoria

Revision ID: f863dd17f60b
Revises: f7f90766d174
Create Date: 2026-11-06 15:10:38.437369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f863dd17f60b"
down_revision: Union[str, Sequence[str], None] = "f7f90766d174"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "plataforma_categoria",
        sa.Column("destino_divulgacao_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_plataforma_categoria_destino_divulgacao_id",
        "plataforma_categoria",
        ["destino_divulgacao_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_plataforma_categoria_destino_divulgacao",
        "plataforma_categoria",
        "destinos_divulgacao",
        ["destino_divulgacao_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_plataforma_categoria_destino_divulgacao",
        "plataforma_categoria",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_plataforma_categoria_destino_divulgacao_id",
        table_name="plataforma_categoria",
    )

    op.drop_column(
        "plataforma_categoria",
        "destino_divulgacao_id",
    )
