from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CredencialPlataformaCreate(BaseModel):
    plataforma_id: int = Field(gt=0)
    tipo_credencial: str = Field(min_length=1, max_length=50)
    valor: str = Field(min_length=1)


class CredencialPlataformaStatusUpdate(BaseModel):
    status_credencial: str = Field(pattern="^(ativa|inativa)$")


class CredencialPlataformaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_id: int
    tipo_credencial: str
    status_credencial: str
    created_at: datetime
    updated_at: datetime
