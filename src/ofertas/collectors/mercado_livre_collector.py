import logging
import threading
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ofertas.core.filtro_categoria import motivo_fora_da_categoria
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

    def _dominio_da_categoria(
        self,
        session: Session,
        categoria: PlataformaCategoria,
    ) -> str | None:
        try:
            return self.client.buscar_dominio_categoria(
                session,
                categoria.plataforma_id,
                categoria.id_categoria_plataforma,
            )
        except Exception as erro:
            logger.warning(
                "Domínio da categoria %s indisponível, busca sem ele: %s",
                categoria.id_categoria_plataforma,
                erro,
            )
            return None

    def coletar_categoria(
        self,
        session: Session,
        categoria: PlataformaCategoria,
        encerrando: threading.Event | None = None,
    ) -> dict:
        if not categoria.status_categoria:
            return {
                "encontradas": 0,
                "processadas": 0,
                "ignoradas": 0,
                "erros": [],
            }

        plataforma_id = categoria.plataforma_id

        if categoria.termo_busca:
            dominio = self._dominio_da_categoria(session, categoria)
            busca = self.client.buscar_produtos_catalogo(
                session,
                plataforma_id,
                categoria.termo_busca,
                dominio=dominio,
            )
            # Domínio da categoria diferente do produto (teclados: categoria
            # MLB1713 é COMPUTER_EQUIPMENT, o produto é PC_KEYBOARDS): busca sem.
            if dominio and not busca.get("results"):
                busca = self.client.buscar_produtos_catalogo(
                    session,
                    plataforma_id,
                    categoria.termo_busca,
                )
            produtos = [
                {"id": resultado["id"], "type": "PRODUCT"}
                for resultado in busca.get("results", [])
                if resultado.get("id")
            ]
        else:
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

        # Posição na lista da loja (mais vendidos ou relevância da busca):
        # usada para priorizar os mais populares na publicação.
        self.produto_service.limpar_posicoes_categoria(session, categoria.id)

        for posicao, destaque in enumerate(produtos, start=1):
            # Encerramento da API: mantém o que já foi salvo e para.
            if encerrando is not None and encerrando.is_set():
                erros.append(
                    f"Coleta da categoria {categoria.nome_categoria} "
                    "interrompida pelo encerramento da API."
                )
                break

            product_id = destaque.get("id")
            tipo = destaque.get("type") or "SEM_TIPO"

            if not product_id or product_id in ids_processados:
                ignoradas += 1
                continue

            ids_processados.add(product_id)

            if tipo == "USER_PRODUCT":
                ignoradas += 1
                mensagem = (
                    f"USER_PRODUCT {product_id}: coleta ainda não "
                    "implementada para o modelo User Products. "
                    "Este identificador requer um fluxo específico, "
                    "diferente das consultas de ITEM e PRODUCT."
                )
                erros.append(mensagem)
                logger.warning(
                    "%s Categoria: %s.",
                    mensagem,
                    categoria.nome_categoria,
                )
                continue

            if tipo not in {"PRODUCT", "ITEM"}:
                ignoradas += 1
                mensagem = (
                    f"Destaque {product_id}: tipo não suportado ({tipo})."
                )
                erros.append(mensagem)
                logger.warning(
                    "%s Categoria: %s.",
                    mensagem,
                    categoria.nome_categoria,
                )
                continue

            try:
                if tipo == "PRODUCT":
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

                else:
                    anuncio = self.client.buscar_item(
                        session,
                        plataforma_id,
                        product_id,
                    )
                    dados = self._preparar_item(categoria, anuncio)

                if dados is None:
                    ignoradas += 1
                    continue

                if motivo_fora_da_categoria(dados["titulo"], categoria.termo_busca):
                    ignoradas += 1
                    continue

                dados["posicao_selecao_categoria"] = posicao

                self.produto_service.registrar_coleta(
                    session,
                    dados,
                )
                processadas += 1

            except httpx.HTTPStatusError as erro:
                codigo_http = erro.response.status_code

                if codigo_http in (403, 404):
                    ignoradas += 1

                    # Na busca por termo é comum o produto de catálogo não
                    # ter anúncio ativo: descarta sem poluir os avisos.
                    if categoria.termo_busca and codigo_http == 404:
                        continue

                    if codigo_http == 403:
                        motivo = (
                            "Acesso negado pela API. Verificar permissões, "
                            "escopos e autorização do usuário para o recurso."
                        )
                    else:
                        motivo = "Recurso não encontrado na API."

                    mensagem = (
                        f"{tipo} {product_id}: HTTP {codigo_http} - "
                        f"{motivo} Resposta: {erro.response.text[:300]}"
                    )
                    erros.append(mensagem)

                    logger.warning(
                        "%s Categoria: %s.",
                        mensagem,
                        categoria.nome_categoria,
                    )
                    continue

                logger.exception(
                    "Falha HTTP ao processar destaque %s (%s) "
                    "na categoria %s.",
                    product_id,
                    tipo,
                    categoria.nome_categoria,
                )
                raise

            except SQLAlchemyError:
                logger.exception(
                    "Falha de banco ao processar destaque %s "
                    "na categoria %s.",
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
                    f"{tipo} {product_id}: "
                    f"{type(erro).__name__}: {erro}"
                )
                erros.append(mensagem)

                logger.warning(
                    "Erro ao processar destaque na categoria %s: %s",
                    categoria.nome_categoria,
                    mensagem,
                    exc_info=True,
                )

            except Exception:
                logger.exception(
                    "Erro inesperado ao processar destaque %s "
                    "na categoria %s.",
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

    def _preparar_item(
        self,
        categoria: PlataformaCategoria,
        anuncio: dict,
    ) -> dict | None:
        """Converte um anúncio ITEM para o formato interno de produto."""

        if not isinstance(anuncio, dict):
            return None

        detalhes = {
            "id": anuncio.get("catalog_product_id"),
            "name": anuncio.get("title"),
            "status": anuncio.get("status"),
            "pictures": anuncio.get("pictures") or [],
        }

        dados_anuncio = {
            "item_id": anuncio.get("id"),
            "price": anuncio.get("price"),
            "original_price": anuncio.get("original_price"),
            "available_quantity": anuncio.get("available_quantity"),
        }

        return self._preparar_produto(
            categoria,
            detalhes,
            dados_anuncio,
            url_anuncio=anuncio.get("permalink"),
        )

    def _preparar_produto(
        self,
        categoria: PlataformaCategoria,
        detalhes: dict,
        anuncio: dict,
        *,
        url_anuncio: str | None = None,
    ) -> dict | None:
        """Converte dados de catálogo ou anúncio para o formato interno."""

        if not isinstance(detalhes, dict) or not isinstance(anuncio, dict):
            return None

        product_id = detalhes.get("id")
        item_id = anuncio.get("item_id")
        titulo = detalhes.get("name") or detalhes.get("title")

        if not item_id or not isinstance(titulo, str) or not titulo.strip():
            return None

        if detalhes.get("status") != "active":
            return None

        try:
            preco = Decimal(str(anuncio.get("price") or 0))
        except (InvalidOperation, TypeError, ValueError):
            return None

        if not preco.is_finite() or preco <= 0:
            return None

        preco_original = anuncio.get("original_price")
        desconto = None

        if preco_original is not None:
            try:
                preco_original = Decimal(str(preco_original))
            except (InvalidOperation, TypeError, ValueError):
                return None

            if not preco_original.is_finite():
                return None

            if preco_original > preco:
                desconto = (
                    (preco_original - preco) / preco_original
                ) * Decimal("100")
                desconto = desconto.quantize(Decimal("0.01"))
            else:
                preco_original = None

        quantidade_disponivel = anuncio.get("available_quantity")

        if quantidade_disponivel is None:
            disponivel = True
        else:
            try:
                quantidade_disponivel = int(quantidade_disponivel)
            except (TypeError, ValueError):
                return None

            disponivel = quantidade_disponivel > 0

        imagens = detalhes.get("pictures") or []
        if not isinstance(imagens, list):
            imagens = []

        primeira_imagem = imagens[0] if imagens else {}
        imagem_url = None

        if isinstance(primeira_imagem, dict):
            imagem_url = (
                primeira_imagem.get("secure_url")
                or primeira_imagem.get("url")
            )

        url = url_anuncio.strip() if isinstance(url_anuncio, str) else ""

        if not url and product_id:
            url = (
                f"{self.SITE_URL}/p/{product_id}"
                f"?pdp_filters=item_id%3A{item_id}&wid={item_id}"
            )

        if not url or not url.startswith(("https://", "http://")):
            return None

        return {
            "plataforma_id": categoria.plataforma_id,
            "categoria_id": categoria.id,
            "id_produto_plataforma": (
                str(product_id) if product_id else None
            ),
            "id_item_plataforma": str(item_id),
            "titulo": titulo.strip(),
            "descricao": None,
            "url": url,
            "imagem_url": str(imagem_url) if imagem_url else None,
            "preco_atual": preco,
            "preco_original": preco_original,
            "percentual_desconto": desconto,
            "disponivel": disponivel,
        }
