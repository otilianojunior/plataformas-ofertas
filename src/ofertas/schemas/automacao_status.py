from datetime import datetime
from pydantic import BaseModel

from ofertas.schemas.ciclo_publicacao import CicloPublicacaoResponse
from ofertas.schemas.configuracao_sistema import ConfiguracaoSistemaResponse
from ofertas.schemas.janela_execucao import JanelaExecucaoResponse


class MonitorAutomacoesStatus(BaseModel):
    status: str
    online: bool
    ultimo_sinal_em: datetime | None
    limite_sinal_minutos: int


class ColetaMarketplaceStatus(BaseModel):
    plataforma_id: int | None
    codigo: str
    nome: str
    plataforma_ativa: bool
    automacao_habilitada: bool
    status: str
    ultima_execucao_id: int | None
    ultima_execucao_status: str | None
    ultima_execucao_iniciada_em: datetime | None
    ultima_execucao_finalizada_em: datetime | None
    ultima_execucao_erro: str | None
    quantidade_encontrada: int | None
    quantidade_processada: int | None
    quantidade_ignorada: int | None
    proxima_execucao_em: datetime | None


class DestinoPublicacaoStatus(BaseModel):
    configuracao_id: int
    destino_id: int
    nome_destino: str
    codigo_canal: str
    canal_ativo: bool
    destino_ativo: bool
    configuracao_ativa: bool
    intervalo_publicacao_minutos: int
    ultima_execucao_ciclo_em: datetime | None
    proxima_execucao_em: datetime | None
    status: str
    ultima_publicacao_id: int | None
    ultima_publicacao_status: str | None
    ultima_publicacao_em: datetime | None
    ultima_publicacao_erro: str | None
    ciclo_em_andamento: bool
    ultimo_ciclo: CicloPublicacaoResponse | None


class AutomacoesStatusResponse(BaseModel):
    consultado_em: datetime
    fuso_horario: str
    horario_permitido: bool
    configuracoes_sistema: ConfiguracaoSistemaResponse
    monitor: MonitorAutomacoesStatus
    janelas_execucao: list[JanelaExecucaoResponse]
    coletas: list[ColetaMarketplaceStatus]
    destinos_publicacao: list[DestinoPublicacaoStatus]
    publicacao_whatsapp_habilitada: bool
    publicacao_whatsapp_status: str
