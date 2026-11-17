from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.core.tempo import (
    FUSO_HORARIO,
    NOME_FUSO_HORARIO,
    garantir_utc,
)
from ofertas.models.configuracao_divulgacao import ConfiguracaoDivulgacao
from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.execucao_coleta import ExecucaoColeta
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.models.publicacao import Publicacao
from ofertas.repositories.ciclo_publicacao_repository import (
    CicloPublicacaoRepository,
)
from ofertas.services.configuracao_sistema_service import (
    CAMPO_PUBLICACAO_POR_CANAL,
    ConfiguracaoSistemaService,
    publicacao_do_canal_ativa,
)
from ofertas.services.janela_execucao_service import (
    JanelaExecucaoService,
)



class AutomacaoStatusService:
    """Consolida o estado das automações usando os registros existentes."""

    MARKETPLACES = {
        "mercado_livre": (
            "Mercado Livre",
            "coleta_mercado_livre_ativa",
        ),
        "shopee": (
            "Shopee",
            "coleta_shopee_ativa",
        ),
    }

    def __init__(
        self,
        configuracao_sistema_service: ConfiguracaoSistemaService | None = None,
        janela_execucao_service: JanelaExecucaoService | None = None,
        ciclo_repository: CicloPublicacaoRepository | None = None,
    ) -> None:
        self.configuracao_sistema_service = (
            configuracao_sistema_service or ConfiguracaoSistemaService()
        )
        self.janela_execucao_service = (
            janela_execucao_service or JanelaExecucaoService()
        )
        self.ciclo_repository = (
            ciclo_repository or CicloPublicacaoRepository()
        )

    @classmethod
    def _proxima_data_permitida(
        cls,
        primeira_data: datetime,
        janelas_ativas: list,
        agora: datetime,
    ) -> datetime | None:
        """Encontra o próximo instante permitido no horário de Brasília.

        Uma execução atrasada (data prevista no passado) é considerada a
        partir de agora, para nunca apontar para uma janela que já passou.
        """

        primeira_data_local = max(
            garantir_utc(primeira_data),
            garantir_utc(agora),
        ).astimezone(FUSO_HORARIO)

        if not janelas_ativas:
            return primeira_data_local

        janelas_ordenadas = sorted(
            janelas_ativas,
            key=lambda janela: janela.hora_inicio,
        )

        for deslocamento in range(8):
            dia = primeira_data_local.date() + timedelta(
                days=deslocamento
            )

            for janela in janelas_ordenadas:
                inicio = datetime.combine(
                    dia,
                    janela.hora_inicio,
                    tzinfo=FUSO_HORARIO,
                )
                fim = datetime.combine(
                    dia,
                    janela.hora_fim,
                    tzinfo=FUSO_HORARIO,
                )

                candidata = max(primeira_data_local, inicio)

                if candidata < fim:
                    return candidata

        return None

    @staticmethod
    def _buscar_ultima_coleta(
        session: Session,
        plataforma_id: int,
    ) -> ExecucaoColeta | None:
        return session.scalar(
            select(ExecucaoColeta)
            .where(ExecucaoColeta.plataforma_id == plataforma_id)
            .order_by(
                ExecucaoColeta.iniciada_em.desc(),
                ExecucaoColeta.id.desc(),
            )
            .limit(1)
        )

    @staticmethod
    def _buscar_ultima_publicacao(
        session: Session,
        destino_id: int,
    ) -> Publicacao | None:
        return session.scalar(
            select(Publicacao)
            .where(Publicacao.destino_divulgacao_id == destino_id)
            .order_by(
                Publicacao.created_at.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
        )

    def consultar(self, session: Session) -> dict:
        configuracao = self.configuracao_sistema_service.buscar(session)

        agora_utc = datetime.now(timezone.utc)
        agora_local = agora_utc.astimezone(FUSO_HORARIO)

        ultimo_sinal = configuracao.agendador_ultimo_sinal_em
        monitor_online = False

        if ultimo_sinal is not None:
            monitor_online = (
                agora_utc - garantir_utc(ultimo_sinal)
                <= timedelta(
                    minutes=self.configuracao_sistema_service.TEMPO_LIMITE_AGENDADOR_MINUTOS
                )
            )

        janelas = self.janela_execucao_service.listar(session)
        janelas_ativas = [
            janela for janela in janelas if janela.ativa
        ]

        horario_permitido = (
            self.janela_execucao_service.esta_em_horario_permitido(
                session,
                agora_utc,
            )
        )

        monitor = {
            "status": "online" if monitor_online else "offline",
            "online": monitor_online,
            "ultimo_sinal_em": ultimo_sinal,
            "limite_sinal_minutos": (
                self.configuracao_sistema_service.TEMPO_LIMITE_AGENDADOR_MINUTOS
            ),
        }

        # Status individual das coletas de cada marketplace.
        plataformas = session.scalars(
            select(Plataforma)
            .where(
                Plataforma.codigo.in_(list(self.MARKETPLACES))
            )
            .order_by(Plataforma.codigo)
        ).all()

        plataformas_por_codigo = {
            plataforma.codigo: plataforma
            for plataforma in plataformas
        }

        coletas = []

        for codigo, (nome, atributo_ativo) in self.MARKETPLACES.items():
            plataforma = plataformas_por_codigo.get(codigo)
            plataforma_ativa = (
                plataforma.status_plataforma
                if plataforma is not None
                else False
            )

            habilitada = (
                configuracao.automacoes_ativas
                and getattr(configuracao, atributo_ativo)
            )

            ultima = None

            if plataforma is not None:
                ultima = self._buscar_ultima_coleta(
                    session,
                    plataforma.id,
                )

            proxima_execucao = None

            if (
                plataforma is not None
                and plataforma_ativa
                and habilitada
                and monitor_online
                and not (
                    ultima is not None
                    and ultima.status == "em_andamento"
                )
            ):
                if ultima is None:
                    primeira_data = agora_local
                else:
                    referencia = (
                        ultima.finalizada_em
                        or ultima.iniciada_em
                    )
                    primeira_data = (
                        garantir_utc(referencia)
                        + timedelta(
                            minutes=configuracao.intervalo_coleta_minutos
                        )
                    )

                proxima_execucao = self._proxima_data_permitida(
                    primeira_data,
                    janelas_ativas,
                    agora_local,
                )

            if plataforma is None:
                status_coleta = "plataforma_nao_cadastrada"
            elif ultima is not None and ultima.status == "em_andamento":
                status_coleta = "executando"
            elif not configuracao.automacoes_ativas or not getattr(
                configuracao,
                atributo_ativo,
            ):
                status_coleta = "pausada"
            elif not plataforma_ativa:
                status_coleta = "plataforma_inativa"
            elif not monitor_online:
                status_coleta = "monitor_offline"
            elif not horario_permitido:
                status_coleta = "fora_da_janela"
            elif ultima is not None and ultima.status == "falhou":
                status_coleta = "falhou"
            elif (
                proxima_execucao is not None
                and proxima_execucao <= agora_local
            ):
                status_coleta = "pronta_para_execucao"
            else:
                status_coleta = "aguardando_intervalo"

            coletas.append({
                "plataforma_id": (
                    plataforma.id if plataforma is not None else None
                ),
                "codigo": codigo,
                "nome": nome,
                "plataforma_ativa": plataforma_ativa,
                "automacao_habilitada": bool(habilitada),
                "status": status_coleta,
                "ultima_execucao_id": (
                    ultima.id if ultima is not None else None
                ),
                "ultima_execucao_status": (
                    ultima.status if ultima is not None else None
                ),
                "ultima_execucao_iniciada_em": (
                    ultima.iniciada_em if ultima is not None else None
                ),
                "ultima_execucao_finalizada_em": (
                    ultima.finalizada_em if ultima is not None else None
                ),
                "ultima_execucao_erro": (
                    ultima.erro if ultima is not None else None
                ),
                "quantidade_encontrada": (
                    ultima.quantidade_encontrada
                    if ultima is not None else None
                ),
                "quantidade_processada": (
                    ultima.quantidade_processada
                    if ultima is not None else None
                ),
                "quantidade_ignorada": (
                    ultima.quantidade_ignorada
                    if ultima is not None else None
                ),
                "proxima_execucao_em": proxima_execucao,
            })

        # Status de publicação por destino configurado.
        consulta_destinos = (
            select(
                ConfiguracaoDivulgacao,
                DestinoDivulgacao,
                PlataformaDivulgacao,
            )
            .join(
                DestinoDivulgacao,
                DestinoDivulgacao.id
                == ConfiguracaoDivulgacao.destino_divulgacao_id,
            )
            .join(
                PlataformaDivulgacao,
                PlataformaDivulgacao.id
                == DestinoDivulgacao.plataforma_divulgacao_id,
            )
            .order_by(DestinoDivulgacao.id)
        )

        registros_destinos = session.execute(
            consulta_destinos
        ).all()

        destinos_publicacao = []

        for config_destino, destino, canal in registros_destinos:
            ultima_publicacao = self._buscar_ultima_publicacao(
                session,
                destino.id,
            )

            ultima_execucao_ciclo = (
                config_destino.ultima_execucao_publicacao_em
            )

            ultimo_ciclo = self.ciclo_repository.buscar_ultimo(
                session,
                destino.id,
            )
            ciclo_em_andamento = (
                ultimo_ciclo is not None
                and ultimo_ciclo.status == "em_andamento"
                and monitor_online
            )

            proxima_execucao = None
            habilitada_globalmente = configuracao.automacoes_ativas

            if canal.codigo in CAMPO_PUBLICACAO_POR_CANAL:
                habilitada_globalmente = publicacao_do_canal_ativa(
                    configuracao,
                    canal.codigo,
                )

                pode_executar = (
                    habilitada_globalmente
                    and config_destino.status_configuracao
                    and destino.status_destino
                    and canal.status_plataforma
                    and monitor_online
                )

                if pode_executar and not ciclo_em_andamento:
                    primeira_data = (
                        agora_local
                        if ultima_execucao_ciclo is None
                        else (
                            garantir_utc(
                                ultima_execucao_ciclo
                            )
                            + timedelta(
                                minutes=config_destino.intervalo_publicacao_minutos
                            )
                        )
                    )

                    proxima_execucao = (
                        self._proxima_data_permitida(
                            primeira_data,
                            janelas_ativas,
                            agora_local,
                        )
                    )

                if not habilitada_globalmente or not config_destino.status_configuracao:
                    status_publicacao = "pausada"
                elif not destino.status_destino or not canal.status_plataforma:
                    status_publicacao = "destino_inativo"
                elif not monitor_online:
                    status_publicacao = "monitor_offline"
                elif ciclo_em_andamento:
                    status_publicacao = "publicando"
                elif not horario_permitido:
                    status_publicacao = "fora_da_janela"
                elif (
                    proxima_execucao is not None
                    and proxima_execucao > agora_local
                ):
                    status_publicacao = "aguardando_intervalo"
                else:
                    status_publicacao = "pronta_para_execucao"

            else:
                status_publicacao = "canal_nao_suportado"

            destinos_publicacao.append({
                "configuracao_id": config_destino.id,
                "destino_id": destino.id,
                "nome_destino": destino.nome_destino,
                "codigo_canal": canal.codigo,
                "canal_ativo": canal.status_plataforma,
                "destino_ativo": destino.status_destino,
                "configuracao_ativa": config_destino.status_configuracao,
                "intervalo_publicacao_minutos": (
                    config_destino.intervalo_publicacao_minutos
                ),
                "ultima_execucao_ciclo_em": ultima_execucao_ciclo,
                "proxima_execucao_em": proxima_execucao,
                "status": status_publicacao,
                "ultima_publicacao_id": (
                    ultima_publicacao.id
                    if ultima_publicacao is not None else None
                ),
                "ultima_publicacao_status": (
                    ultima_publicacao.status_publicacao
                    if ultima_publicacao is not None else None
                ),
                "ultima_publicacao_em": (
                    (
                        ultima_publicacao.publicada_em
                        or ultima_publicacao.created_at
                    )
                    if ultima_publicacao is not None else None
                ),
                "ultima_publicacao_erro": (
                    ultima_publicacao.erro
                    if ultima_publicacao is not None else None
                ),
                "ciclo_em_andamento": ciclo_em_andamento,
                "ultimo_ciclo": ultimo_ciclo,
            })

        return {
            "consultado_em": agora_local,
            "fuso_horario": NOME_FUSO_HORARIO,
            "horario_permitido": horario_permitido,
            "configuracoes_sistema": configuracao,
            "monitor": monitor,
            "janelas_execucao": janelas,
            "coletas": coletas,
            "destinos_publicacao": destinos_publicacao,
            "publicacao_whatsapp_habilitada": (
                configuracao.publicacao_whatsapp_ativa
            ),
            "publicacao_whatsapp_status": (
                "ativa"
                if publicacao_do_canal_ativa(configuracao, "whatsapp")
                else "pausada"
            ),
        }
