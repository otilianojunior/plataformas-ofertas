
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PublicacaoResponse(BaseModel):
    """Dados retornados sobre uma tentativa de publicação."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    produto_id: int
    destino_divulgacao_id: int
    preco_divulgado: Decimal
    status_publicacao: str
    tentativas: int
    publicada_em: datetime | None
    erro: str | None
    created_at: datetime
    updated_at: datetime
