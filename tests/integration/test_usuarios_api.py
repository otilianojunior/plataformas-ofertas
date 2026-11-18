from sqlalchemy import text

from ofertas.api.autenticacao import usuario_atual
from ofertas.main import app
from ofertas.models.usuario import Usuario
from ofertas.services.usuario_service import UsuarioService


SENHA = "senha-de-teste-123"


def _criar(db_session, login, perfil="operador"):
    usuario = UsuarioService().criar(db_session, login=login, nome=login.title(), senha=SENHA, perfil=perfil)
    db_session.commit()  # vira savepoint: sobrevive ao rollback de um 409 da rota
    return usuario


def _logar(client, login, senha=SENHA):
    resposta = client.post("/auth/login", json={"login": login, "senha": senha})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def test_admin_cria_lista_e_edita_usuario(client):
    resposta = client.post("/usuarios", json={"login": "maria.op", "nome": "Maria", "senha": SENHA})
    assert resposta.status_code == 201
    usuario = resposta.json()
    assert usuario["perfil"] == "operador" and usuario["ativo"]

    assert client.post("/usuarios", json={"login": "MARIA.OP", "nome": "Outra", "senha": SENHA}).status_code == 409
    assert client.post("/usuarios", json={"login": "x y", "nome": "Inválido", "senha": SENHA}).status_code == 422
    assert client.post("/usuarios", json={"login": "curta", "nome": "Curta", "senha": "123"}).status_code == 422

    assert any(u["login"] == "maria.op" for u in client.get("/usuarios").json())

    resposta = client.patch(f"/usuarios/{usuario['id']}", json={"nome": "Maria Silva", "ativo": False})
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Maria Silva" and not resposta.json()["ativo"]

    assert client.patch("/usuarios/999999", json={"ativo": False}).status_code == 404
    assert client.patch(f"/usuarios/{usuario['id']}", json={}).status_code == 422


def test_operador_nao_gerencia_usuarios(client_sem_login, db_session):
    _criar(db_session, "operador.teste")
    cabecalho = _logar(client_sem_login, "operador.teste")

    assert client_sem_login.get("/usuarios", headers=cabecalho).status_code == 403
    assert client_sem_login.get("/automacoes/status", headers=cabecalho).status_code == 200


def test_sempre_sobra_um_admin_ativo(client_sem_login, db_session):
    db_session.execute(text("UPDATE usuarios SET ativo = false"))  # desfeito ao final
    admin = _criar(db_session, "admin.unico", perfil="admin")
    outro = _criar(db_session, "outro.admin", perfil="admin")

    # Executado pelo próprio admin: não pode se desativar nem se rebaixar.
    app.dependency_overrides[usuario_atual] = lambda: admin
    try:
        for dados in ({"ativo": False}, {"perfil": "operador"}):
            assert client_sem_login.patch(f"/usuarios/{admin.id}", json=dados).status_code == 409

        # Pode desativar o outro, mas aí o último admin fica protegido.
        assert client_sem_login.patch(f"/usuarios/{outro.id}", json={"ativo": False}).status_code == 200
        app.dependency_overrides[usuario_atual] = lambda: Usuario(id=0, perfil="admin", ativo=True)
        resposta = client_sem_login.patch(f"/usuarios/{admin.id}", json={"perfil": "operador"})
        assert resposta.status_code == 409
        assert resposta.json()["detail"] == "É preciso manter ao menos um admin ativo."
    finally:
        app.dependency_overrides.pop(usuario_atual, None)


def test_redefinir_senha_derruba_sessao_do_usuario(client, client_sem_login, db_session):
    usuario = _criar(db_session, "esqueceu.senha")
    cabecalho = _logar(client_sem_login, "esqueceu.senha")

    assert client.put(f"/usuarios/{usuario.id}/senha", json={"senha": "nova-senha-789"}).status_code == 200
    app.dependency_overrides.pop(usuario_atual, None)  # volta a validar o token de verdade

    assert client_sem_login.get("/auth/eu", headers=cabecalho).status_code == 401
    _logar(client_sem_login, "esqueceu.senha", "nova-senha-789")


def test_trocar_propria_senha(client_sem_login, db_session):
    _criar(db_session, "troca.senha")
    antigo = _logar(client_sem_login, "troca.senha")

    resposta = client_sem_login.put(
        "/auth/senha", headers=antigo, json={"senha_atual": "errada-000", "senha_nova": "nova-senha-789"}
    )
    assert resposta.status_code == 409

    resposta = client_sem_login.put(
        "/auth/senha", headers=antigo, json={"senha_atual": SENHA, "senha_nova": "nova-senha-789"}
    )
    assert resposta.status_code == 200
    novo = {"Authorization": f"Bearer {resposta.json()['access_token']}"}

    assert client_sem_login.get("/auth/eu", headers=antigo).status_code == 401
    assert client_sem_login.get("/auth/eu", headers=novo).status_code == 200
