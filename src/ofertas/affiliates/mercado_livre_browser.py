import logging

from ofertas.core.chrome_dedicado import ChromeDedicado, ChromeDedicadoError
from ofertas.core.config import Settings, get_settings


logger = logging.getLogger(__name__)

# Mantido por compatibilidade: quem captura o erro do Chrome do ML.
MercadoLivreBrowserError = ChromeDedicadoError


class MercadoLivreLoginRequiredError(ChromeDedicadoError):
    """Indica que a sessão do Mercado Livre não está autenticada."""


class MercadoLivreBrowser(ChromeDedicado):
    """Chrome persistente com a sessão do Mercado Livre."""

    HOME_URL = "https://www.mercadolivre.com.br/"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        super().__init__(
            perfil=self.settings.mercado_livre_chrome_profile_dir,
            cdp_url=self.settings.mercado_livre_chrome_cdp_url,
            chrome_path=self.settings.mercado_livre_chrome_path,
        )

    def verificar_sessao(self) -> dict:
        """Verifica se o perfil persistente mantém a sessão autenticada."""

        try:
            with self.connect() as context:
                page = context.new_page()

                try:
                    page.goto(
                        self.HOME_URL,
                        wait_until="domcontentloaded",
                        timeout=self.TIMEOUT_NAVEGACAO,
                    )

                    page.wait_for_timeout(2000)

                    cookies = context.cookies(self.HOME_URL)

                    csrf_present = any(
                        cookie["name"] == "_csrf"
                        for cookie in cookies
                    )

                    login_button_present = (
                        page.get_by_text("Entrar", exact=True).count() > 0
                    )

                    resultado = {
                        "authenticated": (
                            csrf_present and not login_button_present
                        ),
                        "cookies": len(cookies),
                        "csrf": csrf_present,
                        "login_button": login_button_present,
                        "title": page.title(),
                        "url": page.url,
                    }

                finally:
                    if not page.is_closed():
                        page.close()

            if not resultado["authenticated"]:
                raise MercadoLivreLoginRequiredError(
                    "A sessão do Mercado Livre não está autenticada."
                )

            return resultado

        except MercadoLivreLoginRequiredError:
            raise

        except Exception as erro:
            raise MercadoLivreBrowserError(
                f"Falha ao verificar a sessão do Mercado Livre: {erro}"
            ) from erro