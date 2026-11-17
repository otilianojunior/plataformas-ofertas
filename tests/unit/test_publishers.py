"""Publishers do Telegram e do WhatsApp sobre a base comum."""

import time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.models.publicacao import Publicacao
from ofertas.publishers.telegram import TelegramPublisher
from ofertas.publishers.whatsapp import WhatsAppPublisher
from ofertas.publishers.whatsapp_web import (
    WhatsAppGrupoNaoEncontradoError,
    WhatsAppSessaoError,
    WhatsAppWebClient,
    WhatsAppWebError,
)


def _produto():
    return SimpleNamespace(
        id=1, plataforma_id=1, titulo="Headset Razer Kraken", url_afiliada="https://meli.la/x",
        status_link_afiliado="gerado", elegivel_divulgacao=True, disponivel=True,
        status_monitoramento="ativo", preco_atual=Decimal("199.90"),
        preco_original=Decimal("299.90"), percentual_desconto=Decimal("33"),
        imagem_url="https://img/x.jpg",
    )


def _sessao(codigo_canal, configuracao=None):
    objetos = {
        PlataformaDivulgacao: PlataformaDivulgacao(id=7, codigo=codigo_canal, status_plataforma=True),
        Plataforma: Plataforma(id=1, nome="Mercado Livre"),
        ConfiguracaoSistema: configuracao,
    }
    session = Mock()
    session.get.side_effect = lambda modelo, _id: objetos.get(modelo)
    return session


def _repositorios(destino):
    destino_repository = Mock()
    destino_repository.buscar_por_id.return_value = destino
    publicacao_repository = Mock()
    publicacao_repository.buscar_ativa.return_value = None
    publicacao_repository.criar.side_effect = lambda _s, **kw: Publicacao(
        status_publicacao="pendente", **{k: v for k, v in kw.items() if k != "destino_id"},
        destino_divulgacao_id=kw["destino_id"],
    )
    publicacao_repository.contar_publicadas_canal_desde.return_value = 0
    return destino_repository, publicacao_repository


GRUPO_WHATSAPP = DestinoDivulgacao(
    id=3, plataforma_divulgacao_id=7, identificador_destino="Ofertas Tech", status_destino=True,
)


def _whatsapp(cliente, limite=30):
    destino_repository, publicacao_repository = _repositorios(GRUPO_WHATSAPP)
    settings = SimpleNamespace(whatsapp_limite_diario=limite, whatsapp_intervalo_minimo_segundos=120)
    return WhatsAppPublisher(destino_repository, publicacao_repository, cliente, settings), publicacao_repository


# --- WhatsApp -----------------------------------------------------------------

def test_whatsapp_envia_para_o_grupo_pelo_nome_com_formatacao_do_whatsapp():
    cliente = Mock()
    publisher, _ = _whatsapp(cliente)

    publicacao = publisher.publicar(_sessao("whatsapp"), _produto(), 3)

    assert publicacao.status_publicacao == "publicada"
    grupo, texto, imagem = cliente.enviar.call_args.args
    assert grupo == "Ofertas Tech"
    assert texto.startswith("*Headset Razer Kraken*")
    assert "https://meli.la/x" in texto and "<b>" not in texto
    assert imagem == "https://img/x.jpg"


def test_whatsapp_respeita_o_limite_diario():
    cliente = Mock()
    publisher, publicacao_repository = _whatsapp(cliente, limite=30)
    publicacao_repository.contar_publicadas_canal_desde.return_value = 30

    with pytest.raises(ValueError, match="Limite diário do WhatsApp"):
        publisher.publicar(_sessao("whatsapp"), _produto(), 3)

    cliente.enviar.assert_not_called()
    publicacao_repository.criar.assert_not_called()


def test_sessao_desconectada_pausa_as_publicacoes_no_whatsapp():
    configuracao = ConfiguracaoSistema(id=1, publicacao_whatsapp_ativa=True, automacoes_ativas=True)
    cliente = Mock()
    cliente.enviar.side_effect = WhatsAppSessaoError("pede QR Code")
    publisher, _ = _whatsapp(cliente)

    publicacao = publisher.publicar(_sessao("whatsapp", configuracao), _produto(), 3)

    assert publicacao.status_publicacao == "falhou"
    assert "QR Code" in publicacao.erro
    assert configuracao.publicacao_whatsapp_ativa is False


def test_grupo_nao_encontrado_falha_sem_pausar_o_canal():
    configuracao = ConfiguracaoSistema(id=1, publicacao_whatsapp_ativa=True, automacoes_ativas=True)
    cliente = Mock()
    cliente.enviar.side_effect = WhatsAppGrupoNaoEncontradoError("Grupo 'X' não encontrado")
    publisher, _ = _whatsapp(cliente)

    publicacao = publisher.publicar(_sessao("whatsapp", configuracao), _produto(), 3)

    assert publicacao.status_publicacao == "falhou"
    assert configuracao.publicacao_whatsapp_ativa is True


def test_publisher_do_whatsapp_recusa_grupo_do_telegram():
    publisher, _ = _whatsapp(Mock())

    with pytest.raises(ValueError, match="não é do WhatsApp"):
        publisher.publicar(_sessao("telegram"), _produto(), 3)


# --- Telegram (refatorado sobre a base) ---------------------------------------

def test_telegram_continua_enviando_foto_com_legenda_html():
    destino = DestinoDivulgacao(
        id=1, plataforma_divulgacao_id=7, identificador_destino="-100123",
        status_destino=True, credencial_divulgacao_id=9,
    )
    destino_repository, publicacao_repository = _repositorios(destino)
    credenciais = Mock()
    credenciais.buscar_por_id.return_value = SimpleNamespace(
        status_credencial="ativa", plataforma_divulgacao_id=7,
        tipo_credencial="bot_telegram", valor_criptografado="x",
    )
    publisher = TelegramPublisher(credenciais, destino_repository, publicacao_repository)

    resposta = Mock(json=Mock(return_value={"ok": True}), raise_for_status=Mock())
    with (
        patch("ofertas.publishers.telegram.descriptografar_credencial", return_value="TOKEN"),
        patch("ofertas.publishers.telegram.httpx.post", return_value=resposta) as post,
    ):
        publicacao = publisher.publicar(_sessao("telegram"), _produto(), 1)

    assert publicacao.status_publicacao == "publicada"
    assert post.call_args.args[0].endswith("/sendPhoto")
    assert post.call_args.kwargs["data"]["parse_mode"] == "HTML"


def test_erro_do_telegram_nao_grava_o_token():
    destino = DestinoDivulgacao(
        id=1, plataforma_divulgacao_id=7, identificador_destino="-100123",
        status_destino=True, credencial_divulgacao_id=9,
    )
    destino_repository, publicacao_repository = _repositorios(destino)
    credenciais = Mock()
    credenciais.buscar_por_id.return_value = SimpleNamespace(
        status_credencial="ativa", plataforma_divulgacao_id=7,
        tipo_credencial="bot_telegram", valor_criptografado="x",
    )
    publisher = TelegramPublisher(credenciais, destino_repository, publicacao_repository)
    erro = httpx.HTTPStatusError(
        "Client error for url https://api.telegram.org/botSEGREDO/sendPhoto",
        request=Mock(),
        response=Mock(status_code=400, json=Mock(return_value={"description": "chat not found"})),
    )

    with (
        patch("ofertas.publishers.telegram.descriptografar_credencial", return_value="SEGREDO"),
        patch("ofertas.publishers.telegram.httpx.post", side_effect=erro),
    ):
        publicacao = publisher.publicar(_sessao("telegram"), _produto(), 1)

    assert publicacao.erro == "HTTP 400: chat not found"
    assert "SEGREDO" not in publicacao.erro


# --- cliente do WhatsApp Web --------------------------------------------------

@pytest.fixture
def cliente():
    WhatsAppWebClient._ultimo_envio = None
    WhatsAppWebClient.encerrando.clear()
    settings = SimpleNamespace(whatsapp_intervalo_minimo_segundos=120)
    yield WhatsAppWebClient(browser=Mock(), settings=settings)
    WhatsAppWebClient._ultimo_envio = None
    WhatsAppWebClient.encerrando.clear()


def test_intervalo_minimo_vale_para_todos_os_grupos(cliente):
    WhatsAppWebClient._ultimo_envio = time.monotonic()

    with patch.object(WhatsAppWebClient.encerrando, "wait", return_value=False) as espera:
        cliente._aguardar_intervalo()

    assert 119 < espera.call_args.args[0] <= 120


def test_encerramento_cancela_a_espera_do_intervalo(cliente):
    WhatsAppWebClient._ultimo_envio = time.monotonic()
    WhatsAppWebClient.encerrando.set()

    with pytest.raises(WhatsAppWebError, match="encerrando"):
        cliente._aguardar_intervalo()


def test_qr_code_na_tela_e_sessao_desconectada(cliente):
    pagina = MagicMock()
    pagina.locator.return_value.count.return_value = 1  # QR Code presente

    with pytest.raises(WhatsAppSessaoError, match="QR Code"):
        cliente._aguardar_pronto(pagina)


def test_nao_envia_se_abriu_outra_conversa(cliente):
    pagina = MagicMock()
    pagina.locator.return_value.first.inner_text.return_value = "Família"

    with pytest.raises(WhatsAppGrupoNaoEncontradoError, match="em vez de"):
        cliente._abrir_grupo(pagina, "Ofertas Tech")


def test_quebra_de_linha_nao_envia_a_mensagem():
    pagina = MagicMock()

    WhatsAppWebClient._digitar(pagina, "linha 1\n\nlinha 3")

    teclas = [c.args[0] for c in pagina.keyboard.press.call_args_list]
    assert teclas == ["Shift+Enter", "Shift+Enter"]  # nunca "Enter"
    assert [c.args[0] for c in pagina.keyboard.insert_text.call_args_list] == ["linha 1", "linha 3"]
