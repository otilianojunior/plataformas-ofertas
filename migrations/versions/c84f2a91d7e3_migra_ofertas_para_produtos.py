"""Migra ofertas para produtos e centraliza links de afiliados."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c84f2a91d7e3"
down_revision: Union[str, None] = "7e66baf315b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove o índice parcial antes de alterar a coluna utilizada por ele.
    op.execute("DROP INDEX IF EXISTS uq_publicacao_ativa_por_destino")

    # A tabela está vazia. Os links passam a pertencer diretamente ao produto.
    op.drop_table("links_afiliados")

    # Renomeia a tabela principal e os campos preservados.
    op.rename_table("ofertas", "produtos")

    op.alter_column(
        "produtos",
        "affiliate_url",
        new_column_name="url_afiliada",
    )
    op.alter_column(
        "produtos",
        "coletada_em",
        new_column_name="primeira_coleta_em",
    )

    # Remove restrições antigas que serão substituídas.
    op.drop_constraint(
        "ck_oferta_expiracao_posterior_coleta",
        "produtos",
        type_="check",
    )
    op.drop_constraint(
        "ck_oferta_desconto_valido",
        "produtos",
        type_="check",
    )
    op.drop_constraint(
        "ck_oferta_preco_atual_positivo",
        "produtos",
        type_="check",
    )
    op.drop_constraint(
        "ck_oferta_preco_original_nao_negativo",
        "produtos",
        type_="check",
    )
    op.drop_constraint(
        "uq_oferta_plataforma_item_externo",
        "produtos",
        type_="unique",
    )

    # Atualiza a chave estrangeira composta da categoria.
    op.drop_constraint(
        "fk_oferta_categoria_mesma_plataforma",
        "produtos",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_produto_categoria_mesma_plataforma",
        "produtos",
        "plataforma_categoria",
        ["categoria_id", "plataforma_id"],
        ["id", "plataforma_id"],
    )

    # Atualiza a referência do histórico de preços.
    op.drop_constraint(
        "historico_precos_oferta_id_fkey",
        "historico_precos",
        type_="foreignkey",
    )
    op.alter_column(
        "historico_precos",
        "oferta_id",
        new_column_name="produto_id",
    )
    op.create_foreign_key(
        "historico_precos_produto_id_fkey",
        "historico_precos",
        "produtos",
        ["produto_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Atualiza a referência das publicações.
    op.drop_constraint(
        "publicacoes_oferta_id_fkey",
        "publicacoes",
        type_="foreignkey",
    )
    op.alter_column(
        "publicacoes",
        "oferta_id",
        new_column_name="produto_id",
    )
    op.create_foreign_key(
        "publicacoes_produto_id_fkey",
        "publicacoes",
        "produtos",
        ["produto_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Novos campos do produto.
    op.add_column(
        "produtos",
        sa.Column("id_produto_plataforma", sa.String(150), nullable=True),
    )
    op.add_column(
        "produtos",
        sa.Column(
            "disponivel",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "produtos",
        sa.Column(
            "status_monitoramento",
            sa.String(20),
            server_default=sa.text("'ativo'"),
            nullable=False,
        ),
    )
    op.add_column(
        "produtos",
        sa.Column(
            "elegivel_divulgacao",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "produtos",
        sa.Column(
            "status_link_afiliado",
            sa.String(20),
            server_default=sa.text("'pendente'"),
            nullable=False,
        ),
    )
    op.add_column(
        "produtos",
        sa.Column("metodo_geracao_link_afiliado", sa.String(20), nullable=True),
    )
    op.add_column(
        "produtos",
        sa.Column("identificador_rastreamento", sa.String(150), nullable=True),
    )
    op.add_column(
        "produtos",
        sa.Column("erro_geracao_link_afiliado", sa.Text(), nullable=True),
    )
    op.add_column(
        "produtos",
        sa.Column(
            "link_afiliado_gerado_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "produtos",
        sa.Column(
            "ultima_coleta_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "produtos",
        sa.Column(
            "proxima_coleta_em",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Mantém os produtos antigos ativos no monitoramento.
    # A elegibilidade será calculada pelo serviço conforme as regras atuais.
    op.execute(
        """
        UPDATE produtos
        SET
            status_monitoramento = 'ativo',
            disponivel = TRUE,
            elegivel_divulgacao = FALSE,
            status_link_afiliado = CASE
                WHEN url_afiliada IS NOT NULL THEN 'gerado'
                ELSE 'pendente'
            END,
            ultima_coleta_em = primeira_coleta_em
        """
    )

    op.alter_column(
        "produtos",
        "ultima_coleta_em",
        nullable=False,
        server_default=sa.func.now(),
    )

    # Remove campos que não existem mais no modelo de produto.
    op.drop_column("produtos", "status_oferta")
    op.drop_column("produtos", "expira_em")

    # Restrições do novo modelo.
    op.create_unique_constraint(
        "uq_produto_plataforma_item_externo",
        "produtos",
        ["plataforma_id", "id_item_plataforma"],
    )
    op.create_check_constraint(
        "ck_produto_preco_atual_positivo",
        "produtos",
        "preco_atual > 0",
    )
    op.create_check_constraint(
        "ck_produto_preco_original_nao_negativo",
        "produtos",
        "preco_original IS NULL OR preco_original >= 0",
    )
    op.create_check_constraint(
        "ck_produto_desconto_valido",
        "produtos",
        "percentual_desconto IS NULL OR "
        "(percentual_desconto >= 0 AND percentual_desconto <= 100)",
    )
    op.create_check_constraint(
        "ck_produto_status_monitoramento_valido",
        "produtos",
        "status_monitoramento IN ('ativo', 'pausado', 'encerrado')",
    )
    op.create_check_constraint(
        "ck_produto_status_link_afiliado_valido",
        "produtos",
        "status_link_afiliado IN ('pendente', 'gerado', 'erro')",
    )
    op.create_check_constraint(
        "ck_produto_metodo_link_afiliado_valido",
        "produtos",
        "metodo_geracao_link_afiliado IS NULL OR "
        "metodo_geracao_link_afiliado IN ('manual', 'api')",
    )

    # Renomeia índices existentes para refletir o novo modelo.
    op.execute(
        "ALTER INDEX ix_ofertas_categoria_id "
        "RENAME TO ix_produtos_categoria_id"
    )
    op.execute(
        "ALTER INDEX ix_ofertas_plataforma_id "
        "RENAME TO ix_produtos_plataforma_id"
    )
    op.execute(
        "ALTER INDEX ix_historico_precos_oferta_id "
        "RENAME TO ix_historico_precos_produto_id"
    )
    op.execute(
        "ALTER INDEX ix_publicacoes_oferta_id "
        "RENAME TO ix_publicacoes_produto_id"
    )

    op.create_index(
        "ix_produtos_id_produto_plataforma",
        "produtos",
        ["id_produto_plataforma"],
    )
    op.create_index(
        "ix_produtos_ultima_coleta_em",
        "produtos",
        ["ultima_coleta_em"],
    )
    op.create_index(
        "ix_produtos_proxima_coleta_em",
        "produtos",
        ["proxima_coleta_em"],
    )

    # Mantém a proteção contra publicações duplicadas por produto e destino.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_publicacao_ativa_por_destino
        ON publicacoes (produto_id, destino_divulgacao_id)
        WHERE status_publicacao IN ('pendente', 'publicada')
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Esta migração de transição não possui downgrade automático."
    )
