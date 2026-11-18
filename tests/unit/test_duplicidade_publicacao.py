"""Mesmo produto (qualquer loja) só volta ao grupo em 24h com preço menor."""

from decimal import Decimal
from unittest.mock import Mock

import pytest

from ofertas.core.similaridade_produto import PublicacaoRecente, bloqueio_republicacao
from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.services.publicacao_lote_service import PublicacaoLoteService
from ofertas.services.publicacao_service import PublicacaoService

FONE_SHOPEE = "Headset Gamer Razer Blackshark V2 X Preto"
FONE_ML = "Headset Razer BlackShark V2 X - Preto - Original Envio Imediato"


def _produto(id, titulo, preco):
    return Mock(id=id, titulo=titulo, preco_atual=Decimal(preco))


def _recente(titulo, preco, loja="Shopee", produto_id=1):
    return PublicacaoRecente(produto_id=produto_id, titulo=titulo, preco=Decimal(preco), loja=loja)


# --- regra pura --------------------------------------------------------------

def test_mesmo_produto_de_outra_loja_mais_caro_e_bloqueado():
    bloqueio = bloqueio_republicacao(2, FONE_ML, Decimal("219.90"), [_recente(FONE_SHOPEE, "199.90")])
    assert bloqueio is not None and bloqueio.loja == "Shopee"


def test_preco_igual_tambem_e_bloqueado():
    assert bloqueio_republicacao(2, FONE_ML, Decimal("199.90"), [_recente(FONE_SHOPEE, "199.90")])


def test_preco_menor_libera():
    assert bloqueio_republicacao(2, FONE_ML, Decimal("189.90"), [_recente(FONE_SHOPEE, "199.90")]) is None


def test_compara_com_o_menor_preco_ja_publicado():
    recentes = [_recente(FONE_SHOPEE, "199.90"), _recente(FONE_ML, "179.90", loja="Mercado Livre", produto_id=9)]
    assert bloqueio_republicacao(3, FONE_ML, Decimal("189.90"), recentes).preco == Decimal("179.90")


def test_mesmo_id_e_bloqueado_mesmo_com_titulo_alterado():
    assert bloqueio_republicacao(1, "Título novo do anúncio", Decimal("250"), [_recente(FONE_SHOPEE, "199.90")])


def test_produto_diferente_passa():
    assert bloqueio_republicacao(2, "Mouse Gamer Logitech G203", Decimal("99"), [_recente(FONE_SHOPEE, "199.90")]) is None


# --- seleção do ciclo --------------------------------------------------------

def _servico(produtos_por_categoria, recentes=(), limite=2):
    session = Mock()
    session.get.side_effect = lambda modelo, _id: (
        ConfiguracaoSistema(id=1, limite_produtos_por_categoria=limite)
        if modelo is ConfiguracaoSistema else Mock(status_plataforma=True)
    )
    categorias = [
        Mock(id=cid, nome_categoria=f"Cat {cid}", plataforma_id=1, desconto_minimo_percentual=0)
        for cid in produtos_por_categoria
    ]
    configuracao_repository = Mock()
    configuracao_repository.buscar_por_destino.return_value = Mock(
        desconto_minimo_percentual=0, preco_minimo=None, preco_maximo=None
    )
    produto_repository = Mock()
    produto_repository.listar_candidatos_publicacao.side_effect = (
        lambda _s, categoria_id, **_k: produtos_por_categoria[categoria_id]
    )
    servico = PublicacaoLoteService(
        configuracao_repository=configuracao_repository,
        destino_repository=Mock(),
        categoria_repository=Mock(listar_por_destino=Mock(return_value=categorias)),
        produto_repository=produto_repository,
        publicacao_service=Mock(),
        janela_execucao_service=Mock(),
        publicacao_repository=Mock(
            listar_publicadas_recentes=Mock(return_value=list(recentes)),
            ultima_publicacao_por_categoria=Mock(return_value={}),
        ),
    )
    return servico, session


def test_produto_barrado_da_lugar_ao_proximo_da_lista():
    servico, session = _servico(
        {1: [_produto(10, FONE_ML, "219.90"), _produto(11, "Headset HyperX Cloud Stinger 2", "149"),
             _produto(12, "Headset Redragon Zeus X H510", "199")]},
        recentes=[_recente(FONE_SHOPEE, "199.90")],
    )

    ids = [c[2] for c in servico._selecionar_candidatos(session, 1)]

    assert ids == [11, 12]  # 10 foi barrado e o 12 ocupou a vaga


def test_mesmo_produto_nas_duas_lojas_no_mesmo_ciclo_fica_o_mais_barato():
    servico, session = _servico({
        1: [_produto(20, FONE_SHOPEE, "209.90")],          # Shopee
        2: [_produto(30, FONE_ML, "189.90")],              # Mercado Livre
    })

    ids = [c[2] for c in servico._selecionar_candidatos(session, 1)]

    assert ids == [30]


def test_troca_pelo_mais_barato_respeita_o_limite_da_categoria():
    servico, session = _servico(
        {
            1: [_produto(1, FONE_SHOPEE, "209.90")],
            2: [_produto(2, "Mouse Logitech G203", "99"), _produto(3, FONE_ML, "189.90")],
        },
        limite=1,
    )

    selecionados = servico._selecionar_candidatos(session, 1)

    por_categoria = {}
    for categoria_id, _, _ in selecionados:
        por_categoria[categoria_id] = por_categoria.get(categoria_id, 0) + 1
    assert all(qtd <= 1 for qtd in por_categoria.values())


# --- validação no envio (manual e automático) --------------------------------

def test_envio_recusa_produto_igual_mais_caro_com_mensagem_clara():
    publicacao_repository = Mock()
    publicacao_repository.listar_publicadas_recentes.return_value = [_recente(FONE_SHOPEE, "199.90")]
    servico = PublicacaoService(
        produto_repository=Mock(), categoria_repository=Mock(),
        publicacao_repository=publicacao_repository,
        configuracao_repository=Mock(), telegram_publisher=Mock(),
    )

    with pytest.raises(ValueError, match=r"R\$ 199,90.*Shopee.*preço menor"):
        servico._validar_republicacao(Mock(), _produto(2, FONE_ML, "219.90"), 1, Mock(__sub__=Mock()))
