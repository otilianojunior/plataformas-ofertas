import httpx
from sqlalchemy.orm import Session

from ofertas.core.security import descriptografar_credencial
from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.models.produto import Produto
from ofertas.publishers.base import PublisherBase
from ofertas.publishers.mensagem import formatar_mensagem
from ofertas.repositories.credencial_divulgacao_repository import (
    CredencialDivulgacaoRepository,
)
from ofertas.repositories.destino_divulgacao_repository import (
    DestinoDivulgacaoRepository,
)
from ofertas.repositories.publicacao_repository import (
    PublicacaoRepository,
)


class TelegramPublisher(PublisherBase):
    """Publica produtos elegíveis em destinos do Telegram (Bot API)."""

    CODIGO_CANAL = "telegram"
    NOME_CANAL = "Telegram"

    def __init__(
        self,
        credencial_repository: CredencialDivulgacaoRepository | None = None,
        destino_repository: DestinoDivulgacaoRepository | None = None,
        publicacao_repository: PublicacaoRepository | None = None,
        timeout: float = 20.0,
    ) -> None:
        super().__init__(destino_repository, publicacao_repository)
        self.credencial_repository = (
            credencial_repository or CredencialDivulgacaoRepository()
        )
        self.timeout = timeout

    def _preparar_envio(
        self,
        session: Session,
        destino: DestinoDivulgacao,
        canal: PlataformaDivulgacao,
    ) -> str:
        """Valida a credencial do bot e devolve o token."""

        if destino.credencial_divulgacao_id is None:
            raise ValueError(
                "O destino não possui credencial associada."
            )

        credencial = self.credencial_repository.buscar_por_id(
            session,
            destino.credencial_divulgacao_id,
        )

        if credencial is None:
            raise LookupError(
                "Credencial de divulgação não encontrada."
            )

        if credencial.status_credencial != "ativa":
            raise ValueError(
                "A credencial de divulgação está inativa."
            )

        if credencial.plataforma_divulgacao_id != canal.id:
            raise ValueError(
                "A credencial não pertence ao canal de divulgação "
                "do destino."
            )

        if credencial.tipo_credencial != "bot_telegram":
            raise ValueError(
                "A credencial não é um token de bot do Telegram."
            )

        return descriptografar_credencial(credencial.valor_criptografado)

    def _enviar(
        self,
        produto: Produto,
        destino: DestinoDivulgacao,
        nome_loja: str,
        contexto: str,
    ) -> None:
        mensagem = formatar_mensagem(produto, nome_loja)

        dados = {
            "chat_id": destino.identificador_destino,
            "caption" if produto.imagem_url else "text": mensagem,
            "parse_mode": "HTML",
        }

        if produto.imagem_url:
            metodo = "sendPhoto"
            dados["photo"] = produto.imagem_url
        else:
            metodo = "sendMessage"

        # A URL contém o token: nunca registrar nem gravar esta URL.
        resposta = httpx.post(
            f"https://api.telegram.org/bot{contexto}/{metodo}",
            data=dados,
            timeout=self.timeout,
        )
        resposta.raise_for_status()
        resultado = resposta.json()

        if not isinstance(resultado, dict) or resultado.get("ok") is not True:
            raise RuntimeError("O Telegram não confirmou a publicação.")

    def _descrever_erro(self, erro: Exception) -> str:
        if isinstance(erro, httpx.HTTPStatusError):
            try:
                detalhe = erro.response.json().get("description", "")
            except (ValueError, AttributeError):
                detalhe = ""

            return (
                f"HTTP {erro.response.status_code}: "
                f"{detalhe or 'Erro retornado pelo Telegram'}"
            )

        return type(erro).__name__
