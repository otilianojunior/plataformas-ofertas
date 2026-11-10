
import json
import logging
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

from ofertas.affiliates.mercado_livre_browser import (
    MercadoLivreBrowser,
    MercadoLivreBrowserError,
)
from ofertas.core.config import Settings


logger = logging.getLogger(__name__)


class MercadoLivreAffiliateError(RuntimeError):
    """Erro na comunicação com o gerador de links afiliados."""


class MercadoLivreAffiliateClient:
    """Gera links afiliados usando a sessão autenticada do Chrome."""

    HOME_URL = "https://www.mercadolivre.com.br/"

    ENDPOINT = (
        "https://www.mercadolivre.com.br/"
        "affiliate-program/api/v2/affiliates/createLink"
    )

    TIMEOUT_NAVEGACAO = 30_000

    def __init__(
        self,
        settings: Settings | None = None,
        browser: MercadoLivreBrowser | None = None,
    ) -> None:
        self.browser = browser or MercadoLivreBrowser(
            settings=settings,
        )

    def create_links(
        self,
        urls: Sequence[str],
        tag: str,
    ) -> Any:
        """
        Gera links afiliados para uma lista de URLs.

        A resposta original do gerador é retornada para que
        o serviço possa interpretar cada resultado.
        """

        if isinstance(urls, (str, bytes)):
            raise ValueError(
                "Informe uma lista de URLs, não uma URL isolada."
            )

        urls_validas = [
            url.strip()
            for url in urls
            if isinstance(url, str) and url.strip()
        ]

        if not urls_validas:
            raise ValueError(
                "É necessário informar pelo menos uma URL."
            )

        if len(urls_validas) != len(urls):
            raise ValueError(
                "A lista contém URLs vazias ou inválidas."
            )

        if not isinstance(tag, str) or not tag.strip():
            raise ValueError(
                "A etiqueta do programa de afiliados é obrigatória."
            )

        for url in urls_validas:
            parsed = urlsplit(url)

            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
            ):
                raise ValueError(
                    f"URL de produto inválida: {url}"
                )

        try:
            with self.browser.connect() as context:
                page = context.new_page()

                try:
                    page.goto(
                        self.HOME_URL,
                        wait_until="domcontentloaded",
                        timeout=self.TIMEOUT_NAVEGACAO,
                    )

                    resultado = page.evaluate(
                        """
                        async ({ endpoint, urls, tag }) => {
                            const response = await fetch(endpoint, {
                                method: "POST",
                                headers: {
                                    "accept": "application/json, text/plain, */*",
                                    "content-type": "application/json"
                                },
                                body: JSON.stringify({
                                    urls: urls,
                                    tag: tag
                                }),
                                credentials: "include"
                            });

                            return {
                                status: response.status,
                                contentType: response.headers.get(
                                    "content-type"
                                ),
                                body: await response.text()
                            };
                        }
                        """,
                        {
                            "endpoint": self.ENDPOINT,
                            "urls": urls_validas,
                            "tag": tag.strip(),
                        },
                    )

                finally:
                    if not page.is_closed():
                        page.close()

        except MercadoLivreBrowserError as erro:
            raise MercadoLivreAffiliateError(
                f"Falha ao acessar a sessão do Mercado Livre: {erro}"
            ) from erro

        except Exception as erro:
            raise MercadoLivreAffiliateError(
                f"Falha na comunicação com o Chrome ou "
                f"Mercado Livre: {erro}"
            ) from erro

        if not isinstance(resultado, dict):
            raise MercadoLivreAffiliateError(
                "O navegador retornou uma resposta inválida."
            )

        status_http = resultado.get("status")
        corpo = resultado.get("body")

        if not isinstance(status_http, int):
            raise MercadoLivreAffiliateError(
                "Não foi possível identificar o status HTTP da resposta."
            )

        if not isinstance(corpo, str):
            raise MercadoLivreAffiliateError(
                "O Mercado Livre retornou uma resposta sem conteúdo válido."
            )

        if not 200 <= status_http < 300:
            raise MercadoLivreAffiliateError(
                f"Mercado Livre retornou HTTP {status_http}: "
                f"{corpo[:1500]}"
            )

        try:
            return json.loads(corpo)

        except json.JSONDecodeError as erro:
            raise MercadoLivreAffiliateError(
                "O gerador de links retornou uma resposta "
                "que não é um JSON válido."
            ) from erro
