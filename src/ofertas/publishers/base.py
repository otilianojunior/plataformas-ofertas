"""Fluxo comum de publicação: validações, registro e tratamento de falhas.

Cada canal (Telegram, WhatsApp) implementa só o que é dele: o que precisa
para enviar (`_preparar_envio`) e o envio em si (`_enviar`).
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.models.produto import Produto
from ofertas.models.publicacao import Publicacao
from ofertas.repositories.destino_divulgacao_repository import (
    DestinoDivulgacaoRepository,
)
from ofertas.repositories.publicacao_repository import PublicacaoRepository


class PublisherBase:
    CODIGO_CANAL: str = ""
    NOME_CANAL: str = ""

    def __init__(
        self,
        destino_repository: DestinoDivulgacaoRepository | None = None,
        publicacao_repository: PublicacaoRepository | None = None,
    ) -> None:
        self.destino_repository = (
            destino_repository or DestinoDivulgacaoRepository()
        )
        self.publicacao_repository = (
            publicacao_repository or PublicacaoRepository()
        )

    # --- pontos de extensão --------------------------------------------------

    def _preparar_envio(
        self,
        session: Session,
        destino: DestinoDivulgacao,
        canal: PlataformaDivulgacao,
    ) -> Any:
        """Valida e devolve o que o canal precisa para enviar (ex.: token)."""
        return None

    def _enviar(
        self,
        produto: Produto,
        destino: DestinoDivulgacao,
        nome_loja: str,
        contexto: Any,
    ) -> None:
        """Envia a mensagem. Deve levantar exceção se não houver confirmação."""
        raise NotImplementedError

    def _ao_falhar(self, session: Session, erro: Exception) -> None:
        """Reação do canal a uma falha de envio (ex.: pausar o canal)."""

    def _descrever_erro(self, erro: Exception) -> str:
        """Mensagem gravada na publicação. Nunca deve conter segredos."""
        return type(erro).__name__

    # --- fluxo comum -----------------------------------------------------------

    def _validar_produto(self, produto: Produto) -> None:
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

    def _registrar_tentativa(
        self,
        session: Session,
        produto: Produto,
        destino: DestinoDivulgacao,
        publicacao: Publicacao | None,
    ) -> Publicacao:
        if publicacao is None:
            if self.publicacao_repository.buscar_ativa(
                session,
                produto.id,
                destino.id,
            ) is not None:
                raise ValueError(
                    "Este produto já possui uma publicação pendente "
                    "neste destino."
                )

            return self.publicacao_repository.criar(
                session,
                produto_id=produto.id,
                destino_id=destino.id,
                preco_divulgado=produto.preco_atual,
                percentual_desconto_divulgado=produto.percentual_desconto,
                tentativas=1,
            )

        if publicacao.status_publicacao != "pendente":
            raise ValueError("A publicação informada não está pendente.")

        if (
            publicacao.produto_id != produto.id
            or publicacao.destino_divulgacao_id != destino.id
        ):
            raise ValueError(
                "A publicação pendente não corresponde "
                "ao produto e destino informados."
            )

        return publicacao

    def publicar(
        self,
        session: Session,
        produto: Produto,
        destino_id: int,
        publicacao: Publicacao | None = None,
    ) -> Publicacao:
        """Publica um produto sem confirmar a transação da sessão."""

        self._validar_produto(produto)

        destino = self.destino_repository.buscar_por_id(session, destino_id)

        if destino is None:
            raise LookupError("Destino de divulgação não encontrado.")

        if not destino.status_destino:
            raise ValueError("O destino de divulgação está inativo.")

        canal = session.get(
            PlataformaDivulgacao,
            destino.plataforma_divulgacao_id,
        )

        if canal is None:
            raise LookupError("Canal de divulgação não encontrado.")

        if not canal.status_plataforma:
            raise ValueError("O canal de divulgação está inativo.")

        if canal.codigo.lower() != self.CODIGO_CANAL:
            raise ValueError(
                f"O destino selecionado não é do {self.NOME_CANAL}."
            )

        contexto = self._preparar_envio(session, destino, canal)

        loja = session.get(Plataforma, produto.plataforma_id)

        if loja is None:
            raise LookupError(
                "Plataforma de origem do produto não encontrada."
            )

        publicacao = self._registrar_tentativa(
            session,
            produto,
            destino,
            publicacao,
        )

        try:
            self._enviar(produto, destino, loja.nome, contexto)

        except Exception as erro:
            publicacao.status_publicacao = "falhou"
            publicacao.erro = self._descrever_erro(erro)[:500]
            self._ao_falhar(session, erro)
            session.flush()
            return publicacao

        publicacao.status_publicacao = "publicada"
        publicacao.publicada_em = datetime.now(timezone.utc)
        publicacao.erro = None

        session.flush()
        return publicacao
