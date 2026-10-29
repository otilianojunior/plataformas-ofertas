from decimal import Decimal
from html import escape
from urllib.parse import urlparse


RODAPE_PUBLICACAO = "⚠️ Oferta por tempo limitado. Os preços podem mudar."


def formatar_preco(valor: Decimal) -> str:
    """Formata um valor monetário no padrão brasileiro."""
    valor_formatado = f"{valor:,.2f}"
    valor_formatado = (
        valor_formatado.replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    return f"R$ {valor_formatado}"


def validar_link_afiliado(link: str | None) -> str:
    """Exige um link de afiliado HTTP ou HTTPS válido."""
    if not link:
        raise ValueError(
            "A oferta não pode ser publicada sem link de afiliado."
        )

    link = link.strip()
    partes = urlparse(link)

    if partes.scheme not in {"http", "https"} or not partes.netloc:
        raise ValueError("O link de afiliado informado é inválido.")

    return link


def formatar_mensagem(oferta, nome_plataforma: str) -> str:
    """Gera a legenda HTML padronizada para publicação no Telegram."""
    link_afiliado = validar_link_afiliado(oferta.affiliate_url)

    titulo = escape(oferta.titulo.strip())
    plataforma = escape(nome_plataforma.strip())

    if not titulo:
        raise ValueError("O título do produto não pode ficar vazio.")

    if not plataforma:
        raise ValueError("O nome da plataforma não pode ficar vazio.")

    partes = [f"<b>{titulo}</b>", ""]

    preco_original = oferta.preco_original
    preco_atual = oferta.preco_atual

    if preco_original is not None and preco_original > preco_atual:
        partes.append(
            f"💰 De: <s>{formatar_preco(preco_original)}</s>"
        )

    partes.append(f"🔥 <b>Por: {formatar_preco(preco_atual)}</b>")
    partes.append("")
    preposicao = "no" if plataforma.casefold() == "mercado livre" else "na"
    partes.append(
        f'🛒 Link do produto {preposicao} <b>{plataforma}</b>:\n'
        f'<a href="{escape(link_afiliado, quote=True)}">Comprar produto</a>'
    )
    partes.append("")
    partes.append(RODAPE_PUBLICACAO)

    return "\n".join(partes)
