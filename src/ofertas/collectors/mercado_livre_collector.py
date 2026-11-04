import logging
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ofertas.collectors.mercado_livre_client import MercadoLivreClient
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.services.produto_service import ProdutoService


logger = logging.getLogger(__name__)


class MercadoLivreCollector:
    """Executa a coleta e o monitoramento de produtos do Mercado Livre."""

    SITE_URL = "https://www.mercadolivre.com.br"

    def __init__(
        self,
        client: MercadoLivreClient | None = None,
        produto_service: ProdutoService | None = None,
    ) -> None:
        self.client = client or MercadoLivreClient()
        self.produto_service = produto_service or ProdutoService()

    def coletar_categoria(
        self,
        session: Session,
        categoria: PlataformaCategoria,
    ) -> dict:
        if not categoria.status_categoria:
            return {
                "encontradas": 0,
                "processadas": 0,
                "ignoradas": 0,
                "erros": [],
            }

        plataforma_id = categoria.plataforma_id

        destaques = self.client.buscar_destaques(
            session,
            plataforma_id,
            categoria.id_categoria_plataforma,
        )

        produtos = destaques.get("content", [])
        processadas = 0
        ignoradas = 0
        ids_processados = set()
        erros = []

        for produto in produtos:
            product_id = produto.get("id")

            if not product_id or product_id in ids_processados:
                ignoradas += 1
                continue

            ids_processados.add(product_id)

            try:
                detalhes = self.client.buscar_detalhes_produto(
                    session,
                    plataforma_id,
                    product_id,
                )

                anuncios = self.client.buscar_anuncios_produto(
                    session,
                    plataforma_id,
                    product_id,
                )

                resultados = anuncios.get("results", [])

                if not resultados:
                    ignoradas += 1
                    continue

                dados = self._preparar_produto(
                    categoria,
                    detalhes,
                    resultados[0],
                )

                if dados is None:
                    ignoradas += 1
                    continue

                self.produto_service.registrar_coleta(
                    session,
                    dados,
                )

                processadas += 1

            except httpx.HTTPStatusError as erro:
                codigo_http = erro.response.status_code

                if codigo_http in (403, 404):
                    ignoradas += 1

                    mensagem = (
                        f"Produto {product_id}: HTTP {codigo_http}"
                    )
                    erros.append(mensagem)

                    logger.warning(
                        "%s na categoria %s.",
                        mensagem,
                        categoria.nome_categoria,
                    )
                    continue

                logger.exception(
                    "Falha HTTP ao processar produto %s na categoria %s.",
                    product_id,
                    categoria.nome_categoria,
                )
                raise

            except SQLAlchemyError:
                logger.exception(
                    "Falha de banco ao processar produto %s na categoria %s.",
                    product_id,
                    categoria.nome_categoria,
                )
                raise

            except (
                KeyError,
                TypeError,
                ValueError,
                InvalidOperation,
                AttributeError,
            ) as erro:
                ignoradas += 1

                mensagem = (
                    f"Produto {product_id}: "
                    f"{type(erro).__name__}: {erro}"
                )
                erros.append(mensagem)

                logger.warning(
                    "Erro ao processar produto na categoria %s: %s",
                    categoria.nome_categoria,
                    mensagem,
                    exc_info=True,
                )

            except Exception:
                logger.exception(
                    "Erro inesperado ao processar produto %s na categoria %s.",
                    product_id,
                    categoria.nome_categoria,
                )
                raise

        return {
            "encontradas": len(produtos),
            "processadas": processadas,
            "ignoradas": ignoradas,
            "erros": erros,
        }

    def _preparar_produto(
        self,
        categoria: PlataformaCategoria,
        detalhes: dict,
        anuncio: dict,
    ) -> dict | None:
        product_id = detalhes.get("id")
        item_id = anuncio.get("item_id")
        titulo = detalhes.get("name") or detalhes.get("title")

        if not product_id or not item_id or not titulo:
            return None

        if detalhes.get("status") != "active":
            return None

        preco = Decimal(str(anuncio.get("price") or 0))

        if preco <= 0:
            return None

        preco_original = anuncio.get("original_price")
        desconto = None

        if preco_original is not None:
            preco_original = Decimal(str(preco_original))

            if preco_original > preco:
                desconto = (
                    (preco_original - preco) / preco_original
                ) * Decimal("100")

                desconto = desconto.quantize(Decimal("0.01"))
            else:
                preco_original = None

        quantidade_disponivel = anuncio.get("available_quantity")
        disponivel = (
            quantidade_disponivel > 0
            if quantidade_disponivel is not None
            else True
        )

        imagens = detalhes.get("pictures") or []
        primeira_imagem = imagens[0] if imagens else {}

        imagem_url = (
            primeira_imagem.get("url")
            if isinstance(primeira_imagem, dict)
            else None
        )

        url = (
            f"{self.SITE_URL}/p/{product_id}"
            f"?pdp_filters=item_id%3A{item_id}&wid={item_id}"
        )

        return {
            "plataforma_id": categoria.plataforma_id,
            "categoria_id": categoria.id,
            "id_produto_plataforma": str(product_id),
            "id_item_plataforma": str(item_id),
            "titulo": titulo.strip(),
            "descricao": None,
            "url": url,
            "imagem_url": imagem_url,
            "preco_atual": preco,
            "preco_original": preco_original,
            "percentual_desconto": desconto,
            "disponivel": disponivel,
        }