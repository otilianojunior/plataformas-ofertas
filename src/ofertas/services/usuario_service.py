from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ofertas.core.autenticacao import (
    HASH_FICTICIO,
    gerar_hash_senha,
    gerar_token_sessao,
    ler_token_sessao,
    token_confere_com_senha,
    verificar_senha,
)
from ofertas.models.usuario import PERFIS_USUARIO, Usuario
from ofertas.repositories.usuario_repository import UsuarioRepository


class CredenciaisInvalidasError(Exception):
    """Login ou senha incorretos, usuário inativo ou sessão inválida."""


class UsuarioService:
    """Login no painel e cadastro de usuários."""

    def __init__(self, repository: UsuarioRepository | None = None) -> None:
        self.repository = repository or UsuarioRepository()

    def autenticar(
        self,
        session: Session,
        login: str,
        senha: str,
    ) -> tuple[Usuario, str]:
        usuario = self.repository.buscar_por_login(session, login.strip())

        # Verifica a senha mesmo sem usuário: o tempo de resposta não
        # revela se o login existe.
        senha_ok = verificar_senha(
            senha,
            usuario.senha_hash if usuario else HASH_FICTICIO,
        )

        if usuario is None or not senha_ok or not usuario.ativo:
            raise CredenciaisInvalidasError("Login ou senha inválidos.")

        usuario.ultimo_login_em = datetime.now(timezone.utc)
        self.repository.salvar(session, usuario)

        return usuario, gerar_token_sessao(usuario.id, usuario.senha_hash)

    def usuario_do_token(self, session: Session, token: str) -> Usuario:
        dados = ler_token_sessao(token)

        if dados is None:
            raise CredenciaisInvalidasError("Sessão expirada ou inválida.")

        usuario_id, carimbo = dados
        usuario = self.repository.buscar(session, usuario_id)

        if (
            usuario is None
            or not usuario.ativo
            or not token_confere_com_senha(carimbo, usuario.senha_hash)
        ):
            raise CredenciaisInvalidasError("Sessão expirada ou inválida.")

        return usuario

    def criar(
        self,
        session: Session,
        *,
        login: str,
        nome: str,
        senha: str,
        perfil: str = "operador",
    ) -> Usuario:
        login = login.strip()

        if not login or not nome.strip():
            raise ValueError("Login e nome são obrigatórios.")

        if perfil not in PERFIS_USUARIO:
            raise ValueError(f"Perfil inválido: {perfil}.")

        if self.repository.buscar_por_login(session, login) is not None:
            raise ValueError(f"Já existe um usuário com o login '{login}'.")

        return self.repository.criar(
            session,
            Usuario(
                login=login,
                nome=nome.strip(),
                senha_hash=gerar_hash_senha(senha),
                perfil=perfil,
            ),
        )

    def alterar_senha(self, session: Session, login: str, senha: str) -> Usuario:
        usuario = self.repository.buscar_por_login(session, login.strip())

        if usuario is None:
            raise LookupError(f"Usuário '{login}' não encontrado.")

        usuario.senha_hash = gerar_hash_senha(senha)
        usuario.ativo = True
        return self.repository.salvar(session, usuario)
