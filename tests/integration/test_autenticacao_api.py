from ofertas.core.autenticacao import gerar_token_sessao
from ofertas.services.usuario_service import UsuarioService


SENHA = "senha-de-teste-123"


def _criar_usuario(db_session, ativo=True):
    usuario = UsuarioService().criar(
        db_session, login="Admin.Teste", nome="Admin", senha=SENHA, perfil="admin"
    )
    usuario.ativo = ativo
    db_session.flush()
    return usuario


def test_rotas_exigem_login(client_sem_login):
    resposta = client_sem_login.get("/automacoes/status")
    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"

    resposta = client_sem_login.get(
        "/automacoes/status", headers={"Authorization": "Bearer invalido"}
    )
    assert resposta.status_code == 401


def test_rotas_abertas_continuam_sem_login(client_sem_login):
    assert client_sem_login.get("/health").status_code == 200
    assert client_sem_login.get("/", follow_redirects=False).headers["location"] == "/painel/"


def test_login_devolve_token_que_libera_a_api(client_sem_login, db_session):
    _criar_usuario(db_session)

    resposta = client_sem_login.post("/auth/login", json={"login": "admin.teste", "senha": SENHA})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["usuario"]["perfil"] == "admin"
    assert "senha_hash" not in corpo["usuario"]

    cabecalho = {"Authorization": f"Bearer {corpo['access_token']}"}
    assert client_sem_login.get("/auth/eu", headers=cabecalho).json()["login"] == "Admin.Teste"
    assert client_sem_login.get("/automacoes/status", headers=cabecalho).status_code == 200


def test_login_recusa_senha_errada_login_inexistente_e_inativo(client_sem_login, db_session):
    _criar_usuario(db_session, ativo=False)

    for login, senha in (("admin.teste", "errada-123"), ("ninguem", SENHA), ("admin.teste", SENHA)):
        resposta = client_sem_login.post("/auth/login", json={"login": login, "senha": senha})
        assert resposta.status_code == 401
        assert resposta.json()["detail"] == "Login ou senha inválidos."


def test_trocar_senha_derruba_sessoes_abertas(client_sem_login, db_session):
    usuario = _criar_usuario(db_session)
    token = gerar_token_sessao(usuario.id, usuario.senha_hash)
    cabecalho = {"Authorization": f"Bearer {token}"}
    assert client_sem_login.get("/auth/eu", headers=cabecalho).status_code == 200

    UsuarioService().alterar_senha(db_session, "admin.teste", "outra-senha-456")
    assert client_sem_login.get("/auth/eu", headers=cabecalho).status_code == 401
