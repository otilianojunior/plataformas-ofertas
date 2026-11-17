"""Categorias coletadas por termo de busca (ex.: headsets de marca)."""

from unittest.mock import Mock

import httpx

from ofertas.collectors.mercado_livre_collector import MercadoLivreCollector
from ofertas.collectors.shopee_collector import ShopeeCollector


def _categoria(id_externo, termo):
    return Mock(
        id=1, plataforma_id=1, nome_categoria="Headsets Razer",
        id_categoria_plataforma=id_externo, status_categoria=True, termo_busca=termo,
    )


def test_shopee_envia_o_termo_junto_com_a_categoria():
    client = Mock()
    client.buscar_ofertas_categoria.return_value = {"nodes": [], "pageInfo": {"hasNextPage": False}}
    coletor = ShopeeCollector(client=client, produto_service=Mock(), sort_types=(2,))

    coletor.coletar_categoria(Mock(), _categoria("100578", "headset razer"))

    args, kwargs = client.buscar_ofertas_categoria.call_args
    assert args[1] == 100578
    assert kwargs["termo_busca"] == "headset razer"


def _coletor_ml(client):
    coletor = MercadoLivreCollector.__new__(MercadoLivreCollector)
    coletor.client = client
    coletor.produto_service = Mock()
    coletor._preparar_produto = Mock(return_value={"x": 1})
    return coletor


def test_mercado_livre_usa_busca_de_catalogo_e_nao_os_destaques():
    client = Mock()
    client.buscar_produtos_catalogo.return_value = {"results": [{"id": "MLB1"}, {"id": "MLB2"}]}
    client.buscar_detalhes_produto.return_value = {}
    client.buscar_anuncios_produto.return_value = {"results": [{"id": "MLB-ITEM"}]}
    coletor = _coletor_ml(client)

    resultado = coletor.coletar_categoria(Mock(), _categoria("MLB1664", "headset razer"))

    client.buscar_destaques.assert_not_called()
    assert client.buscar_produtos_catalogo.call_args.args[2] == "headset razer"
    assert resultado["processadas"] == 2


def test_produto_de_catalogo_sem_anuncio_e_descartado_sem_aviso():
    erro_404 = httpx.HTTPStatusError(
        "404", request=Mock(), response=Mock(status_code=404, text="not found")
    )
    client = Mock()
    client.buscar_produtos_catalogo.return_value = {"results": [{"id": "MLB1"}]}
    client.buscar_detalhes_produto.return_value = {}
    client.buscar_anuncios_produto.side_effect = erro_404
    coletor = _coletor_ml(client)

    resultado = coletor.coletar_categoria(Mock(), _categoria("MLB1664", "fone jbl"))

    assert resultado["ignoradas"] == 1
    assert resultado["erros"] == []


def test_categoria_sem_termo_continua_usando_os_destaques():
    client = Mock()
    client.buscar_destaques.return_value = {"content": []}
    coletor = _coletor_ml(client)

    coletor.coletar_categoria(Mock(), _categoria("MLB1664", None))

    client.buscar_destaques.assert_called_once()
    client.buscar_produtos_catalogo.assert_not_called()
