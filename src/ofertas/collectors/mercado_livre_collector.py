
import logging
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ofertas.collectors.mercado_livre_client import MercadoLivreClient
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.services.categoria_service import CategoriaService
from ofertas.services.produto_service import ProdutoService


logger = logging.getLogger(__name__)


class MercadoLivreCollector:
    """Executa a coleta e o monitoramento de produtos do Mercado Livre."""

    TAMANHO_PAGINA = 50
    LIMITE_MAXIMO_SELECAO = 1000

    def __init__(
        self,
        client: MercadoLivreClient | None = None,
        produto_service: ProdutoService | None = None,
        categoria_service: CategoriaService | None = None,
    ) -> None:
        self.client = client or MercadoLivreClient()
        self.produto_service = produto_service or ProdutoService()
        self.categoria_service = categoria_service or CategoriaService()

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

        categoria = self.categoria_service.preparar_selecao_coleta(
            session,
            categoria,
        )

        plataforma_id = categoria.plataforma_id

        anuncios, total_resultados = self._buscar_anuncios_categoria(
            session,
            plataforma_id,
            categoria.id_categoria_plataforma,
            categoria.limite_produtos_selecao,
        )

        processadas = 0
        ignoradas = 0
        ids_processados: set[str] = set()
        posicoes: dict[int, int] = {}
        erros: list[str] = []

        for posicao, anuncio_busca in enumerate(anuncios, start=1):
            item_id = "desconhecido"

            try:
                if not isinstance(anuncio_busca, dict):
                    ignoradas += 1

                    mensagem = (
                        f"Anúncio na posição {posicao}: "
                        "resposta com estrutura inválida."
                    )
                    erros.append(mensagem)

                    logger.warning(
                        "%s Categoria: %s.",
                        mensagem,
                        categoria.nome_categoria,
                    )
                    continue

                item_id = anuncio_busca.get("id")

                if not item_id:
                    ignoradas += 1

                    mensagem = (
                        f"Anúncio na posição {posicao}: ID não informado."
                    )
                    erros.append(mensagem)

                    logger.warning(
                        "%s Categoria: %s.",
                        mensagem,
                        categoria.nome_categoria,
                    )
                    continue

                item_id = str(item_id).strip()

                if not item_id:
                    ignoradas += 1
                    continue

                if item_id in ids_processados:
                    ignoradas += 1
                    continue

                ids_processados.add(item_id)

                detalhes = self.client.buscar_item(
                    session,
                    plataforma_id,
                    item_id,
                )

                if not isinstance(detalhes, dict):
                    raise RuntimeError(
                        f"Resposta inválida ao consultar o anúncio {item_id}."
                    )

                anuncio = {
                    **anuncio_busca,
                    **{
                        campo: valor
                        for campo, valor in detalhes.items()
                        if valor is not None
                    },
                }

                dados = self._preparar_produto(
                    categoria,
                    anuncio,
                )

                if dados is None:
                    ignoradas += 1

                    mensagem = (
                        f"Anúncio {item_id}: dados insuficientes "
                        "ou inválidos para cadastro."
                    )
                    erros.append(mensagem)

                    logger.warning(
                        "%s Categoria: %s.",
                        mensagem,
                        categoria.nome_categoria,
                    )
                    continue

                produto = self.produto_service.registrar_coleta(
                    session,
                    dados,
                )

                posicoes[produto.id] = posicao
                processadas += 1

            except httpx.HTTPStatusError as erro:
                codigo_http = erro.response.status_code

                if codigo_http == 404:
                    ignoradas += 1

                    mensagem = f"Anúncio {item_id}: HTTP 404."
                    erros.append(mensagem)

                    logger.warning(
                        "%s Categoria: %s.",
                        mensagem,
                        categoria.nome_categoria,
                    )
                    continue

                if codigo_http == 403:
                    logger.error(
                        "Acesso negado ao consultar anúncio %s "
                        "na categoria %s.",
                        item_id,
                        categoria.nome_categoria,
                    )
                    raise

                logger.exception(
                    "Falha HTTP ao consultar anúncio %s na categoria %s.",
                    item_id,
                    categoria.nome_categoria,
                )
                raise

            except SQLAlchemyError:
                logger.exception(
                    "Falha de banco ao processar anúncio %s na categoria %s.",
                    item_id,
                    categoria.nome_categoria,
                )
                raise

            except Exception:
                logger.exception(
                    "Erro inesperado ao processar anúncio %s na categoria %s.",
                    item_id,
                    categoria.nome_categoria,
                )
                raise

        if anuncios and processadas == 0:
            raise RuntimeError(
                f"Nenhum anúncio foi processado na categoria "
                f"{categoria.nome_categoria}. "
                "A seleção anterior será preservada."
            )

        self.produto_service.atualizar_posicoes_selecao_categoria(
            session,
            categoria.id,
            posicoes,
        )

        self.categoria_service.avancar_selecao_coleta(
            session,
            categoria,
            total_resultados,
        )

        return {
            "encontradas": len(anuncios),
            "processadas": processadas,
            "ignoradas": ignoradas,
            "erros": erros,
        }

    def _buscar_anuncios_categoria(
        self,
        session: Session,
        plataforma_id: int,
        categoria_id: str,
        limite: int,
    ) -> tuple[list[dict], int]:
        """Busca os primeiros anúncios da categoria usando paginação."""

        if not 1 <= limite <= self.LIMITE_MAXIMO_SELECAO:
            raise ValueError(
                "O limite de seleção deve estar entre 1 e 1000."
            )

        primeira_pagina = self.client.buscar_itens_categoria(
            session,
            plataforma_id,
            categoria_id,
            limite=min(self.TAMANHO_PAGINA, limite),
            offset=0,
        )

        if not isinstance(primeira_pagina, dict):
            raise ValueError(
                "Resposta inválida da busca de anúncios do Mercado Livre."
            )

        resultados = primeira_pagina.get("results")
        paginacao = primeira_pagina.get("paging")

        if not isinstance(resultados, list):
            raise ValueError(
                "A resposta do Mercado Livre não contém uma lista de anúncios."
            )

        if not isinstance(paginacao, dict):
            raise ValueError(
                "A resposta do Mercado Livre não contém os dados de paginação."
            )

        try:
            total_resultados = int(paginacao["total"])
        except (KeyError, TypeError, ValueError) as erro:
            raise ValueError(
                "Não foi possível identificar o total de anúncios da categoria."
            ) from erro

        if total_resultados < 0:
            raise ValueError(
                "O total de anúncios retornado pela API é inválido."
            )

        quantidade_desejada = min(limite, total_resultados)

        if quantidade_desejada > 0 and not resultados:
            raise RuntimeError(
                "A API informou anúncios disponíveis, "
                "mas retornou uma primeira página vazia."
            )

        anuncios = resultados[:quantidade_desejada]
        offset = len(resultados)

        while len(anuncios) < quantidade_desejada:
            restante = quantidade_desejada - len(anuncios)
            limite_pagina = min(self.TAMANHO_PAGINA, restante)

            pagina = self.client.buscar_itens_categoria(
                session,
                plataforma_id,
                categoria_id,
                limite=limite_pagina,
                offset=offset,
            )

            if not isinstance(pagina, dict):
                raise ValueError(
                    "Resposta inválida durante a paginação dos anúncios."
                )

            resultados_pagina = pagina.get("results")

            if not isinstance(resultados_pagina, list):
                raise ValueError(
                    "A resposta paginada não contém uma lista de anúncios."
                )

            if not resultados_pagina:
                raise RuntimeError(
                    "A paginação terminou antes de obter todos os "
                    "anúncios esperados."
                )

            anuncios.extend(resultados_pagina[:restante])
            offset += len(resultados_pagina)

        return anuncios, total_resultados

    def _preparar_produto(
        self,
        categoria: PlataformaCategoria,
        anuncio: dict,
    ) -> dict | None:
        """Converte os dados de um anúncio para o cadastro de produto."""

        item_id = anuncio.get("id")
        titulo = anuncio.get("title")

        if not item_id or not isinstance(titulo, str):
            return None

        item_id = str(item_id).strip()
        titulo = titulo.strip()

        if not item_id or not titulo:
            return None

        url = anuncio.get("permalink")

        if not isinstance(url, str) or not url.strip():
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

        disponivel = anuncio.get("status") == "active"

        if quantidade_disponivel is not None:
            try:
                quantidade_disponivel = int(quantidade_disponivel)
            except (TypeError, ValueError):
                return None

            disponivel = (
                disponivel
                and quantidade_disponivel > 0
            )

        imagens = anuncio.get("pictures")
        if not isinstance(imagens, list):
            imagens = []

        primeira_imagem = imagens[0] if imagens else {}

        imagem_url = (
            anuncio.get("secure_thumbnail")
            or anuncio.get("thumbnail")
        )

        if not imagem_url and isinstance(primeira_imagem, dict):
            imagem_url = (
                primeira_imagem.get("secure_url")
                or primeira_imagem.get("url")
            )

        catalog_product_id = anuncio.get("catalog_product_id")

        return {
            "plataforma_id": categoria.plataforma_id,
            "categoria_id": categoria.id,
            "id_produto_plataforma": (
                str(catalog_product_id)
                if catalog_product_id
                else None
            ),
            "id_item_plataforma": item_id,
            "titulo": titulo,
            "descricao": None,
            "url": url.strip(),
            "imagem_url": str(imagem_url) if imagem_url else None,
            "preco_atual": preco,
            "preco_original": preco_original,
            "percentual_desconto": desconto,
            "disponivel": disponivel,
        }
