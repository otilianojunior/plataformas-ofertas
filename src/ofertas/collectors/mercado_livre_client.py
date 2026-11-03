import httpx


class MercadoLivreClient:
    """Cliente HTTP para consultar a API pública do Mercado Livre."""

    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def buscar_produtos(
        self,
        consulta: str,
        *,
        limite: int = 50,
        offset: int = 0,
    ) -> dict:
        """Busca produtos no catálogo do Mercado Livre."""
        if not consulta.strip():
            raise ValueError("O termo de busca não pode ficar vazio.")

        if not 1 <= limite <= 50:
            raise ValueError("O limite deve estar entre 1 e 50.")

        if offset < 0:
            raise ValueError("O offset não pode ser negativo.")

        url = f"{self.BASE_URL}/products/search"
        parametros = {
            "q": consulta.strip(),
            "limit": limite,
            "offset": offset,
        }

        with httpx.Client(timeout=self.timeout) as cliente:
            resposta = cliente.get(url, params=parametros)
            resposta.raise_for_status()
            return resposta.json()