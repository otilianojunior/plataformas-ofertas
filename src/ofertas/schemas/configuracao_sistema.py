from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConfiguracaoSistemaUpdate(BaseModel):
    intervalo_coleta_minutos: int = Field(gt=0)


class ConfiguracaoSistemaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    intervalo_coleta_minutos: int
    coleta_mercado_livre_ativa: bool
    coleta_shopee_ativa: bool
    publicacao_telegram_ativa: bool
    publicacao_whatsapp_ativa: bool
    agendador_ultimo_sinal_em: datetime | None
    created_at: datetime
    updated_at: datetime
