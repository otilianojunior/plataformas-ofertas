"""Associa credencial ao destino de divulgação."""

from alembic import op
import sqlalchemy as sa


revision = "7418fea9829b"
down_revision = "dc4d8b52d42b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "destinos_divulgacao",
        sa.Column(
            "credencial_divulgacao_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_destinos_divulgacao_credencial_divulgacao_id"),
        "destinos_divulgacao",
        ["credencial_divulgacao_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_destinos_divulgacao_credencial_divulgacao_id",
        "destinos_divulgacao",
        "credenciais_divulgacao",
        ["credencial_divulgacao_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_table("credenciais_destinos_divulgacao")


def downgrade() -> None:
    op.create_table(
        "credenciais_destinos_divulgacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "credencial_divulgacao_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "destino_divulgacao_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "credencial_divulgacao_id",
            "destino_divulgacao_id",
            name="uq_credencial_destino_divulgacao",
        ),
        sa.ForeignKeyConstraint(
            ["credencial_divulgacao_id"],
            ["credenciais_divulgacao.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["destino_divulgacao_id"],
            ["destinos_divulgacao.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_credenciais_destinos_divulgacao_credencial_divulgacao_id",
        "credenciais_destinos_divulgacao",
        ["credencial_divulgacao_id"],
        unique=False,
    )

    op.create_index(
        "ix_credenciais_destinos_divulgacao_destino_divulgacao_id",
        "credenciais_destinos_divulgacao",
        ["destino_divulgacao_id"],
        unique=False,
    )

    op.drop_constraint(
        "fk_destinos_divulgacao_credencial_divulgacao_id",
        "destinos_divulgacao",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_destinos_divulgacao_credencial_divulgacao_id"),
        table_name="destinos_divulgacao",
    )

    op.drop_column(
        "destinos_divulgacao",
        "credencial_divulgacao_id",
    )
