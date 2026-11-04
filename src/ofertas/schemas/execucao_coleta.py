from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExecucaoColetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_id: int
    iniciada_em: datetime
    finalizada_em: datetime | None
    status: str
    quantidade_encontrada: int = Field(ge=0)
    quantidade_processada: int = Field(ge=0)
    quantidade_ignorada: int = Field(ge=0)
    erro: str | None