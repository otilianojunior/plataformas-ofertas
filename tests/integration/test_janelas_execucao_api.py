import pytest


pytestmark = pytest.mark.usefixtures("sem_janelas")


def _criar(client, inicio, fim, ativa=True):
    return client.post(
        "/janelas-execucao",
        json={"hora_inicio": inicio, "hora_fim": fim, "ativa": ativa},
    )


def test_cadastro_e_horarios_retornados(client):
    resposta = _criar(client, "08:00", "12:00")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["hora_inicio"] == "08:00:00"
    assert corpo["hora_fim"] == "12:00:00"
    assert corpo["ativa"] is True

    consulta = client.get(f"/janelas-execucao/{corpo['id']}")
    assert consulta.status_code == 200
    assert consulta.json() == corpo


def test_listagem_ordenada_por_inicio(client):
    _criar(client, "18:00", "22:00")
    _criar(client, "08:00", "12:00")

    inicios = [j["hora_inicio"] for j in client.get("/janelas-execucao").json()]
    assert inicios == ["08:00:00", "18:00:00"]


@pytest.mark.parametrize(
    ("inicio", "fim"),
    [
        ("11:00", "13:00"),  # começa dentro
        ("07:00", "09:00"),  # termina dentro
        ("09:00", "10:00"),  # contida
        ("07:00", "13:00"),  # contém
        ("08:00", "12:00"),  # idêntica
    ],
)
def test_sobreposicao_retorna_409(client, inicio, fim):
    assert _criar(client, "08:00", "12:00").status_code == 201

    resposta = _criar(client, inicio, fim)

    assert resposta.status_code == 409
    assert "sobrepõe" in resposta.json()["detail"]


def test_horarios_consecutivos_sao_permitidos(client):
    assert _criar(client, "08:00", "12:00").status_code == 201
    assert _criar(client, "12:00", "14:00").status_code == 201
    assert _criar(client, "06:00", "08:00").status_code == 201


def test_janela_inativa_pode_se_sobrepor_mas_nao_ser_ativada(client):
    assert _criar(client, "08:00", "12:00").status_code == 201
    inativa = _criar(client, "10:00", "14:00", ativa=False)
    assert inativa.status_code == 201

    resposta = client.patch(
        f"/janelas-execucao/{inativa.json()['id']}",
        json={"ativa": True},
    )
    assert resposta.status_code == 409


@pytest.mark.parametrize(
    "corpo",
    [
        {"hora_inicio": "12:00", "hora_fim": "08:00"},
        {"hora_inicio": "08:00", "hora_fim": "08:00"},
        {"hora_inicio": "22:00", "hora_fim": "02:00"},  # atravessa meia-noite
        {"hora_inicio": "08:00-03:00", "hora_fim": "12:00"},  # com fuso
        {"hora_inicio": "25:00", "hora_fim": "26:00"},
    ],
)
def test_cadastro_invalido_retorna_422(client, corpo):
    assert client.post("/janelas-execucao", json=corpo).status_code == 422


def test_janela_ate_o_fim_do_dia(client):
    resposta = _criar(client, "20:00", "23:59:59")
    assert resposta.status_code == 201


def test_alteracao(client):
    janela = _criar(client, "08:00", "12:00").json()

    resposta = client.patch(
        f"/janelas-execucao/{janela['id']}",
        json={"hora_fim": "13:30"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["hora_inicio"] == "08:00:00"
    assert resposta.json()["hora_fim"] == "13:30:00"


def test_alteracao_para_sobreposicao_retorna_409(client):
    _criar(client, "08:00", "12:00")
    outra = _criar(client, "14:00", "16:00").json()

    resposta = client.patch(
        f"/janelas-execucao/{outra['id']}",
        json={"hora_inicio": "11:00"},
    )

    assert resposta.status_code == 409
    assert client.get(f"/janelas-execucao/{outra['id']}").json()[
        "hora_inicio"
    ] == "14:00:00"


def test_alteracao_invalida(client):
    janela = _criar(client, "08:00", "12:00").json()
    url = f"/janelas-execucao/{janela['id']}"

    # fim antes do início atual: chega ao serviço e vira 409
    assert client.patch(url, json={"hora_fim": "07:00"}).status_code == 409
    assert client.patch(url, json={}).status_code == 422
    assert client.patch(url, json={"ativa": None}).status_code == 422


def test_exclusao(client):
    janela = _criar(client, "08:00", "12:00").json()
    url = f"/janelas-execucao/{janela['id']}"

    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404
    assert client.patch(url, json={"ativa": False}).status_code == 404


def test_exclusao_libera_o_horario(client):
    janela = _criar(client, "08:00", "12:00").json()
    client.delete(f"/janelas-execucao/{janela['id']}")

    assert _criar(client, "09:00", "11:00").status_code == 201
