from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoriaCreate(BaseModel):
    plataforma_id: int = Field(gt=0)
    id_categoria_plataforma: str = Field(min_length=1, max_length=100)
    nome_categoria: str = Field(min_length=1, max_length=150)
    etiqueta_afiliado: str | None = Field(default=None, max_length=150)
    destino_divulgacao_id: int | None = Field(default=None, gt=0)
    desconto_minimo_percentual: Decimal = Field(ge=10, le=100)
    status_categoria: bool = True


class CategoriaStatusUpdate(BaseModel):
    status_categoria: bool


class CategoriaEtiquetaAfiliadoUpdate(BaseModel):
    etiqueta_afiliado: str | None = Field(default=None, max_length=150)


class CategoriaDestinoDivulgacaoUpdate(BaseModel):
    destino_divulgacao_id: int | None = Field(gt=0)


class CategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_id: int
    id_categoria_plataforma: str
    nome_categoria: str
    etiqueta_afiliado: str | None
    destino_divulgacao_id: int | None
    desconto_minimo_percentual: Decimal
    limite_produtos_selecao: int
    selecao_renovada_em: datetime | None
    status_categoria: bool
    created_at: datetime
    updated_at: datetime


class CategoriaDescontoUpdate(BaseModel):
    desconto_minimo_percentual: Decimal = Field(ge=10, le=100)