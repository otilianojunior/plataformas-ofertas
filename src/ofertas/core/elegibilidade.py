from decimal import Decimal

from ofertas.core.config import get_settings
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.produto import Produto


def desconto_plausivel(desconto: Decimal | None) -> bool:
    """Falso quando o desconto passa do teto (preço "de" inflado pela loja)."""

    return desconto is None or desconto <= get_settings().desconto_maximo_percentual


def produto_elegivel(
    produto: Produto,
    categoria: PlataformaCategoria | None,
) -> bool:
    """Regra única de elegibilidade para divulgação."""

    desconto = produto.percentual_desconto

    desconto_atingido = (
        categoria is not None
        and desconto is not None
        and desconto >= categoria.desconto_minimo_percentual
        and desconto_plausivel(desconto)
    )

    return bool(
        produto.status_monitoramento == "ativo"
        and produto.disponivel
        and desconto_atingido
        and produto.status_link_afiliado == "gerado"
        and produto.url_afiliada
    )
