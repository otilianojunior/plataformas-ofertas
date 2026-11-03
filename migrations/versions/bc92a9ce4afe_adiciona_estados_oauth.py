"""Adiciona estados temporários para autorização OAuth."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bc92a9ce4afe"
down_revision: Union[str, Sequence[str], None] = "7d8fc4ca923d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estados_oauth",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plataforma_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=255), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plataforma_id"],
            ["plataformas.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "state",
            name="uq_estados_oauth_state",
        ),
    )

    op.create_index(
        "ix_estados_oauth_plataforma_id",
        "estados_oauth",
        ["plataforma_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_estados_oauth_plataforma_id",
        table_name="estados_oauth",
    )
    op.drop_table("estados_oauth")
