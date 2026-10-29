"""Adiciona nome às credenciais de divulgação."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "10bdca924edd"
down_revision: Union[str, None] = "7418fea9829b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "credenciais_divulgacao",
        sa.Column("nome_credencial", sa.String(length=100), nullable=True),
    )

    op.execute(
        """
        UPDATE credenciais_divulgacao
        SET nome_credencial = 'credencial_' || id::text
        WHERE nome_credencial IS NULL
        """
    )

    op.alter_column(
        "credenciais_divulgacao",
        "nome_credencial",
        existing_type=sa.String(length=100),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("credenciais_divulgacao", "nome_credencial")