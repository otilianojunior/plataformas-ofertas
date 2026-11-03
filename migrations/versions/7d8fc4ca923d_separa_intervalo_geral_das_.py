"""Separa intervalo global das configurações por categoria."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7d8fc4ca923d"
down_revision: Union[str, Sequence[str], None] = "242165d1a61a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "configuracoes_sistema",
        sa.Column("id", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("intervalo_coleta_minutos", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_config_sistema_registro_unico"),
        sa.CheckConstraint("intervalo_coleta_minutos > 0", name="ck_config_sistema_intervalo_positivo"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute("""
        INSERT INTO configuracoes_sistema (id, intervalo_coleta_minutos)
        SELECT 1, COALESCE(
            (SELECT intervalo_coleta_minutos
             FROM configuracoes_coleta
             WHERE categoria_id IS NULL
             ORDER BY id
             LIMIT 1),
            45
        )
    """)

    # Remove somente a configuração geral antiga.
    op.execute(
        "DELETE FROM configuracoes_coleta WHERE categoria_id IS NULL"
    )

    # Remove os índices parciais antigos.
    op.drop_index(
        "uq_config_coleta_plataforma_geral",
        table_name="configuracoes_coleta",
    )
    op.drop_index(
        "uq_config_coleta_plataforma_categoria",
        table_name="configuracoes_coleta",
    )

    op.drop_constraint(
        "ck_config_coleta_intervalo_positivo",
        "configuracoes_coleta",
        type_="check",
    )
    op.drop_constraint(
        "ck_config_coleta_desconto_valido",
        "configuracoes_coleta",
        type_="check",
    )

    op.drop_column("configuracoes_coleta", "intervalo_coleta_minutos")

    op.alter_column(
        "configuracoes_coleta",
        "categoria_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_check_constraint(
        "ck_config_coleta_desconto_valido",
        "configuracoes_coleta",
        "desconto_minimo_percentual >= 10 AND desconto_minimo_percentual <= 100",
    )

    op.create_unique_constraint(
        "uq_config_coleta_plataforma_categoria",
        "configuracoes_coleta",
        ["plataforma_id", "categoria_id"],
    )

    op.create_foreign_key(
        "fk_config_coleta_categoria_plataforma",
        "configuracoes_coleta",
        "plataforma_categoria",
        ["categoria_id", "plataforma_id"],
        ["id", "plataforma_id"],
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Esta migração não possui downgrade automático seguro."
    )
