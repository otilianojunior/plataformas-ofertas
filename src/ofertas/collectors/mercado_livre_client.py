import logging
import time

import httpx
from sqlalchemy.orm import Session

from ofertas.services.autenticacao_oauth_service import (
    AutenticacaoOAuthService,
)


logger = logging.getLogger(__name__)


class MercadoLivreClient:
    """Cliente HTTP autenticado da API do Mercado Livre."""

    BASE_URL = "https://api.mercadolibre.com"
    MAX_RETRIES = 3
    RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(
        self,
        auth_service: AutenticacaoOAuthService | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.auth_service = auth_service or AutenticacaoOAuthService()
        self.timeout = timeout

    def _tempo_espera(
        self,
        resposta: httpx.Response | None,
        tentativa: int,
    ) -> float:
        if resposta is not None:
            try:
                return min(
                    float(resposta.headers["Retry-After"]),
                    60.0,
                )
            except (KeyError, ValueError):
                pass

        return min(2 ** (tentativa + 1), 30)

    def _request(
        self,
        session: Session,
        plataforma_id: int,
        path: str,
        params: dict | None = None,
    ) -> dict:
        access_token = self.auth_service.obter_access_token(
            session,
            plataforma_id,
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        with httpx.Client(timeout=self.timeout) as cliente:
            for tentativa in range(self.MAX_RETRIES + 1):
                resposta = None

                try:
                    resposta = cliente.get(
                        f"{self.BASE_URL}{path}",
                        params=params,
                        headers=headers,
                    )

                except httpx.TransportError:
                    if tentativa == self.MAX_RETRIES:
                        raise

                    espera = self._tempo_espera(
                        None,
                        tentativa,
                    )

                    logger.warning(
                        "Falha de comunicação com o Mercado Livre "
                        "em %s. Tentativa %s/%s em %.1f segundos.",
                        path,
                        tentativa + 1,
                        self.MAX_RETRIES,
                        espera,
                    )

                    time.sleep(espera)
                    continue

                if resposta.status_code == 401:
                    raise httpx.HTTPStatusError(
                        "Token recusado pelo Mercado Livre.",
                        request=resposta.request,
                        response=resposta,
                    )

                if resposta.status_code not in self.RETRYABLE_STATUS:
                    resposta.raise_for_status()
                    return resposta.json()

                if tentativa == self.MAX_RETRIES:
                    resposta.raise_for_status()

                espera = self._tempo_espera(
                    resposta,
                    tentativa,
                )

                logger.warning(
                    "Mercado Livre retornou HTTP %s em %s. "
                    "Tentativa %s/%s em %.1f segundos.",
                    resposta.status_code,
                    path,
                    tentativa + 1,
                    self.MAX_RETRIES,
                    espera,
                )

                time.sleep(espera)

        raise RuntimeError("Não foi possível concluir a requisição.")

    def buscar_destaques(
        self,
        session: Session,
        plataforma_id: int,
        id_categoria: str,
    ) -> dict:
        """Busca os produtos em destaque de uma categoria."""
        if not id_categoria.strip():
            raise ValueError("O ID da categoria é obrigatório.")

        return self._request(
            session,
            plataforma_id,
            f"/highlights/MLB/category/{id_categoria.strip()}",
        )

    def buscar_detalhes_produto(
        self,
        session: Session,
        plataforma_id: int,
        product_id: str,
    ) -> dict:
        """Busca os detalhes de um produto."""
        if not product_id.strip():
            raise ValueError("O ID do produto é obrigatório.")

        return self._request(
            session,
            plataforma_id,
            f"/products/{product_id.strip()}",
        )

    def buscar_anuncios_produto(
        self,
        session: Session,
        plataforma_id: int,
        product_id: str,
    ) -> dict:
        """Busca os anúncios disponíveis para um produto."""
        if not product_id.strip():
            raise ValueError("O ID do produto é obrigatório.")

        return self._request(
            session,
            plataforma_id,
            f"/products/{product_id.strip()}/items",
        )