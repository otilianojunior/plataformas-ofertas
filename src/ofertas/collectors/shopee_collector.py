import logging
import threading
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ofertas.collectors.shopee_client import (
    ShopeeAPIError,
    ShopeeClient,
)
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.services.produto_service import ProdutoService


logger = logging.getLogger(__name__)


class ShopeeCollector:
    """Executa a coleta e normalização de ofertas da Shopee."""

    DEFAULT_SORT_TYPES = (2, 5, 1)
    DEFAULT_MAX_PAGES = 10
    DEFAULT_PAGE_SIZE = 10

    def __init__(
        self,
        client: ShopeeClient | None = None,
        produto_service: ProdutoService | None = None,
        *,
        sort_types: tuple[int, ...] = DEFAULT_SORT_TYPES,
        max_pages: int = DEFAULT_MAX_PAGES,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> None:
        self.client = client or ShopeeClient()
        self.produto_service = produto_service or ProdutoService()

        if not sort_types:
            raise ValueError(
                "É necessário informar pelo menos um tipo de ordenação."
            )

        if any(
            isinstance(tipo, bool)
            or not isinstance(tipo, int)
            or tipo not in {1, 2, 3, 4, 5}
            for tipo in sort_types
        ):
            raise ValueError(
                "Todos os tipos de ordenação devem estar entre 1 e 5."
            )

        if (
            isinstance(max_pages, bool)
            or not isinstance(max_pages, int)
            or max_pages < 1
        ):
            raise ValueError(
                "O limite de páginas deve ser um inteiro positivo."
            )

        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or page_size < 1
        ):
            raise ValueError(
                "O tamanho da página deve ser um inteiro positivo."
            )

        self.sort_types = tuple(dict.fromkeys(sort_types))
        self.max_pages = max_pages
        self.page_size = page_size

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

        try:
            categoria_id = int(
                categoria.id_categoria_plataforma.strip()
            )
        except (AttributeError, TypeError, ValueError) as erro:
            raise ValueError(
                f"ID da categoria Shopee inválido: "
                f"{categoria.id_categoria_plataforma!r}."
            ) from erro

        if categoria_id <= 0:
            raise ValueError(
                "O ID da categoria Shopee deve ser positivo."
            )

        encontradas = 0
        ignoradas = 0
        erros = []
        ofertas_por_id = {}
        consultas_com_sucesso = 0

        interrompida = False

        for sort_type in self.sort_types:
            if interrompida:
                break

            pagina = 1

            while pagina <= self.max_pages:
                # Encerramento da API: processa o que já veio e para.
                if encerrando is not None and encerrando.is_set():
                    interrompida = True
                    erros.append(
                        f"Coleta da categoria {categoria.nome_categoria} "
                        "interrompida pelo encerramento da API."
                    )
                    break

                try:
                    resultado = self.client.buscar_ofertas_categoria(
                        session,
                        categoria_id,
                        sort_type,
                        page=pagina,
                        limit=self.page_size,
                        termo_busca=categoria.termo_busca,
                    )

                except ShopeeAPIError as erro:
                    mensagem = (
                        f"Falha na consulta da categoria "
                        f"{categoria.nome_categoria}, "
                        f"sortType={sort_type}, página={pagina}: {erro}"
                    )
                    erros.append(mensagem)

                    logger.warning("%s", mensagem)
                    break

                consultas_com_sucesso += 1

                nodes = resultado["nodes"]
                page_info = resultado["pageInfo"]

                encontradas += len(nodes)

                for oferta in nodes:
                    item_id = oferta.get("itemId")

                    if (
                        item_id is None
                        or isinstance(item_id, bool)
                        or not str(item_id).strip()
                    ):
                        ignoradas += 1
                        erros.append(
                            "Oferta Shopee ignorada: itemId ausente "
                            "ou inválido."
                        )
                        continue

                    item_id = str(item_id).strip()
                    oferta_existente = ofertas_por_id.get(item_id)

                    if oferta_existente is None:
                        ofertas_por_id[item_id] = oferta
                        continue

                    # O mesmo item pode aparecer em diferentes páginas
                    # ou ordenações. Mantemos a ocorrência com mais vendas.
                    ignoradas += 1

                    if self._obter_vendas(oferta) > self._obter_vendas(
                        oferta_existente
                    ):
                        ofertas_por_id[item_id] = oferta

                if not page_info["hasNextPage"]:
                    break

                if pagina == self.max_pages:
                    mensagem = (
                        f"Limite de {self.max_pages} páginas atingido "
                        f"na categoria {categoria.nome_categoria}, "
                        f"sortType={sort_type}."
                    )
                    erros.append(mensagem)
                    logger.warning("%s", mensagem)
                    break

                pagina += 1

        if consultas_com_sucesso == 0 and not interrompida:
            detalhes = "; ".join(erros) or (
                "Nenhuma consulta foi concluída."
            )
            raise ShopeeAPIError(
                f"Não foi possível consultar a categoria "
                f"{categoria.nome_categoria}: {detalhes}"
            )

        # Processa primeiro as ofertas com maior volume de vendas.
        ofertas_ordenadas = sorted(
            ofertas_por_id.values(),
            key=self._obter_vendas,
            reverse=True,
        )

        processadas = 0

        for oferta in ofertas_ordenadas:
            try:
                dados = self._preparar_produto(
                    categoria,
                    oferta,
                )

                if dados is None:
                    ignoradas += 1
                    continue

                self.produto_service.registrar_coleta(
                    session,
                    dados,
                )

                processadas += 1

            except SQLAlchemyError:
                logger.exception(
                    "Falha de banco ao processar oferta Shopee %s "
                    "na categoria %s.",
                    oferta.get("itemId"),
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
                    f"Oferta {oferta.get('itemId')}: "
                    f"{type(erro).__name__}: {erro}"
                )
                erros.append(mensagem)

                logger.warning(
                    "Erro ao processar oferta na categoria %s: %s",
                    categoria.nome_categoria,
                    mensagem,
                    exc_info=True,
                )

            except Exception:
                logger.exception(
                    "Erro inesperado ao processar oferta Shopee %s "
                    "na categoria %s.",
                    oferta.get("itemId"),
                    categoria.nome_categoria,
                )
                raise

        return {
            "encontradas": encontradas,
            "processadas": processadas,
            "ignoradas": ignoradas,
            "erros": erros,
        }

    @staticmethod
    def _obter_vendas(oferta: dict) -> Decimal:
        """Converte o volume de vendas para ordenação numérica."""

        try:
            vendas = Decimal(str(oferta.get("sales") or 0))

            if not vendas.is_finite() or vendas < 0:
                return Decimal("0")

            return vendas

        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0")


    def _preparar_produto(
        self,
        categoria: PlataformaCategoria,
        oferta: dict,
    ) -> dict | None:
        """Converte uma oferta Shopee para o formato interno de produto."""

        if not isinstance(oferta, dict):
            return None

        item_id = oferta.get("itemId")
        titulo = oferta.get("productName")

        if (
            item_id is None
            or isinstance(item_id, bool)
            or not str(item_id).strip()
        ):
            return None

        if not isinstance(titulo, str) or not titulo.strip():
            return None

        preco_bruto = oferta.get("price") or oferta.get("priceMin")

        try:
            preco = Decimal(str(preco_bruto))
        except (InvalidOperation, TypeError, ValueError):
            return None

        if not preco.is_finite() or preco <= 0:
            return None

        desconto = None
        preco_original = None
        desconto_bruto = oferta.get("priceDiscountRate")

        if desconto_bruto is not None:
            try:
                desconto_informado = Decimal(str(desconto_bruto))

                if (
                    desconto_informado.is_finite()
                    and Decimal("0") <= desconto_informado <= Decimal("100")
                ):
                    desconto = desconto_informado.quantize(
                        Decimal("0.01")
                    )

                    if Decimal("0") < desconto < Decimal("100"):
                        fator = (
                            Decimal("1")
                            - desconto / Decimal("100")
                        )

                        preco_original = (
                            preco / fator
                        ).quantize(Decimal("0.01"))

                        if preco_original <= preco:
                            preco_original = None

            except (InvalidOperation, TypeError, ValueError):
                desconto = None
                preco_original = None

        url = oferta.get("productLink") or oferta.get("offerLink")

        if not isinstance(url, str):
            return None

        url = url.strip()

        if not url.startswith(("https://", "http://")):
            return None

        imagem_url = oferta.get("imageUrl")

        if not isinstance(imagem_url, str) or not imagem_url.strip():
            imagem_url = None
        else:
            imagem_url = imagem_url.strip()

        return {
            "plataforma_id": categoria.plataforma_id,
            "categoria_id": categoria.id,
            "id_produto_plataforma": None,
            "id_item_plataforma": str(item_id).strip(),
            "titulo": titulo.strip(),
            "descricao": None,
            "url": url,
            "imagem_url": imagem_url,
            "preco_atual": preco,
            "preco_original": preco_original,
            "percentual_desconto": desconto,
            "disponivel": True,
        }
