"""Confere se um produto da busca por termo é mesmo o que a categoria promete.

A busca das lojas devolve resultados aproximados: em "headset mchose" vem
headset de outra marca, em "mouse corsair" vem mousepad, em "teclado akko" vem
kit de parafusos. Vale só para categorias com `termo_busca` (ex.: "mouse razer").
"""

import re
import unicodedata

# Palavras do termo que dizem o tipo do produto; o resto do termo é a marca.
TIPOS = frozenset(
    "mouse mouses teclado teclados headset headsets fone fones".split()
)

# Tipo do produto quando aparece no título (ordem importa, ver abaixo).
TIPOS_NO_TITULO = TIPOS | {"headphone", "headphones", "earbuds"}

# Peças e acessórios de periféricos. Fica de fora o que aparece no título do
# próprio produto (cabo, adaptador, case, suporte, compatível, switch, dongle...).
ACESSORIOS = frozenset(
    """
    almofada almofadas earpad earpads espuma espumas pad keycap keycaps
    parafuso parafusos estabilizador estabilizadores capa estojo bolsa saco
    pelicula protetor substituicao reposicao grip skate skates adesivo adesivos
    """.split()
)


def _palavras(texto: str) -> list[str]:
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(c)
    )
    return re.findall(r"[a-z0-9]+", sem_acento)


def _primeira(palavras: list[str], conjunto: frozenset[str]) -> int | None:
    return next((i for i, p in enumerate(palavras) if p in conjunto), None)


def _eh_acessorio(palavras: list[str]) -> str | None:
    """"Almofada para Headset X" é acessório; "Headset X com almofadas", não."""

    if "mousepad" in palavras or "mouse pad" in " ".join(palavras):
        return "mousepad"

    acessorio = _primeira(palavras, ACESSORIOS)
    if acessorio is None:
        return None

    tipo = _primeira(palavras, TIPOS_NO_TITULO)
    if tipo is not None and tipo < acessorio:
        return None

    return palavras[acessorio]


def motivo_fora_da_categoria(titulo: str, termo_busca: str | None) -> str | None:
    """None se o produto condiz com a categoria; senão, o motivo do descarte."""

    if not termo_busca:
        return None

    palavras = _palavras(titulo)
    titulo_palavras = set(palavras)
    termo = set(_palavras(termo_busca))

    marca = {p for p in termo - TIPOS if len(p) > 1}
    if marca - titulo_palavras:
        return f"marca {' '.join(sorted(marca))} ausente do título"

    acessorio = _eh_acessorio(palavras)
    if acessorio:
        return f"acessório ({acessorio})"

    # Kit teclado + mouse numa categoria de teclado ou de mouse.
    tipos_do_termo = termo & TIPOS
    if tipos_do_termo & {"mouse", "mouses", "teclado", "teclados"} and {
        "mouse",
        "teclado",
    } <= titulo_palavras:
        return "kit teclado e mouse"

    return None
