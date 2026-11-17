import pytest


def test_get_retorna_configuracao_global(client):
    resposta = client.get("/configuracoes-sistema")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["limite_produtos_por_categoria"] >= 1
    assert corpo["intervalo_coleta_minutos"] > 0


def test_patch_limite_preserva_intervalo(client):
    antes = client.get("/configuracoes-sistema").json()

    resposta = client.patch(
        "/configuracoes-sistema",
        json={"limite_produtos_por_categoria": 5},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["limite_produtos_por_categoria"] == 5
    assert corpo["intervalo_coleta_minutos"] == antes["intervalo_coleta_minutos"]
    assert client.get("/configuracoes-sistema").json()[
        "limite_produtos_por_categoria"
    ] == 5


def test_patch_intervalo_preserva_limite(client):
    antes = client.get("/configuracoes-sistema").json()

    resposta = client.patch(
        "/configuracoes-sistema",
        json={"intervalo_coleta_minutos": 45},
    )

    assert resposta.status_code == 200
    assert resposta.json()["intervalo_coleta_minutos"] == 45
    assert (
        resposta.json()["limite_produtos_por_categoria"]
        == antes["limite_produtos_por_categoria"]
    )


def test_patch_ambos_os_campos(client):
    resposta = client.patch(
        "/configuracoes-sistema",
        json={"intervalo_coleta_minutos": 15, "limite_produtos_por_categoria": 3},
    )

    assert resposta.status_code == 200
    assert resposta.json()["intervalo_coleta_minutos"] == 15
    assert resposta.json()["limite_produtos_por_categoria"] == 3


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"limite_produtos_por_categoria": 0},
        {"limite_produtos_por_categoria": -1},
        {"limite_produtos_por_categoria": None},
        {"intervalo_coleta_minutos": 0},
        {"campo_inexistente": 1},
    ],
)
def test_patch_invalido_retorna_422_e_nao_altera(client, corpo):
    antes = client.get("/configuracoes-sistema").json()

    resposta = client.patch("/configuracoes-sistema", json=corpo)

    assert resposta.status_code == 422
    depois = client.get("/configuracoes-sistema").json()
    assert depois["limite_produtos_por_categoria"] == antes["limite_produtos_por_categoria"]
    assert depois["intervalo_coleta_minutos"] == antes["intervalo_coleta_minutos"]
