"""Envio de mensagens pelo WhatsApp Web (integração NÃO oficial).

Controla um Chrome real, com perfil próprio do projeto, logado por QR Code
na sua conta. Isso viola os termos do WhatsApp e pode levar à restrição ou
ao banimento do número: use um número que você aceite perder e somente em
grupos seus, cujos participantes aceitaram receber as ofertas.

O que este módulo faz para reduzir o risco (comportamento conservador, não
disfarce):
- um envio por vez, para qualquer grupo;
- intervalo mínimo entre mensagens (WHATSAPP_INTERVALO_MINIMO_SEGUNDOS);
- limite diário de mensagens (aplicado pelo publisher);
- para tudo ao ver o QR Code (sessão caiu) ou aviso de restrição da conta.

Os seletores da página ficam todos em SELETORES: quando o WhatsApp mudar o
HTML, ajuste só ali e valide com `make whatsapp-teste`.
"""

import logging
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ofertas.core.chrome_dedicado import ChromeDedicado, ChromeDedicadoError
from ofertas.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


class WhatsAppWebError(RuntimeError):
    """Falha no envio pelo WhatsApp Web."""


class WhatsAppSessaoError(WhatsAppWebError):
    """Sessão desconectada ou conta restrita: as automações devem parar."""


class WhatsAppGrupoNaoEncontradoError(WhatsAppWebError):
    """O grupo não aparece na conta logada (nome diferente ou saiu do grupo)."""


SELETORES = {
    "lista_conversas": "#pane-side",
    "qr_code": "canvas[aria-label*='QR'], div[data-ref] canvas",
    "busca": (
        "#side div[contenteditable='true'][role='textbox'], "
        "#side div[contenteditable='true'][data-tab='3'], "
        "#side input[role='textbox']"
    ),
    "titulo_conversa": "#main header span[title], #main header span[dir='auto']",
    "caixa_mensagem": "#main footer div[contenteditable='true'][role='textbox']",
    "botao_anexar": (
        "#main footer button[title='Anexar'], "
        "#main footer button[aria-label='Anexar'], "
        "#main footer span[data-icon='plus-rounded'], "
        "#main footer span[data-icon='plus'], "
        "#main footer span[data-icon='clip']"
    ),
    "entrada_imagem": "input[type='file'][accept*='image']",
    "legenda": (
        "div[contenteditable='true'][role='textbox'][aria-label*='legenda' i], "
        "div[contenteditable='true'][data-tab='10']"
    ),
    "botao_enviar_midia": (
        "div[role='button'][aria-label='Enviar'], "
        "div[role='button'][aria-label='Send'], "
        "span[data-icon='send'], span[data-icon='wds-ic-send-filled']"
    ),
    "mensagens_enviadas": "#main div.message-out",
    "mensagem_pendente": "span[data-icon='msg-time']",
}

# Textos que indicam conta restrita/banida (pt-BR e inglês).
AVISOS_RESTRICAO = (
    "banido",
    "banned",
    "não tem permissão para usar o whatsapp",
    "not allowed to use whatsapp",
    "conta foi restringida",
    "account is restricted",
    "temporariamente banido",
    "temporarily banned",
)


class WhatsAppWebBrowser(ChromeDedicado):
    """Chrome dedicado à sessão do WhatsApp Web (perfil e porta próprios)."""

    HOME_URL = "https://web.whatsapp.com/"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        super().__init__(
            perfil=self.settings.whatsapp_chrome_profile_dir,
            cdp_url=self.settings.whatsapp_chrome_cdp_url,
            chrome_path=self.settings.mercado_livre_chrome_path,
        )


class WhatsAppWebClient:
    TIMEOUT_CARREGAMENTO_MS = 60_000
    TIMEOUT_ACAO_MS = 15_000
    TIMEOUT_CONFIRMACAO_S = 60

    # Compartilhados no processo: uma aba, um envio por vez, intervalo global.
    _trava = threading.Lock()
    _ultimo_envio: float | None = None
    # Sinalizado no encerramento da API para não ficar esperando o intervalo.
    encerrando = threading.Event()

    def __init__(
        self,
        browser: WhatsAppWebBrowser | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.browser = browser or WhatsAppWebBrowser(self.settings)

    # --- sessão -----------------------------------------------------------------

    @contextmanager
    def _pagina(self) -> Iterator[Page]:
        """Reaproveita a aba do WhatsApp Web (ou abre uma) sem fechá-la."""

        try:
            with self.browser.connect() as contexto:
                pagina = next(
                    (
                        p
                        for p in contexto.pages
                        if p.url.startswith(WhatsAppWebBrowser.HOME_URL)
                    ),
                    None,
                )

                if pagina is None:
                    pagina = contexto.new_page()
                    pagina.goto(
                        WhatsAppWebBrowser.HOME_URL,
                        wait_until="domcontentloaded",
                        timeout=self.TIMEOUT_CARREGAMENTO_MS,
                    )

                yield pagina

        except ChromeDedicadoError as erro:
            raise WhatsAppWebError(
                f"Não foi possível abrir o Chrome do WhatsApp: {erro}"
            ) from erro

    def _verificar_restricao(self, pagina: Page) -> None:
        """Só chamado quando a lista de conversas NÃO carregou: a tela de
        restrição substitui o app. Com a lista visível, o texto da página
        inclui prévias de conversas e daria falso positivo."""

        texto = pagina.locator("body").inner_text(timeout=5_000).casefold()

        for aviso in AVISOS_RESTRICAO:
            if aviso in texto:
                raise WhatsAppSessaoError(
                    "O WhatsApp exibiu um aviso de restrição da conta "
                    f"('{aviso}'). Publicações no WhatsApp pausadas."
                )

    def _aguardar_pronto(self, pagina: Page) -> None:
        """Espera a lista de conversas; QR Code ou restrição param tudo."""

        try:
            pagina.locator(
                f"{SELETORES['lista_conversas']}, {SELETORES['qr_code']}"
            ).first.wait_for(timeout=self.TIMEOUT_CARREGAMENTO_MS)
        except PlaywrightTimeoutError as erro:
            self._verificar_restricao(pagina)
            raise WhatsAppWebError(
                "O WhatsApp Web não carregou a tempo."
            ) from erro

        if pagina.locator(SELETORES["qr_code"]).count() > 0:
            raise WhatsAppSessaoError(
                "O WhatsApp Web está desconectado (pede QR Code). "
                "Rode `make whatsapp-login` e leia o QR Code no celular."
            )

    def status(self) -> dict:
        """Diz se o Chrome está aberto e se a sessão está conectada."""

        if not self.browser.esta_aberto():
            return {"aberto": False, "conectado": False, "detalhe": "Chrome fechado"}

        try:
            with self._pagina() as pagina:
                self._aguardar_pronto(pagina)
        except WhatsAppWebError as erro:
            return {"aberto": True, "conectado": False, "detalhe": str(erro)}

        return {"aberto": True, "conectado": True, "detalhe": "Sessão conectada"}

    # --- envio ------------------------------------------------------------------

    def _aguardar_intervalo(self) -> None:
        """Respeita o intervalo mínimo desde o último envio (todos os grupos)."""

        if WhatsAppWebClient._ultimo_envio is None:
            return

        restante = (
            self.settings.whatsapp_intervalo_minimo_segundos
            - (time.monotonic() - WhatsAppWebClient._ultimo_envio)
        )

        if restante > 0 and self.encerrando.wait(restante):
            raise WhatsAppWebError("Envio cancelado: a API está encerrando.")

    def _abrir_grupo(self, pagina: Page, nome_grupo: str) -> None:
        busca = pagina.locator(SELETORES["busca"]).first
        busca.click(timeout=self.TIMEOUT_ACAO_MS)
        busca.fill("")
        pagina.keyboard.insert_text(nome_grupo)

        resultado = pagina.locator(
            f"{SELETORES['lista_conversas']} span[title={_aspas(nome_grupo)}]"
        ).first

        try:
            resultado.wait_for(timeout=self.TIMEOUT_ACAO_MS)
        except PlaywrightTimeoutError as erro:
            pagina.keyboard.press("Escape")
            raise WhatsAppGrupoNaoEncontradoError(
                f"Grupo '{nome_grupo}' não encontrado na conta conectada. "
                "Confira se o nome do grupo está idêntico ao do WhatsApp."
            ) from erro

        resultado.click(timeout=self.TIMEOUT_ACAO_MS)

        titulo = pagina.locator(SELETORES["titulo_conversa"]).first
        titulo.wait_for(timeout=self.TIMEOUT_ACAO_MS)

        if titulo.inner_text().strip() != nome_grupo:
            raise WhatsAppGrupoNaoEncontradoError(
                f"Abriu a conversa '{titulo.inner_text().strip()}' em vez "
                f"de '{nome_grupo}'. Envio cancelado."
            )

    @staticmethod
    def _digitar(pagina: Page, texto: str) -> None:
        """Insere o texto; Shift+Enter quebra linha (Enter enviaria)."""

        for indice, linha in enumerate(texto.split("\n")):
            if indice:
                pagina.keyboard.press("Shift+Enter")
            if linha:
                pagina.keyboard.insert_text(linha)

    def _baixar_imagem(self, url: str) -> dict:
        resposta = httpx.get(url, timeout=20, follow_redirects=True)
        resposta.raise_for_status()
        tipo = resposta.headers.get("content-type", "image/jpeg").split(";")[0]

        if not tipo.startswith("image/"):
            raise WhatsAppWebError("A imagem do produto não é válida.")

        return {"name": "oferta.jpg", "mimeType": tipo, "buffer": resposta.content}

    def _aguardar_confirmacao(self, pagina: Page, antes: int) -> None:
        """Confirma que a mensagem saiu (apareceu e perdeu o relógio)."""

        enviadas = pagina.locator(SELETORES["mensagens_enviadas"])
        limite = time.monotonic() + self.TIMEOUT_CONFIRMACAO_S

        while time.monotonic() < limite:
            if enviadas.count() > antes:
                ultima = enviadas.last
                if ultima.locator(SELETORES["mensagem_pendente"]).count() == 0:
                    return
            pagina.wait_for_timeout(1_000)

        raise WhatsAppWebError(
            "O WhatsApp não confirmou o envio da mensagem a tempo."
        )

    def enviar(
        self,
        nome_grupo: str,
        texto: str,
        imagem_url: str | None = None,
        *,
        confirmar: bool = True,
    ) -> None:
        """Envia texto (com imagem, se houver) para o grupo.

        Com confirmar=False, prepara a mensagem no grupo e para antes de
        enviar (usado pelo `make whatsapp-teste` para validar os seletores).
        """

        with WhatsAppWebClient._trava:
            self._aguardar_intervalo()

            with self._pagina() as pagina:
                pagina.bring_to_front()
                self._aguardar_pronto(pagina)
                self._abrir_grupo(pagina, nome_grupo)

                antes = pagina.locator(SELETORES["mensagens_enviadas"]).count()

                imagem = None
                if imagem_url:
                    try:
                        imagem = self._baixar_imagem(imagem_url)
                    except (httpx.HTTPError, WhatsAppWebError):
                        logger.warning(
                            "Imagem indisponível; enviando só o texto."
                        )

                if imagem is not None:
                    pagina.locator(SELETORES["botao_anexar"]).first.click(
                        timeout=self.TIMEOUT_ACAO_MS
                    )
                    pagina.locator(SELETORES["entrada_imagem"]).first.set_input_files(
                        imagem
                    )
                    legenda = pagina.locator(SELETORES["legenda"]).first
                    legenda.click(timeout=self.TIMEOUT_ACAO_MS)
                    self._digitar(pagina, texto)
                else:
                    caixa = pagina.locator(SELETORES["caixa_mensagem"]).first
                    caixa.click(timeout=self.TIMEOUT_ACAO_MS)
                    self._digitar(pagina, texto)
                    # tempo para o WhatsApp montar a prévia do link
                    pagina.wait_for_timeout(3_000)

                if not confirmar:
                    logger.info(
                        "Mensagem preparada no grupo '%s' sem enviar (teste).",
                        nome_grupo,
                    )
                    return

                if imagem is not None:
                    pagina.locator(SELETORES["botao_enviar_midia"]).first.click(
                        timeout=self.TIMEOUT_ACAO_MS
                    )
                else:
                    pagina.keyboard.press("Enter")

                WhatsAppWebClient._ultimo_envio = time.monotonic()
                self._aguardar_confirmacao(pagina, antes)


def _aspas(valor: str) -> str:
    """Valor de atributo CSS entre aspas, escapando aspas e barras."""

    return '"' + valor.replace("\\", "\\\\").replace('"', '\\"') + '"'
