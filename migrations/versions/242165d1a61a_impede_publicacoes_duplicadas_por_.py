"""Impede publicações duplicadas por oferta e destino."""

from typing import Sequence, Union

from alembic import op


revision: str = "242165d1a61a"
down_revision: Union[str, None] = "10bdca924edd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_publicacao_ativa_por_destino
        ON publicacoes (oferta_id, destino_divulgacao_id)
        WHERE status_publicacao IN ('pendente', 'publicada')
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS uq_publicacao_ativa_por_destino"
    )
