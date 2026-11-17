import json
from unittest.mock import Mock

import httpx
import pytest

from ofertas.collectors import shopee_client as modulo
from ofertas.collectors.shopee_client import ShopeeAPIError, ShopeeClient


RESPOSTA_OK = {
    "data": {
        "productOfferV2": {
            "nodes": [{"itemId": 1, "productName": "Teclado"}],
            "pageInfo": {"page": 1, "limit": 10, "hasNextPage": False},
        }
    }
}
ERRO_10000 = {"errors": [{"message": "error [10000]: System Error"}]}


@pytest.fixture
def cliente(monkeypatch):
    credenciais = Mock()
    credenciais.buscar_valor_ativo.side_effect = ["app", "segredo"] * 10
    monkeypatch.setattr(modulo.time, "sleep", lambda _s: None)
    return ShopeeClient(credencial_service=credenciais, timestamp_provider=lambda: 1)


def _servidor(monkeypatch, respostas):
    """Faz o httpx.Client do módulo responder com a sequência informada."""
    chamadas = []
    fila = list(respostas)

    def handler(request):
        chamadas.append(json.loads(request.content))
        status, corpo = fila.pop(0)
        return httpx.Response(status, json=corpo)

    cliente_real = httpx.Client
    monkeypatch.setattr(
        modulo.httpx,
        "Client",
        lambda **kw: cliente_real(transport=httpx.MockTransport(handler), **kw),
    )
    return chamadas


def test_erro_10000_e_retentado_ate_obter_sucesso(cliente, monkeypatch):
    chamadas = _servidor(
        monkeypatch,
        [(200, ERRO_10000), (200, ERRO_10000), (200, RESPOSTA_OK)],
    )

    resultado = cliente.buscar_ofertas_categoria(Mock(), 100, 2)

    assert len(chamadas) == 3
    assert resultado["nodes"][0]["itemId"] == 1


def test_erro_10000_persistente_vira_shopee_api_error(cliente, monkeypatch):
    chamadas = _servidor(monkeypatch, [(200, ERRO_10000)] * 4)

    with pytest.raises(ShopeeAPIError, match=r"\[10000\]"):
        cliente.buscar_ofertas_categoria(Mock(), 100, 2)

    assert len(chamadas) == ShopeeClient.MAX_RETRIES + 1


def test_http_503_e_retentado(cliente, monkeypatch):
    chamadas = _servidor(monkeypatch, [(503, {}), (200, RESPOSTA_OK)])

    cliente.buscar_ofertas_categoria(Mock(), 100, 2)

    assert len(chamadas) == 2


def test_erro_graphql_nao_temporario_nao_e_retentado(cliente, monkeypatch):
    chamadas = _servidor(
        monkeypatch,
        [(200, {"errors": [{"message": "error [10020]: Invalid Signature"}]})],
    )

    with pytest.raises(ShopeeAPIError, match="10020"):
        cliente.buscar_ofertas_categoria(Mock(), 100, 2)

    assert len(chamadas) == 1
