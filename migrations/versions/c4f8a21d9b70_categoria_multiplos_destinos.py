"""Permite associar categorias a multiplos destinos.

Revision ID: c4f8a21d9b70
Revises: 6db524ad4e0d
"""

from alembic import op
import sqlalchemy as sa


revision = "c4f8a21d9b70"
down_revision = "6db524ad4e0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plataforma_categoria_destino",
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("destino_divulgacao_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "categoria_id",
            "destino_divulgacao_id",
            name="pk_plataforma_categoria_destino",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["plataforma_categoria.id"],
            name="fk_categoria_destino_categoria",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["destino_divulgacao_id"],
            ["destinos_divulgacao.id"],
            name="fk_categoria_destino_destino",
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_plataforma_categoria_destino_destino_id",
        "plataforma_categoria_destino",
        ["destino_divulgacao_id"],
    )

    op.execute(
        sa.text("""
            INSERT INTO plataforma_categoria_destino (
                categoria_id,
                destino_divulgacao_id
            )
            SELECT
                id,
                destino_divulgacao_id
            FROM plataforma_categoria
            WHERE destino_divulgacao_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    op.drop_index(
        "ix_plataforma_categoria_destino_destino_id",
        table_name="plataforma_categoria_destino",
    )
    op.drop_table("plataforma_categoria_destino")
