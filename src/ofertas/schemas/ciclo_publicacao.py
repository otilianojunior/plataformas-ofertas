from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CicloPublicacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    destino_divulgacao_id: int
    status: str
    iniciado_em: datetime
    finalizado_em: datetime | None
    atualizado_em: datetime
    quantidade_candidatos: int
    quantidade_publicada: int
    quantidade_falha: int
    quantidade_ignorada: int
    erro: str | None
