"""Fuso horário e normalização de datas usados em todo o sistema."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")
NOME_FUSO_HORARIO = "America/Sao_Paulo"


def garantir_utc(data: datetime) -> datetime:
    """Trata datas sem fuso como UTC (padrão das colunas do banco)."""

    if data.tzinfo is None:
        return data.replace(tzinfo=timezone.utc)

    return data
