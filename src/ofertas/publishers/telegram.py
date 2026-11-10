from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from ofertas.core.security import descriptografar_credencial
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.models.produto import Produto
from ofertas.models.publicacao import Publicacao
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


class TelegramPublisher:
    """Publica produtos elegíveis em destinos do Telegram."""

    def __init__(
        self,
        credencial_repository: CredencialDivulgacaoRepository | None = None,
        destino_repository: DestinoDivulgacaoRepository | None = None,
        publicacao_repository: PublicacaoRepository | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.credencial_repository = (
            credencial_repository or CredencialDivulgacaoRepository()
        )
        self.destino_repository = (
            destino_repository or DestinoDivulgacaoRepository()
        )
        self.publicacao_repository = (
            publicacao_repository or PublicacaoRepository()
        )
        self.timeout = timeout

    def publicar(
        self,
        session: Session,
        produto: Produto,
        destino_id: int,
        publicacao: Publicacao | None = None,
    ) -> Publicacao:
        """Publica um produto sem confirmar a transação da sessão."""

        if not produto.url_afiliada:
            raise ValueError(
                "O produto não pode ser publicado sem link de afiliado."
            )

        if produto.status_link_afiliado != "gerado":
            raise ValueError(
                "O link de afiliado do produto não está validado."
            )

        if not produto.elegivel_divulgacao:
            raise ValueError(
                "O produto não atende aos critérios de divulgação."
            )

        if not produto.disponivel:
            raise ValueError(
                "Não é possível publicar um produto indisponível."
            )

        if produto.status_monitoramento != "ativo":
            raise ValueError(
                "O monitoramento do produto não está ativo."
            )

        destino = self.destino_repository.buscar_por_id(
            session,
            destino_id,
        )

        if destino is None:
            raise LookupError("Destino de divulgação não encontrado.")

        if not destino.status_destino:
            raise ValueError("O destino de divulgação está inativo.")

        plataforma = session.get(
            PlataformaDivulgacao,
            destino.plataforma_divulgacao_id,
        )

        if plataforma is None:
            raise LookupError("Canal de divulgação não encontrado.")

        if not plataforma.status_plataforma:
            raise ValueError("O canal de divulgação está inativo.")

        if plataforma.codigo.lower() != "telegram":
            raise ValueError(
                "O destino selecionado não é do Telegram."
            )

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

        if credencial.plataforma_divulgacao_id != plataforma.id:
            raise ValueError(
                "A credencial não pertence ao canal de divulgação "
                "do destino."
            )

        if credencial.tipo_credencial != "bot_telegram":
            raise ValueError(
                "A credencial não é um token de bot do Telegram."
            )

        plataforma_origem = session.get(
            Plataforma,
            produto.plataforma_id,
        )

        if plataforma_origem is None:
            raise LookupError(
                "Plataforma de origem do produto não encontrada."
            )

        if publicacao is None:
            publicacao_pendente = (
                self.publicacao_repository.buscar_ativa(
                    session,
                    produto.id,
                    destino.id,
                )
            )

            if publicacao_pendente is not None:
                raise ValueError(
                    "Este produto já possui uma publicação pendente "
                    "neste destino."
                )

            publicacao = self.publicacao_repository.criar(
                session,
                produto_id=produto.id,
                destino_id=destino.id,
                preco_divulgado=produto.preco_atual,
                percentual_desconto_divulgado=(
                    produto.percentual_desconto
                ),
                tentativas=1,
            )

        else:
            if publicacao.status_publicacao != "pendente":
                raise ValueError(
                    "A publicação informada não está pendente."
                )

            if (
                publicacao.produto_id != produto.id
                or publicacao.destino_divulgacao_id != destino.id
            ):
                raise ValueError(
                    "A publicação pendente não corresponde "
                    "ao produto e destino informados."
                )

        try:
            mensagem = formatar_mensagem(
                produto,
                plataforma_origem.nome,
            )

            token = descriptografar_credencial(
                credencial.valor_criptografado
            )

            dados = {
                "chat_id": destino.identificador_destino,
                "caption" if produto.imagem_url else "text": mensagem,
                "parse_mode": "HTML",
            }

            if produto.imagem_url:
                endpoint = (
                    f"https://api.telegram.org/bot{token}/sendPhoto"
                )
                dados["photo"] = produto.imagem_url
            else:
                endpoint = (
                    f"https://api.telegram.org/bot{token}/sendMessage"
                )

            resposta = httpx.post(
                endpoint,
                data=dados,
                timeout=self.timeout,
            )
            resposta.raise_for_status()
            resultado = resposta.json()

            if (
                not isinstance(resultado, dict)
                or resultado.get("ok") is not True
            ):
                raise RuntimeError(
                    "O Telegram não confirmou a publicação."
                )

        except Exception as erro:
            publicacao.status_publicacao = "falhou"

            if isinstance(erro, httpx.HTTPStatusError):
                try:
                    detalhe = erro.response.json().get(
                        "description",
                        "",
                    )
                except (ValueError, AttributeError):
                    detalhe = ""

                publicacao.erro = (
                    f"HTTP {erro.response.status_code}: "
                    f"{detalhe or 'Erro retornado pelo Telegram'}"
                )[:500]
            else:
                publicacao.erro = type(erro).__name__

            session.flush()
            return publicacao

        publicacao.status_publicacao = "publicada"
        publicacao.publicada_em = datetime.now(timezone.utc)
        publicacao.erro = None

        session.flush()
        return publicacao
