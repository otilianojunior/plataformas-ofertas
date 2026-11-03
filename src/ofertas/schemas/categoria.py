
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class CategoriaCreate(BaseModel):
    plataforma_id: int = Field(gt=0)
    id_categoria_plataforma: str = Field(min_length=1, max_length=100)
    nome_categoria: str = Field(min_length=1, max_length=150)
    desconto_minimo_percentual: Decimal = Field(ge=10, le=100)
    status_categoria: bool = True



class CategoriaStatusUpdate(BaseModel):
    status_categoria: bool


class CategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_id: int
    id_categoria_plataforma: str
    nome_categoria: str
    desconto_minimo_percentual: Decimal
    status_categoria: bool
    created_at: datetime
    updated_at: datetime

class CategoriaDescontoUpdate(BaseModel):
    desconto_minimo_percentual: Decimal = Field(ge=10, le=100)