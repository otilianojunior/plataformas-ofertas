from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConfiguracaoSistemaUpdate(BaseModel):
    intervalo_coleta_minutos: int = Field(gt=0)


class ConfiguracaoSistemaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    intervalo_coleta_minutos: int
    created_at: datetime
    updated_at: datetime
