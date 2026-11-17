from decimal import Decimal
from types import SimpleNamespace

import pytest

from ofertas.publishers.mensagem import RODAPE_PUBLICACAO, formatar_mensagem


def _produto(**kwargs):
    valores = dict(
        titulo="Teclado Mecânico <RGB>",
        preco_atual=Decimal("199.90"),
        preco_original=Decimal("349.90"),
        url_afiliada="https://meli.la/abc?x=1&y=2",
    )
    valores.update(kwargs)
    return SimpleNamespace(**valores)


def test_mensagem_completa():
    mensagem = formatar_mensagem(_produto(), "Mercado Livre")

    assert mensagem == (
        "<b>Teclado Mecânico &lt;RGB&gt;</b>\n"
        "\n"
        "💰 De: <s>R$ 349,90</s>\n"
        "🔥 <b>Por: R$ 199,90</b>\n"
        "\n"
        '🛒 Compre no <b>Mercado Livre</b>: '
        '<a href="https://meli.la/abc?x=1&amp;y=2">Ver oferta</a>\n'
        "\n"
        f"{RODAPE_PUBLICACAO}"
    )


def test_link_fica_na_mesma_linha_da_loja():
    linha = next(
        l for l in formatar_mensagem(_produto(), "Shopee").splitlines() if l.startswith("🛒")
    )
    assert linha.startswith("🛒 Compre na <b>Shopee</b>: <a href=")


def test_sem_preco_original_nao_mostra_de():
    assert "De:" not in formatar_mensagem(_produto(preco_original=None), "Shopee")


def test_sem_link_afiliado_nao_publica():
    with pytest.raises(ValueError, match="link de afiliado"):
        formatar_mensagem(_produto(url_afiliada=None), "Shopee")


def test_logs_do_httpx_nao_expoem_o_token_do_telegram():
    """A URL do Telegram contém o token do bot; o httpx a registra em INFO."""
    import logging

    import ofertas.main  # noqa: F401  (aplica a configuração de logs)

    for nome in ("httpx", "httpcore"):
        assert not logging.getLogger(nome).isEnabledFor(logging.INFO)
