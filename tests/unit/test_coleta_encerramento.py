"""Coletores param entre páginas/itens quando a API está encerrando."""

import threading
from unittest.mock import Mock

from ofertas.collectors.mercado_livre_collector import MercadoLivreCollector
from ofertas.collectors.shopee_collector import ShopeeCollector


def _categoria():
    return Mock(
        id=1, plataforma_id=2, nome_categoria="Coolers",
        id_categoria_plataforma="101949", status_categoria=True, termo_busca=None,
    )


def _pagina(item_id):
    return {
        "nodes": [{"itemId": item_id, "productName": f"Produto {item_id}",
                   "price": "10.00", "productLink": "https://shopee.com.br/p"}],
        "pageInfo": {"hasNextPage": True},
    }


def test_shopee_para_na_proxima_pagina_e_salva_o_que_ja_veio():
    encerrando = threading.Event()
    client = Mock()

    def buscar(*_args, page, **_kwargs):
        encerrando.set()  # a API começa a parar durante a 1ª página
        return _pagina(page)

    client.buscar_ofertas_categoria.side_effect = buscar
    produto_service = Mock()
    coletor = ShopeeCollector(client=client, produto_service=produto_service)

    resultado = coletor.coletar_categoria(Mock(), _categoria(), encerrando=encerrando)

    assert client.buscar_ofertas_categoria.call_count == 1  # não foi para a pág. 2 nem outras ordenações
    assert resultado["processadas"] == 1
    produto_service.registrar_coleta.assert_called_once()
    assert any("encerramento da API" in e for e in resultado["erros"])


def test_shopee_interrompida_antes_de_consultar_nao_vira_falha():
    encerrando = threading.Event()
    encerrando.set()
    client = Mock()
    coletor = ShopeeCollector(client=client, produto_service=Mock())

    resultado = coletor.coletar_categoria(Mock(), _categoria(), encerrando=encerrando)

    client.buscar_ofertas_categoria.assert_not_called()
    assert resultado["processadas"] == 0


def test_mercado_livre_para_entre_destaques():
    encerrando = threading.Event()
    client = Mock()
    client.buscar_destaques.return_value = {
        "content": [{"id": f"MLB{i}", "type": "ITEM"} for i in range(5)]
    }

    def buscar_item(*_args):
        encerrando.set()
        return {}

    client.buscar_item.side_effect = buscar_item
    coletor = MercadoLivreCollector.__new__(MercadoLivreCollector)
    coletor.client = client
    coletor.produto_service = Mock()
    coletor._preparar_item = Mock(return_value=None)

    resultado = coletor.coletar_categoria(Mock(), _categoria(), encerrando=encerrando)

    assert client.buscar_item.call_count == 1
    assert any("encerramento da API" in e for e in resultado["erros"])


def test_geracao_de_afiliados_shopee_para_e_deixa_o_resto_pendente():
    from ofertas.affiliates.shopee_affiliate_service import ShopeeAffiliateService
    from ofertas.models.plataforma import Plataforma

    encerrando = threading.Event()
    produtos = [
        (Mock(id=i, url="https://shopee.com.br/p", status_link_afiliado="pendente",
              percentual_desconto=30, disponivel=True, status_monitoramento="ativo"),
         Mock(etiqueta_afiliado="caramelotech", nome_categoria="Coolers",
              desconto_minimo_percentual=20))
        for i in range(3)
    ]
    repositorio = Mock()
    repositorio.listar_pendentes_para_geracao_afiliado.return_value = produtos
    client = Mock()

    def gerar(*_args, **_kwargs):
        encerrando.set()
        return "https://s.shopee.com.br/abc"

    client.gerar_link_afiliado.side_effect = gerar
    session = Mock()
    session.get.return_value = Plataforma(id=2, codigo="shopee")

    servico = ShopeeAffiliateService(repository=repositorio, client=client)
    servico.gerar_pendentes(session, 2, encerrando=encerrando)

    assert client.gerar_link_afiliado.call_count == 1
    assert [p.status_link_afiliado for p, _ in produtos[1:]] == ["pendente", "pendente"]
