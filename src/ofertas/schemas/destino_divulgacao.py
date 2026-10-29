from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DestinoDivulgacaoCreate(BaseModel):
    plataforma_divulgacao_id: int = Field(gt=0)
    credencial_divulgacao_id: int = Field(gt=0)
    identificador_destino: str = Field(min_length=1, max_length=255)
    nome_destino: str = Field(min_length=1, max_length=150)
    status_destino: bool = True


class DestinoDivulgacaoStatusUpdate(BaseModel):
    status_destino: bool


class DestinoDivulgacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_divulgacao_id: int
    credencial_divulgacao_id: int | None
    identificador_destino: str
    nome_destino: str
    status_destino: bool
    created_at: datetime
    updated_at: datetime
