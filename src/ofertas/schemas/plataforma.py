from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlataformaCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nome: str = Field(min_length=1, max_length=100)
    status_plataforma: bool = True


class PlataformaStatusUpdate(BaseModel):
    status_plataforma: bool


class PlataformaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nome: str
    status_plataforma: bool
    created_at: datetime
    updated_at: datetime
