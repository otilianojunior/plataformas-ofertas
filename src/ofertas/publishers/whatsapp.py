import logging
from datetime import datetime

from sqlalchemy.orm import Session

from ofertas.core.config import Settings, get_settings
from ofertas.core.tempo import FUSO_HORARIO
from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.models.produto import Produto
from ofertas.publishers.base import PublisherBase
from ofertas.publishers.mensagem import formatar_mensagem_whatsapp
from ofertas.publishers.whatsapp_web import (
    WhatsAppSessaoError,
    WhatsAppWebClient,
    WhatsAppWebError,
)
from ofertas.repositories.destino_divulgacao_repository import (
    DestinoDivulgacaoRepository,
)
from ofertas.repositories.publicacao_repository import PublicacaoRepository


logger = logging.getLogger(__name__)


class WhatsAppPublisher(PublisherBase):
    """Publica nos grupos do WhatsApp pelo WhatsApp Web (não oficial).

    O identificador do grupo é o NOME do grupo exatamente como aparece no
    WhatsApp. Não precisa de credencial: a sessão fica no perfil do Chrome.
    """

    CODIGO_CANAL = "whatsapp"
    NOME_CANAL = "WhatsApp"

    def __init__(
        self,
        destino_repository: DestinoDivulgacaoRepository | None = None,
        publicacao_repository: PublicacaoRepository | None = None,
        cliente: WhatsAppWebClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(destino_repository, publicacao_repository)
        self.settings = settings or get_settings()
        self._cliente = cliente

    @property
    def cliente(self) -> WhatsAppWebClient:
        # Criado sob demanda: só abre o Chrome quando houver envio.
        if self._cliente is None:
            self._cliente = WhatsAppWebClient(settings=self.settings)
        return self._cliente

    def _preparar_envio(
        self,
        session: Session,
        destino: DestinoDivulgacao,
        canal: PlataformaDivulgacao,
    ) -> None:
        inicio_do_dia = datetime.now(FUSO_HORARIO).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        enviadas = self.publicacao_repository.contar_publicadas_canal_desde(
            session,
            self.CODIGO_CANAL,
            inicio_do_dia,
        )
        limite = self.settings.whatsapp_limite_diario

        if enviadas >= limite:
            raise ValueError(
                f"Limite diário do WhatsApp atingido ({enviadas}/{limite} "
                "mensagens hoje, somando todos os grupos)."
            )

    def _enviar(
        self,
        produto: Produto,
        destino: DestinoDivulgacao,
        nome_loja: str,
        contexto: None,
    ) -> None:
        self.cliente.enviar(
            destino.identificador_destino,
            formatar_mensagem_whatsapp(produto, nome_loja),
            produto.imagem_url,
        )

    def _ao_falhar(self, session: Session, erro: Exception) -> None:
        if not isinstance(erro, WhatsAppSessaoError):
            return

        configuracao = session.get(ConfiguracaoSistema, 1)

        if configuracao is not None and configuracao.publicacao_whatsapp_ativa:
            configuracao.publicacao_whatsapp_ativa = False
            logger.error(
                "Publicações no WhatsApp PAUSADAS automaticamente: %s "
                "Depois de resolver, reative em "
                "POST /configuracoes-sistema/automacoes/publicacao_whatsapp/ativar.",
                erro,
            )

    def _descrever_erro(self, erro: Exception) -> str:
        if isinstance(erro, WhatsAppWebError):
            return str(erro)
        return type(erro).__name__
