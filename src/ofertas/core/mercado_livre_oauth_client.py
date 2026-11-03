import httpx


class MercadoLivreOAuthClient:
    """Cliente HTTP responsável pelo fluxo OAuth do Mercado Livre."""

    TOKEN_URL = "https://api.mercadolibre.com/oauth/token"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def trocar_codigo_por_tokens(
        self,
        *,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> dict:
        """Troca o código de autorização pelos tokens OAuth."""
        if not all(
            valor.strip()
            for valor in (client_id, client_secret, code, redirect_uri)
        ):
            raise ValueError("Todos os parâmetros OAuth são obrigatórios.")

        dados = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        return self._solicitar_tokens(dados)

    def renovar_tokens(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict:
        """Solicita novos tokens usando o refresh token atual."""
        if not all(
            valor.strip()
            for valor in (client_id, client_secret, refresh_token)
        ):
            raise ValueError("As credenciais OAuth são obrigatórias.")

        dados = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }

        return self._solicitar_tokens(dados)

    def _solicitar_tokens(self, dados: dict) -> dict:
        with httpx.Client(timeout=self.timeout) as cliente:
            resposta = cliente.post(self.TOKEN_URL, data=dados)
            resposta.raise_for_status()
            return resposta.json()