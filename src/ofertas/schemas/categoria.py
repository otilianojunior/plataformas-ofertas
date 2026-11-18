from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoriaCreate(BaseModel):
    plataforma_id: int = Field(gt=0)
    id_categoria_plataforma: str = Field(min_length=1, max_length=100)
    nome_categoria: str = Field(min_length=1, max_length=150)
    etiqueta_afiliado: str | None = Field(default=None, max_length=150)
    termo_busca: str | None = Field(
        default=None,
        max_length=150,
        description=(
            "Opcional. Coleta por busca (ex.: 'headset razer') dentro da "
            "categoria da loja, em vez de só os destaques da categoria."
        ),
    )
    grupos_ids: list[int] = Field(
        default_factory=list,
        description="Grupos que vão receber as publicações da categoria.",
    )
    desconto_minimo_percentual: Decimal = Field(ge=10, le=100)
    status_categoria: bool = True


class CategoriaStatusUpdate(BaseModel):
    status_categoria: bool


class CategoriaPrioridadeUpdate(BaseModel):
    prioritaria: bool


class CategoriaEtiquetaAfiliadoUpdate(BaseModel):
    etiqueta_afiliado: str | None = Field(default=None, max_length=150)


class CategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_id: int
    id_categoria_plataforma: str
    nome_categoria: str
    termo_busca: str | None
    etiqueta_afiliado: str | None
    desconto_minimo_percentual: Decimal
    status_categoria: bool
    prioritaria: bool
    created_at: datetime
    updated_at: datetime


class CategoriaExclusaoResponse(BaseModel):
    categoria_id: int
    produtos_excluidos: int


class CategoriaDescontoUpdate(BaseModel):
    desconto_minimo_percentual: Decimal = Field(ge=10, le=100)