from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CredencialDivulgacaoCreate(BaseModel):
    plataforma_divulgacao_id: int = Field(gt=0)
    nome_credencial: str = Field(min_length=1, max_length=100)
    tipo_credencial: str = Field(min_length=1, max_length=50)
    valor: str = Field(min_length=1)


class CredencialDivulgacaoStatusUpdate(BaseModel):
    status_credencial: str = Field(pattern="^(ativa|inativa)$")


class CredencialDivulgacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_divulgacao_id: int
    nome_credencial: str
    tipo_credencial: str
    status_credencial: str
    created_at: datetime
    updated_at: datetime
