from decimal import Decimal
from types import SimpleNamespace

import pytest

from ofertas.core.autenticacao import gerar_hash_senha, ler_token_sessao, verificar_senha
from ofertas.core.elegibilidade import desconto_plausivel, produto_elegivel


def test_hash_de_senha_tem_sal_e_confere():
    primeiro, segundo = gerar_hash_senha("senha-forte-1"), gerar_hash_senha("senha-forte-1")
    assert primeiro != segundo
    assert "senha-forte-1" not in primeiro
    assert verificar_senha("senha-forte-1", primeiro)
    assert not verificar_senha("senha-forte-2", primeiro)
    assert not verificar_senha("x", "formato-invalido")


def test_senha_curta_e_recusada():
    with pytest.raises(ValueError):
        gerar_hash_senha("curta")


def test_token_adulterado_e_recusado():
    assert ler_token_sessao("nao-e-um-token") is None


def _produto(desconto):
    return SimpleNamespace(
        percentual_desconto=Decimal(desconto),
        status_monitoramento="ativo",
        disponivel=True,
        status_link_afiliado="gerado",
        url_afiliada="https://exemplo.com/a",
    )


def test_desconto_acima_do_teto_nao_e_elegivel():
    categoria = SimpleNamespace(desconto_minimo_percentual=Decimal("10"))
    assert desconto_plausivel(Decimal("90"))
    assert not desconto_plausivel(Decimal("96"))
    assert produto_elegivel(_produto("50"), categoria)
    assert not produto_elegivel(_produto("96"), categoria)
    assert not produto_elegivel(_produto("5"), categoria)
