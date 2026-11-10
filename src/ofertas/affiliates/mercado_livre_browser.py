import logging
import shutil
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import BrowserContext, sync_playwright

from ofertas.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


class MercadoLivreBrowserError(RuntimeError):
    """Erro na inicialização ou comunicação com o Chrome."""


class MercadoLivreLoginRequiredError(MercadoLivreBrowserError):
    """Indica que a sessão do Mercado Livre não está autenticada."""


class MercadoLivreBrowser:
    """Gerencia o Chrome persistente com a sessão do Mercado Livre."""

    HOME_URL = "https://www.mercadolivre.com.br/"

    TEMPO_LIMITE_INICIALIZACAO = 30
    TIMEOUT_CDP = 2
    TIMEOUT_CONEXAO_PLAYWRIGHT = 15_000
    TIMEOUT_NAVEGACAO = 30_000

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()

    def _validar_configuracao_cdp(self) -> int:
        try:
            parsed = urlsplit(
                self.settings.mercado_livre_chrome_cdp_url
            )
            porta = parsed.port

        except ValueError as erro:
            raise MercadoLivreBrowserError(
                "Endereço CDP inválido."
            ) from erro

        if parsed.scheme != "http":
            raise MercadoLivreBrowserError(
                "O endereço CDP deve utilizar HTTP."
            )

        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise MercadoLivreBrowserError(
                "O Chrome CDP deve estar acessível somente localmente."
            )

        if porta is None:
            raise MercadoLivreBrowserError(
                "A porta do Chrome CDP não foi configurada."
            )

        return porta

    def _endpoint_cdp(self) -> str:
        return (
            self.settings.mercado_livre_chrome_cdp_url.rstrip("/")
            + "/json/version"
        )

    def _cdp_disponivel(self) -> bool:
        try:
            response = httpx.get(
                self._endpoint_cdp(),
                timeout=self.TIMEOUT_CDP,
            )
            return response.is_success

        except httpx.HTTPError:
            return False

    def _localizar_chrome(self) -> str:
        chrome_path = self.settings.mercado_livre_chrome_path
        executavel = shutil.which(chrome_path)

        if executavel is None:
            raise FileNotFoundError(
                "Executável do Chrome não encontrado. "
                "Verifique MERCADO_LIVRE_CHROME_PATH."
            )

        return executavel

    def _iniciar_chrome(self) -> None:
        if self._cdp_disponivel():
            logger.info("Chrome CDP já está disponível.")
            return

        porta = self._validar_configuracao_cdp()
        chrome = self._localizar_chrome()

        perfil = Path(
            self.settings.mercado_livre_chrome_profile_dir
        ).expanduser()

        perfil.mkdir(parents=True, exist_ok=True)

        logger.info("Iniciando Chrome com o perfil persistente do projeto.")

        subprocess.Popen(
            [
                chrome,
                f"--user-data-dir={perfil}",
                "--profile-directory=Default",
                "--remote-debugging-address=127.0.0.1",
                f"--remote-debugging-port={porta}",
                "--no-first-run",
                "--no-default-browser-check",
                self.HOME_URL,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        inicio = time.monotonic()

        while (
            time.monotonic() - inicio
            < self.TEMPO_LIMITE_INICIALIZACAO
        ):
            if self._cdp_disponivel():
                logger.info("Chrome CDP disponível.")
                return

            time.sleep(1)

        raise MercadoLivreBrowserError(
            "O Chrome foi iniciado, mas o CDP não ficou disponível "
            "dentro do tempo limite."
        )

    @contextmanager
    def connect(self) -> Iterator[BrowserContext]:
        """Conecta ao Chrome e disponibiliza o contexto autenticado."""

        self._validar_configuracao_cdp()
        self._iniciar_chrome()

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                self.settings.mercado_livre_chrome_cdp_url,
                timeout=self.TIMEOUT_CONEXAO_PLAYWRIGHT,
            )

            try:
                if not browser.contexts:
                    raise MercadoLivreBrowserError(
                        "Nenhum contexto de navegador foi encontrado."
                    )

                yield browser.contexts[0]

            finally:
                # Desconecta o Playwright sem encerrar o Chrome remoto.
                browser.close()

    def check_session(self) -> dict:
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