
import hashlib
import json
import time

import httpx
from sqlalchemy.orm import Session

from ofertas.services.credencial_plataforma_service import (
    CredencialPlataformaService,
)


class ShopeeAPIError(RuntimeError):
    """Erro de comunicação ou resposta da API de afiliados da Shopee."""


class ShopeeClient:
    """Cliente GraphQL autenticado da API de afiliados da Shopee."""

    API_URL = "https://open-api.affiliate.shopee.com.br/graphql"
    TIMEOUT = 20.0

    PRODUCT_OFFER_QUERY = """
        query ProductOfferList(
            $keyword: String,
            $listType: Int,
            $sortType: Int,
            $page: Int,
            $limit: Int,
            $productCatId: Int
        ) {
            productOfferV2(
                keyword: $keyword,
                listType: $listType,
                sortType: $sortType,
                page: $page,
                limit: $limit,
                productCatId: $productCatId
            ) {
                nodes {
                    itemId
                    productName
                    price
                    priceMin
                    priceMax
                    priceDiscountRate
                    productLink
                    offerLink
                    imageUrl
                    shopId
                    shopName
                    sales
                    ratingStar
                    commissionRate
                    periodEndTime
                }
                pageInfo {
                    page
                    limit
                    hasNextPage
                }
            }
        }
    """

    GENERATE_SHORT_LINK_MUTATION = """
        mutation GenerateShortLink(
            $originUrl: String!,
            $subIds: [String!]
        ) {
            generateShortLink(
                input: {
                    originUrl: $originUrl,
                    subIds: $subIds
                }
            ) {
                shortLink
            }
        }
    """

    def __init__(
        self,
        credencial_service: CredencialPlataformaService | None = None,
        *,
        timeout: float = TIMEOUT,
        timestamp_provider=None,
    ) -> None:
        self.credencial_service = (
            credencial_service or CredencialPlataformaService()
        )
        self.timeout = timeout
        self.timestamp_provider = timestamp_provider or time.time

    def _obter_credenciais(
        self,
        session: Session,
    ) -> tuple[str, str]:
        app_id = self.credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo="shopee",
            tipo_credencial="app_id",
        )

        app_secret = self.credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo="shopee",
            tipo_credencial="app_secret",
        )

        return app_id, app_secret

    @staticmethod
    def _gerar_assinatura(
        app_id: str,
        timestamp: int,
        payload: str,
        app_secret: str,
    ) -> str:
        origem = f"{app_id}{timestamp}{payload}{app_secret}"

        return hashlib.sha256(
            origem.encode("utf-8")
        ).hexdigest()

    def _executar_query(
        self,
        session: Session,
        query: str,
        variables: dict | None = None,
        operation_name: str | None = None,
    ) -> dict:
        app_id, app_secret = self._obter_credenciais(session)
        timestamp = int(self.timestamp_provider())

        corpo = {
            "query": query,
        }

        if variables is not None:
            corpo["variables"] = variables

        if operation_name is not None:
            corpo["operationName"] = operation_name

        payload = json.dumps(
            corpo,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        assinatura = self._gerar_assinatura(
            app_id,
            timestamp,
            payload,
            app_secret,
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                f"SHA256 Credential={app_id}, "
                f"Timestamp={timestamp}, "
                f"Signature={assinatura}"
            ),
        }

        try:
            with httpx.Client(timeout=self.timeout) as cliente:
                resposta = cliente.post(
                    self.API_URL,
                    content=payload,
                    headers=headers,
                )

            resposta.raise_for_status()

        except httpx.HTTPStatusError as erro:
            raise ShopeeAPIError(
                f"A Shopee retornou HTTP "
                f"{erro.response.status_code}: "
                f"{erro.response.text[:500]}"
            ) from erro

        except httpx.TransportError as erro:
            raise ShopeeAPIError(
                f"Falha de comunicação com a Shopee: {erro}"
            ) from erro

        try:
            resultado = resposta.json()

        except ValueError as erro:
            raise ShopeeAPIError(
                "A Shopee retornou uma resposta que não é JSON válido."
            ) from erro

        if not isinstance(resultado, dict):
            raise ShopeeAPIError(
                "A Shopee retornou uma estrutura de resposta inválida."
            )

        erros = resultado.get("errors")

        if erros:
            mensagens = [
                item.get("message", str(item))
                if isinstance(item, dict)
                else str(item)
                for item in erros
            ]

            raise ShopeeAPIError(
                "Erro GraphQL da Shopee: " + "; ".join(mensagens)
            )

        return resultado

    @staticmethod
    def _validar_paginacao(
        resultado: dict,
    ) -> dict:
        """Valida e extrai os dados de ofertas e paginação."""

        dados = resultado.get("data")

        if not isinstance(dados, dict):
            raise ShopeeAPIError(
                "A resposta da Shopee não contém o objeto data esperado."
            )

        ofertas = dados.get("productOfferV2")

        if not isinstance(ofertas, dict):
            raise ShopeeAPIError(
                "A resposta da Shopee não contém productOfferV2."
            )

        nodes = ofertas.get("nodes")
        page_info = ofertas.get("pageInfo")

        if not isinstance(nodes, list):
            raise ShopeeAPIError(
                "A lista de ofertas retornada pela Shopee é inválida."
            )

        if not isinstance(page_info, dict):
            raise ShopeeAPIError(
                "As informações de paginação da Shopee são inválidas."
            )

        if not isinstance(page_info.get("hasNextPage"), bool):
            raise ShopeeAPIError(
                "O indicador hasNextPage retornado pela Shopee é inválido."
            )

        if not all(isinstance(item, dict) for item in nodes):
            raise ShopeeAPIError(
                "A Shopee retornou uma oferta em formato inválido."
            )

        return ofertas

    @staticmethod
    def _validar_parametros_paginacao(
        sort_type: int,
        page: int,
        limit: int,
    ) -> None:
        if (
            isinstance(sort_type, bool)
            or not isinstance(sort_type, int)
            or sort_type not in {1, 2, 3, 4, 5}
        ):
            raise ValueError(
                "O tipo de ordenação deve estar entre 1 e 5."
            )

        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError(
                "A página deve ser um inteiro positivo."
            )

        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 1
        ):
            raise ValueError(
                "O limite deve ser um inteiro positivo."
            )

    def _buscar_ofertas(
        self,
        session: Session,
        *,
        keyword: str | None,
        categoria_id: int | None,
        sort_type: int,
        page: int,
        limit: int,
    ) -> dict:
        """Executa a consulta compartilhada de ofertas da Shopee."""

        self._validar_parametros_paginacao(
            sort_type,
            page,
            limit,
        )

        if categoria_id is not None and (
            isinstance(categoria_id, bool)
            or not isinstance(categoria_id, int)
            or categoria_id <= 0
        ):
            raise ValueError(
                "O ID da categoria deve ser um inteiro positivo."
            )

        if keyword is not None:
            if not isinstance(keyword, str) or not keyword.strip():
                raise ValueError(
                    "A palavra-chave não pode ficar vazia."
                )

            keyword = keyword.strip()

        variables = {
            "keyword": keyword,
            "listType": 0,
            "sortType": sort_type,
            "page": page,
            "limit": limit,
            "productCatId": categoria_id,
        }

        resultado = self._executar_query(
            session,
            self.PRODUCT_OFFER_QUERY,
            variables,
            "ProductOfferList",
        )

        return self._validar_paginacao(resultado)

    def buscar_ofertas_categoria(
        self,
        session: Session,
        categoria_id: int,
        sort_type: int,
        *,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Busca uma página de ofertas de uma categoria da Shopee."""

        return self._buscar_ofertas(
            session,
            keyword=None,
            categoria_id=categoria_id,
            sort_type=sort_type,
            page=page,
            limit=limit,
        )

    def buscar_ofertas_por_palavra_chave(
        self,
        session: Session,
        keyword: str,
        sort_type: int = 2,
        *,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Busca ofertas usando o nome da categoria como palavra-chave."""

        return self._buscar_ofertas(
            session,
            keyword=keyword,
            categoria_id=None,
            sort_type=sort_type,
            page=page,
            limit=limit,
        )

    def gerar_link_afiliado(
        self,
        session: Session,
        url_produto: str,
        etiqueta_afiliado: str,
    ) -> str:
        """Gera link afiliado Shopee com identificação da categoria."""

        if not isinstance(url_produto, str):
            raise ValueError(
                "A URL do produto deve ser uma string."
            )

        url_produto = url_produto.strip()

        if not url_produto.startswith(("https://", "http://")):
            raise ValueError(
                "A URL original do produto é inválida."
            )

        if (
            not isinstance(etiqueta_afiliado, str)
            or not etiqueta_afiliado.strip()
        ):
            raise ValueError(
                "A etiqueta afiliada não foi informada."
            )

        resultado = self._executar_query(
            session,
            self.GENERATE_SHORT_LINK_MUTATION,
            {
                "originUrl": url_produto,
                "subIds": [etiqueta_afiliado.strip()],
            },
            "GenerateShortLink",
        )

        dados = resultado.get("data")

        if not isinstance(dados, dict):
            raise ShopeeAPIError(
                "A resposta da Shopee não contém o objeto data esperado."
            )

        link_gerado = dados.get("generateShortLink")

        if not isinstance(link_gerado, dict):
            raise ShopeeAPIError(
                "A Shopee não retornou os dados do link afiliado."
            )

        short_link = link_gerado.get("shortLink")

        if (
            not isinstance(short_link, str)
            or not short_link.strip().startswith(("https://", "http://"))
        ):
            raise ShopeeAPIError(
                "A Shopee retornou um link afiliado inválido."
            )

        return short_link.strip()
