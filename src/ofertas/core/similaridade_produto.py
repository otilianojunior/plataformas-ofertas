"""Identifica o mesmo produto pelo título, mesmo vindo de lojas diferentes.

Sem IA não dá para acertar 100%, então a comparação é conservadora: prefere
tratar como produtos diferentes quando há um sinal claro de variação
(modelo, capacidade, "Ultra"/"Pro"...), e como o mesmo produto quando os
títulos são quase iguais. Cor, loja e palavras de marketing são ignoradas.

Exemplos:
- "Galaxy A17 256gb ... - Azul" e "Galaxy A17 256gb ... - Preto": mesmo produto
- "Galaxy S25 Ultra 256gb" e "Galaxy S25 256gb": diferentes (variante Ultra)
- "Ventus NX PCH-VTN-BK01" e "Ventus NX Reverse PCH-VTNR-BK01": diferentes
- "iPhone 16 256 GB" e "iPhone 16 128 GB": diferentes (capacidade)
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache


PALAVRAS_IGNORADAS = frozenset(
    """
    a o e de da do das dos com para por em no na nos nas um uma ao aos
    the and for with
    cor novo nova original oficial lancamento promocao oferta envio imediato
    frete gratis garantia nota fiscal nf distribuidor autorizado loja
    produto unidade un kit pronta entrega brasil versao modelo
    preto preta branco branca azul vermelho vermelha verde rosa roxo roxa
    cinza prata dourado dourada amarelo amarela laranja lilas lavanda bege
    marrom grafite titanio grafite black white blue red green pink purple
    gray grey silver gold titanium silverblue marinho escuro claro
    """.split()
)

# Palavras que indicam outra versão do mesmo modelo base.
VARIANTES = frozenset(
    """
    ultra pro max plus lite mini fe reverse slim air neo se prime elite
    wireless
    """.split()
)

# Produtos que acompanham outro (o "Suporte para Cooler" não é o cooler).
ACESSORIOS = frozenset(
    """
    suporte capa case pelicula cabo adaptador carregador protetor bolsa
    refil base pasta controladora hub extensor
    """.split()
)

# Especificações (256gb, 120hz, 50mp, 4k, 5g...) não são código de modelo.
_ESPECIFICACAO = re.compile(
    r"^\d+(?:[.,]\d+)?(?:gb|tb|mb|hz|mp|mah|w|mm|cm|v|ms|k|g|p|pol|polegadas|"
    r"x|ghz|mhz|rpm|dpi|ml|l|kg)$"
)
# Padrões técnicos comuns a muitos produtos (plataforma, memória, conexões,
# layout de teclado, medidas e resoluções): não identificam um modelo.
_CODIGO_GENERICO = re.compile(
    r"^(?:ddr\d|am\d|lga\d*|pcie\d*|usb\d*|hdr\d*|wifi\d*|ip\d{2}|ipx\d|"
    r"abnt\d?|gen\d|sata\d*|rj\d+|h\d{3}|\d+x\d+(?:mm|cm)?|"
    r"m\d|ws\d+|bt\d|v\d(?:\.\d)?|"
    r"\d+(?:gb|tb)\d+(?:gb|tb)?)$"
)
_CAPACIDADE = re.compile(r"^(\d+)(gb|tb)$")
_TAMANHO_TELA = re.compile(
    r"(?<![\d.,])(\d{2}(?:[.,]\d)?)\s*(?:\"|''|”|″|pol\b|polegadas)"
)
_CODIGO_HIFENIZADO = re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)+\b")


@dataclass(frozen=True)
class AssinaturaProduto:
    tokens: frozenset[str]
    codigos: frozenset[str]
    armazenamento: frozenset[str]
    telas: frozenset[float]
    variantes: frozenset[str]
    acessorios: frozenset[str]


def _sem_acento(texto: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )


def _eh_codigo(token: str) -> bool:
    """Código de modelo: mistura letras e dígitos (a17, 24b35hm2, mq19v)."""

    return (
        len(token) >= 3
        and any(c.isdigit() for c in token)
        and any(c.isalpha() for c in token)
        and not _ESPECIFICACAO.match(token)
        and not _CODIGO_GENERICO.match(token)
    )


def _armazenamento(token: str) -> bool:
    """256gb/1tb são armazenamento; 4gb/8gb costumam ser RAM."""

    m = _CAPACIDADE.match(token)
    return bool(m) and (m.group(2) == "tb" or int(m.group(1)) >= 32)


@lru_cache(maxsize=20_000)
def assinatura(titulo: str) -> AssinaturaProduto:
    texto = _sem_acento(titulo.casefold())
    telas = frozenset(
        float(valor.replace(",", "."))
        for valor in _TAMANHO_TELA.findall(texto)
    )
    # "256 GB" -> "256gb", "6.7''" -> "6.7"
    texto = re.sub(r"(\d)\s+(gb|tb|mb|hz|mp|mah|ghz)\b", r"\1\2", texto)

    codigos = {
        trecho.replace("-", "")
        for trecho in _CODIGO_HIFENIZADO.findall(texto)
        if _eh_codigo(trecho.replace("-", ""))
    }

    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+(?:[.,][0-9]+)?", texto)
        if token not in PALAVRAS_IGNORADAS and len(token) > 1
    }

    codigos |= {token for token in tokens if _eh_codigo(token)}

    return AssinaturaProduto(
        tokens=frozenset(tokens),
        codigos=frozenset(codigos),
        armazenamento=frozenset(t for t in tokens if _armazenamento(t)),
        telas=telas,
        variantes=frozenset(tokens & VARIANTES),
        acessorios=frozenset(tokens & ACESSORIOS),
    )


def mesmo_produto(titulo_a: str, titulo_b: str) -> bool:
    """Indica se dois títulos provavelmente descrevem o mesmo produto."""

    a = assinatura(titulo_a)
    b = assinatura(titulo_b)

    if not a.tokens or not b.tokens:
        return False

    if a.tokens == b.tokens:
        return True

    # Sinais fortes de que são versões diferentes.
    if a.variantes != b.variantes:
        return False

    if a.acessorios != b.acessorios:
        return False

    if a.armazenamento and b.armazenamento and not (
        a.armazenamento & b.armazenamento
    ):
        return False

    # Telas diferentes (tolerância de 1": 21,5" e 22" são o mesmo monitor).
    if a.telas and b.telas and not any(
        abs(x - y) <= 1 for x in a.telas for y in b.telas
    ):
        return False

    if a.codigos and b.codigos:
        if not (a.codigos & b.codigos):
            return False
        # Mesmo código de modelo: basta o resto do título ser parecido.
        limite_jaccard = 0.4
    else:
        limite_jaccard = 0.7

    comuns = len(a.tokens & b.tokens)
    jaccard = comuns / len(a.tokens | b.tokens)
    contencao = comuns / min(len(a.tokens), len(b.tokens))

    return jaccard >= limite_jaccard or (
        contencao >= 0.9 and min(len(a.tokens), len(b.tokens)) >= 4
    )


@dataclass(frozen=True)
class PublicacaoRecente:
    """Produto publicado no grupo dentro da janela de republicação."""

    produto_id: int
    titulo: str
    preco: Decimal
    loja: str


def bloqueio_republicacao(
    produto_id: int,
    titulo: str,
    preco: Decimal,
    recentes: Iterable[PublicacaoRecente],
) -> PublicacaoRecente | None:
    """Retorna a publicação recente que impede publicar este produto.

    O mesmo produto (mesmo ID ou título equivalente, de qualquer loja) só
    pode voltar ao grupo dentro da janela se o preço for menor que o menor
    preço já publicado para ele.
    """

    iguais = [
        recente
        for recente in recentes
        if recente.produto_id == produto_id
        or mesmo_produto(recente.titulo, titulo)
    ]

    if not iguais:
        return None

    mais_barato = min(iguais, key=lambda recente: recente.preco)

    return mais_barato if preco >= mais_barato.preco else None
