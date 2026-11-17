"""Chrome dedicado do projeto, controlado via CDP (Mercado Livre, WhatsApp)."""

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



logger = logging.getLogger(__name__)


class ChromeDedicadoError(RuntimeError):
    """Erro na inicialização ou comunicação com o Chrome."""


class ChromeDedicado:
    """Chrome com perfil próprio do projeto, controlado pela porta CDP local.

    Cada integração (Mercado Livre, WhatsApp) usa seu perfil e sua porta,
    para as sessões ficarem isoladas.
    """

    HOME_URL = "about:blank"

    TEMPO_LIMITE_INICIALIZACAO = 30
    TIMEOUT_CDP = 2
    TIMEOUT_CONEXAO_PLAYWRIGHT = 15_000
    TIMEOUT_NAVEGACAO = 30_000

    def __init__(
        self,
        *,
        perfil: Path,
        cdp_url: str,
        chrome_path: str | None = None,
    ) -> None:
        self.perfil = Path(perfil)
        self.cdp_url = cdp_url
        self.chrome_path = chrome_path

    def _validar_configuracao_cdp(self) -> int:
        try:
            parsed = urlsplit(
                self.cdp_url
            )
            porta = parsed.port

        except ValueError as erro:
            raise ChromeDedicadoError(
                "Endereço CDP inválido."
            ) from erro

        if parsed.scheme != "http":
            raise ChromeDedicadoError(
                "O endereço CDP deve utilizar HTTP."
            )

        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ChromeDedicadoError(
                "O Chrome CDP deve estar acessível somente localmente."
            )

        if porta is None:
            raise ChromeDedicadoError(
                "A porta do Chrome CDP não foi configurada."
            )

        return porta

    def _endpoint_cdp(self) -> str:
        return (
            self.cdp_url.rstrip("/")
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

    CANDIDATOS_CHROME = (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    )

    def _localizar_chrome(self) -> str:
        """Usa o executável configurado ou detecta o Chrome instalado."""

        configurado = self.chrome_path
        candidatos = (configurado,) if configurado else self.CANDIDATOS_CHROME

        for candidato in candidatos:
            executavel = shutil.which(candidato)

            if executavel is not None:
                return executavel

        raise FileNotFoundError(
            "Executável do Chrome não encontrado "
            f"(procurado: {', '.join(candidatos)}). "
            "Instale o Google Chrome ou defina MERCADO_LIVRE_CHROME_PATH."
        )

    def caminho_perfil(self) -> Path:
        return self.perfil

    def esta_aberto(self) -> bool:
        """Indica se há um Chrome respondendo na porta CDP configurada."""

        return self._cdp_disponivel()

    def abrir(self) -> None:
        """Abre o Chrome do projeto (ou reaproveita um já aberto)."""

        self._validar_configuracao_cdp()
        self._iniciar_chrome()

    def fechar(self) -> bool:
        """Fecha o Chrome do projeto pelo CDP. Retorna False se já estava fechado."""

        if not self._cdp_disponivel():
            return False

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                self.cdp_url,
                timeout=self.TIMEOUT_CONEXAO_PLAYWRIGHT,
            )
            sessao = browser.new_browser_cdp_session()
            sessao.send("Browser.close")

        return True

    def _iniciar_chrome(self) -> None:
        if self._cdp_disponivel():
            logger.info("Chrome CDP já está disponível.")
            return

        porta = self._validar_configuracao_cdp()
        chrome = self._localizar_chrome()

        perfil = self.caminho_perfil()

        perfil.mkdir(parents=True, exist_ok=True)

        logger.info("Iniciando Chrome com o perfil %s.", perfil)

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

        raise ChromeDedicadoError(
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
                self.cdp_url,
                timeout=self.TIMEOUT_CONEXAO_PLAYWRIGHT,
            )

            try:
                if not browser.contexts:
                    raise ChromeDedicadoError(
                        "Nenhum contexto de navegador foi encontrado."
                    )

                yield browser.contexts[0]

            finally:
                # Desconecta o Playwright sem encerrar o Chrome remoto.
                browser.close()
