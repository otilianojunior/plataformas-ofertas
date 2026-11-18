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
    resposta = client.delete(f"/categorias/{ids['categoria']}/grupos/{X}")
    assert resposta.status_code == 404
    assert "não está associado" in resposta.json()["detail"]


def test_publicar_em_destino_inexistente_retorna_404(client, ids):
    resposta = client.post(f"/publicacoes/produtos/{ids['produto']}/grupos/{X}")
    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Destino de divulgação não encontrado."


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


ROTAS_ESPERADAS = {
    ("POST", "/coletas/mercado-livre"),
    ("POST", "/coletas/shopee"),
    ("GET", "/lojas"),
    ("GET", "/canais-divulgacao"),
    ("GET", "/grupos"),
    ("GET", "/grupos/configuracoes"),
    ("GET", "/grupos/{grupo_id}/configuracao"),
    ("POST", "/grupos/{grupo_id}/configuracao"),
    ("PATCH", "/grupos/{grupo_id}/configuracao"),
    ("GET", "/categorias/{categoria_id}/grupos"),
    ("POST", "/categorias/{categoria_id}/grupos/{grupo_id}"),
    ("POST", "/publicacoes/produtos/{produto_id}/grupos/{grupo_id}"),
}

ROTAS_REMOVIDAS = {
    "/plataformas", "/plataformas-divulgacao", "/destinos-divulgacao",
    "/configuracoes-divulgacao", "/coletas/status",
    "/configuracoes-sistema/coleta-automatica/iniciar",
    "/categorias/{categoria_id}/destino-divulgacao",
}


def test_nomes_das_rotas(client):
    paths = client.get("/openapi.json").json()["paths"]
    existentes = {(m.upper(), p) for p, ops in paths.items() for m in ops}

    assert ROTAS_ESPERADAS <= existentes
    assert not ROTAS_REMOVIDAS & set(paths)
    assert not any(op.get("deprecated") for ops in paths.values() for op in ops.values())


def test_lista_de_configuracoes_nao_conflita_com_id_do_grupo(client):
    assert client.get("/grupos/configuracoes").status_code == 200
    assert client.get("/grupos/999999").status_code == 404


def test_criar_configuracao_em_grupo_inexistente(client):
    assert client.post("/grupos/999999/configuracao", json={}).status_code == 404


def test_criar_categoria_ja_associa_os_grupos(client, db_session):
    loja_id, grupo_id = db_session.execute(
        text(
            "SELECT (SELECT id FROM plataformas LIMIT 1), "
            "(SELECT id FROM destinos_divulgacao LIMIT 1)"
        )
    ).one()
    if grupo_id is None:
        pytest.skip("Nenhum grupo cadastrado.")

    resposta = client.post(
        "/categorias",
        json={
            "plataforma_id": loja_id,
            "id_categoria_plataforma": "TESTE-123",
            "nome_categoria": "Categoria de teste",
            "desconto_minimo_percentual": 20,
            "grupos_ids": [grupo_id, grupo_id],
        },
    )

    assert resposta.status_code == 201
    grupos = client.get(f"/categorias/{resposta.json()['id']}/grupos").json()
    assert [g["id"] for g in grupos] == [grupo_id]


def test_criar_categoria_com_grupo_inexistente(client, db_session):
    loja_id = db_session.execute(text("SELECT id FROM plataformas LIMIT 1")).scalar()

    resposta = client.post(
        "/categorias",
        json={
            "plataforma_id": loja_id,
            "id_categoria_plataforma": "TESTE-456",
            "nome_categoria": "Categoria de teste",
            "desconto_minimo_percentual": 20,
            "grupos_ids": [X],
        },
    )

    assert resposta.status_code == 404


def test_painel_e_servido_com_rotas_do_react(client):
    from ofertas.main import PAINEL_DIST

    if not (PAINEL_DIST / "index.html").exists():
        import pytest
        pytest.skip("Painel não compilado.")

    for caminho in ("/painel", "/painel/", "/painel/produtos", "/painel/categorias"):
        resposta = client.get(caminho)
        assert resposta.status_code == 200 and "<div id=\"raiz\">" in resposta.text, caminho

    # não deixa sair da pasta do painel
    resposta = client.get("/painel/..%2F..%2F.env")
    assert "DATABASE_URL" not in resposta.text


def test_excluir_categoria_apaga_produtos_publicacoes_e_historico(client, db_session):
    from sqlalchemy import text

    plataforma_id = db_session.execute(text("SELECT id FROM plataformas ORDER BY id LIMIT 1")).scalar_one()
    categoria_id = db_session.execute(
        text(
            "INSERT INTO plataforma_categoria (plataforma_id, id_categoria_plataforma, nome_categoria, "
            "desconto_minimo_percentual, status_categoria) "
            "VALUES (:p, 'TESTE-EXCLUSAO', 'Categoria de teste', 20, true) RETURNING id"
        ),
        {"p": plataforma_id},
    ).scalar_one()
    produto_ids = [
        db_session.execute(
            text(
                "INSERT INTO produtos (plataforma_id, categoria_id, id_item_plataforma, titulo, url, preco_atual) "
                "VALUES (:p, :c, :i, 'Produto de teste', 'https://exemplo.com', 100) RETURNING id"
            ),
            {"p": plataforma_id, "c": categoria_id, "i": f"TESTE-EXCLUSAO-{n}"},
        ).scalar_one()
        for n in (1, 2)
    ]
    db_session.execute(
        text("INSERT INTO historico_precos (produto_id, preco, origem) VALUES (:id, 100, 'coleta')"),
        {"id": produto_ids[0]},
    )
    db_session.flush()

    resposta = client.delete(f"/categorias/{categoria_id}")
    assert resposta.status_code == 200
    assert resposta.json() == {"categoria_id": categoria_id, "produtos_excluidos": 2}

    restantes = db_session.execute(
        text("SELECT count(*) FROM produtos WHERE id = ANY(:ids)"), {"ids": produto_ids}
    ).scalar_one()
    historico = db_session.execute(
        text("SELECT count(*) FROM historico_precos WHERE produto_id = ANY(:ids)"), {"ids": produto_ids}
    ).scalar_one()
    assert (restantes, historico) == (0, 0)
    assert client.get(f"/categorias/{categoria_id}").status_code == 404
    assert client.delete(f"/categorias/{categoria_id}").status_code == 404
