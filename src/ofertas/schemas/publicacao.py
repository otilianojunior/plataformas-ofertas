from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PublicacaoResponse(BaseModel):
    """Dados retornados sobre uma tentativa de publicação."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    produto_id: int
    destino_divulgacao_id: int
    preco_divulgado: Decimal
    percentual_desconto_divulgado: Decimal | None
    status_publicacao: str
    tentativas: int
    publicada_em: datetime | None
    erro: str | None
    created_at: datetime
    updated_at: datetime


class ResultadoPublicacaoDestino(BaseModel):
    """Resultado da publicação manual em um grupo."""

    destino_id: int
    nome_destino: str
    codigo_canal: str
    status: Literal["publicada", "falhou", "ignorada"]
    motivo: str | None = None
    publicacao: PublicacaoResponse | None = None


class PublicacaoManualResponse(BaseModel):
    """Resumo da publicação manual em todos os grupos da categoria."""

    produto_id: int
    categoria_id: int
    nome_categoria: str
    total_destinos: int
    publicadas: int
    falhas: int
    ignoradas: int
    resultados: list[ResultadoPublicacaoDestino]
