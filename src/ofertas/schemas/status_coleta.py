from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class StatusColetaResponse(BaseModel):
    status_agendador: Literal["online", "offline"]
    status_coleta: Literal[
        "pausada",
        "executando",
        "falhou",
        "aguardando_execucao",
    ]

    coleta_mercado_livre_ativa: bool
    automacoes_ativas: bool
    agendador_ultimo_sinal_em: datetime | None

    ultima_execucao_id: int | None
    ultima_execucao_status: str | None
    ultima_execucao_iniciada_em: datetime | None
    ultima_execucao_finalizada_em: datetime | None

    proxima_execucao_em: datetime | None
