import logging
import threading
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ofertas.collectors.shopee_client import (
    ShopeeClient,
)
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.produto import Produto
from ofertas.repositories.produto_repository import ProdutoRepository


logger = logging.getLogger(__name__)


class ShopeeAffiliateService:
    """Coordena a geração e o registro de links afiliados da Shopee."""

    CODIGO_PLATAFORMA = "shopee"

    def __init__(
        self,
        repository: ProdutoRepository | None = None,
        client: ShopeeClient | None = None,
    ) -> None:
        self.repository = repository or ProdutoRepository()
        self.client = client or ShopeeClient()

    def gerar_pendentes(
        self,
        session: Session,
        plataforma_id: int,
        produto_ids: Sequence[int] | None = None,
        encerrando: threading.Event | None = None,
    ) -> dict[str, Any]:
        """Gera links afiliados para produtos pendentes da Shopee."""

        plataforma = session.get(Plataforma, plataforma_id)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de ID '{plataforma_id}' não encontrada."
            )

        if plataforma.codigo != self.CODIGO_PLATAFORMA:
            raise ValueError(
                "Este serviço aceita somente a plataforma Shopee."
            )

        produtos = self.repository.listar_pendentes_para_geracao_afiliado(
            session,
            plataforma_id,
            produto_ids,
        )

        resultado: dict[str, Any] = {
            "total_encontrados": len(produtos),
            "total_gerados": 0,
            "total_erros": 0,
            "total_tentativas": 0,
            "erros": [],
        }

        for produto, categoria in produtos:
            # Encerramento da API: os restantes ficam pendentes para a
            # próxima geração.
            if encerrando is not None and encerrando.is_set():
                break

            if categoria is None:
                mensagem = "Produto sem categoria associada."
                self._registrar_erro(produto, None, mensagem)
                self._adicionar_erro(resultado, produto, mensagem)
                continue

            etiqueta = (
                categoria.etiqueta_afiliado.strip()
                if categoria.etiqueta_afiliado
                else ""
            )

            if not etiqueta:
                mensagem = (
                    f"A categoria '{categoria.nome_categoria}' "
                    "não possui etiqueta de afiliado."
                )

                self._registrar_erro(
                    produto,
                    categoria,
                    mensagem,
                )
                self._adicionar_erro(resultado, produto, mensagem)
                continue

            url = produto.url.strip() if produto.url else ""

            if not self._url_valida(url):
                mensagem = "Produto possui uma URL original inválida."

                self._registrar_erro(
                    produto,
                    categoria,
                    mensagem,
                )
                self._adicionar_erro(resultado, produto, mensagem)
                continue

            resultado["total_tentativas"] += 1

            try:
                link = self.client.gerar_link_afiliado(
                    session,
                    url,
                    etiqueta,
                )

                if not self._url_valida(link):
                    raise ValueError(
                        "A Shopee retornou um link afiliado inválido."
                    )

            except SQLAlchemyError:
                raise

            except Exception as erro:
                mensagem = f"{type(erro).__name__}: {erro}"

                logger.exception(
                    "Falha ao gerar link afiliado Shopee. "
                    "Produto: %s | Categoria: %s",
                    produto.id,
                    categoria.nome_categoria,
                )

                self._registrar_erro(
                    produto,
                    categoria,
                    mensagem,
                    etiqueta=etiqueta,
                    tentativa_api=True,
                )

                self._adicionar_erro(
                    resultado,
                    produto,
                    mensagem,
                )

                session.flush()
                continue

            self._registrar_sucesso(
                produto,
                categoria,
                link,
                etiqueta,
            )

            resultado["total_gerados"] += 1

            session.flush()

        session.flush()
        return resultado

    def _registrar_sucesso(
        self,
        produto: Produto,
        categoria: PlataformaCategoria,
        link: str,
        etiqueta: str,
    ) -> None:
        produto.url_afiliada = link
        produto.status_link_afiliado = "gerado"
        produto.metodo_geracao_link_afiliado = "api"
        produto.identificador_rastreamento = etiqueta
        produto.erro_geracao_link_afiliado = None
        produto.link_afiliado_gerado_em = datetime.now(timezone.utc)

        self._atualizar_elegibilidade(produto, categoria)

    def _registrar_erro(
        self,
        produto: Produto,
        categoria: PlataformaCategoria | None,
        mensagem: str,
        etiqueta: str | None = None,
        tentativa_api: bool = False,
    ) -> None:
        produto.status_link_afiliado = "erro"
        produto.metodo_geracao_link_afiliado = (
            "api" if tentativa_api else None
        )
        produto.identificador_rastreamento = (
            etiqueta if tentativa_api else None
        )
        produto.erro_geracao_link_afiliado = mensagem[:4000]
        produto.link_afiliado_gerado_em = None

        self._atualizar_elegibilidade(produto, categoria)

    @staticmethod
    def _adicionar_erro(
        resultado: dict[str, Any],
        produto: Produto,
        mensagem: str,
    ) -> None:
        resultado["total_erros"] += 1
        resultado["erros"].append(
            {
                "produto_id": produto.id,
                "mensagem": mensagem,
            }
        )

    @staticmethod
    def _url_valida(url: str) -> bool:
        if not url:
            return False

        try:
            parsed = urlsplit(url)
        except ValueError:
            return False

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    @staticmethod
    def _atualizar_elegibilidade(
        produto: Produto,
        categoria: PlataformaCategoria | None,
    ) -> None:
        desconto_minimo = (
            categoria.desconto_minimo_percentual
            if categoria is not None
            else None
        )

        desconto_atingido = (
            desconto_minimo is not None
            and produto.percentual_desconto is not None
            and produto.percentual_desconto >= desconto_minimo
        )

        produto.elegivel_divulgacao = bool(
            produto.status_monitoramento == "ativo"
            and produto.disponivel
            and desconto_atingido
            and produto.status_link_afiliado == "gerado"
            and produto.url_afiliada
        )