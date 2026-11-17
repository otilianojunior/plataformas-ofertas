"""Regressões dos códigos de erro das rotas."""

import pytest
from sqlalchemy import text

X = 999999


@pytest.fixture
def ids(db_session):
    consultas = {
        "categoria": "SELECT id FROM plataforma_categoria LIMIT 1",
        "produto": "SELECT id FROM produtos LIMIT 1",
        "credencial": (
            "SELECT id FROM credenciais_plataforma "
            "WHERE status_credencial = 'ativa' LIMIT 1"
        ),
    }
    valores = {k: db_session.execute(text(q)).scalar() for k, q in consultas.items()}
    if None in valores.values():
        pytest.skip("Banco sem dados de referência.")
    return valores


def test_credencial_ativa_duplicada_retorna_409(client, db_session, ids):
    plataforma_id, tipo = db_session.execute(
        text("SELECT plataforma_id, tipo_credencial FROM credenciais_plataforma WHERE id = :i"),
        {"i": ids["credencial"]},
    ).one()

    resposta = client.post(
        "/credenciais-plataforma",
        json={"plataforma_id": plataforma_id, "tipo_credencial": tipo, "valor": "novo"},
    )

    assert resposta.status_code == 409
    assert "Já existe uma credencial ativa" in resposta.json()["detail"]


def test_troca_de_credencial_inativando_a_atual(client, db_session, ids):
    plataforma_id, tipo = db_session.execute(
        text("SELECT plataforma_id, tipo_credencial FROM credenciais_plataforma WHERE id = :i"),
        {"i": ids["credencial"]},
    ).one()

    assert client.patch(
        f"/credenciais-plataforma/{ids['credencial']}/status",
        json={"status_credencial": "inativa"},
    ).status_code == 200
    nova = client.post(
        "/credenciais-plataforma",
        json={"plataforma_id": plataforma_id, "tipo_credencial": tipo, "valor": "novo"},
    )
    assert nova.status_code == 201

    # reativar a antiga agora conflita com a nova
    assert client.patch(
        f"/credenciais-plataforma/{ids['credencial']}/status",
        json={"status_credencial": "ativa"},
    ).status_code == 409


def test_desassociar_grupo_nao_associado_retorna_404(client, ids):
    resposta = client.delete(f"/categorias/{ids['categoria']}/destinos/{X}")
    assert resposta.status_code == 404


def test_publicar_em_destino_inexistente_retorna_404(client, ids):
    resposta = client.post(f"/publicacoes/produtos/{ids['produto']}/destinos/{X}")
    assert resposta.status_code == 404


def test_categorias_sem_barra_final(client):
    assert client.get("/categorias", follow_redirects=False).status_code == 200


def test_todas_as_rotas_documentam_os_erros_que_devolvem(client):
    """Toda rota com parâmetro de ID/código documenta o 404."""
    paths = client.get("/openapi.json").json()["paths"]
    sem_404 = [
        f"{metodo.upper()} {path}"
        for path, ops in paths.items()
        if "{" in path and "automacao}" not in path
        for metodo, op in ops.items()
        if "404" not in op["responses"]
    ]
    assert sem_404 == []
