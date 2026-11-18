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

    def listar(self, session: Session) -> list[Usuario]:
        return self.repository.listar(session)

    def buscar(self, session: Session, usuario_id: int) -> Usuario:
        usuario = self.repository.buscar(session, usuario_id)

        if usuario is None:
            raise LookupError(f"Usuário de ID '{usuario_id}' não encontrado.")

        return usuario

    def atualizar(
        self,
        session: Session,
        usuario_id: int,
        dados: dict,
        executor: Usuario,
    ) -> Usuario:
        """Altera nome, perfil e/ou situação. Nunca deixa o sistema sem admin."""

        usuario = self.buscar(session, usuario_id)

        perfil = dados.get("perfil", usuario.perfil)
        ativo = dados.get("ativo", usuario.ativo)

        if perfil not in PERFIS_USUARIO:
            raise ValueError(f"Perfil inválido: {perfil}.")

        if usuario.id == executor.id and (not ativo or perfil != "admin"):
            raise ValueError(
                "Você não pode desativar nem tirar o perfil admin da própria conta."
            )

        deixa_de_ser_admin_ativo = (
            usuario.perfil == "admin"
            and usuario.ativo
            and (perfil != "admin" or not ativo)
        )

        if (
            deixa_de_ser_admin_ativo
            and self.repository.contar_admins_ativos(session) <= 1
        ):
            raise ValueError("É preciso manter ao menos um admin ativo.")

        if "nome" in dados:
            nome = dados["nome"].strip()
            if not nome:
                raise ValueError("O nome não pode ficar vazio.")
            usuario.nome = nome

        usuario.perfil = perfil
        usuario.ativo = ativo

        return self.repository.salvar(session, usuario)

    def redefinir_senha(
        self,
        session: Session,
        usuario_id: int,
        senha: str,
    ) -> Usuario:
        """Troca a senha de outro usuário; as sessões dele caem."""

        usuario = self.buscar(session, usuario_id)
        usuario.senha_hash = gerar_hash_senha(senha)
        return self.repository.salvar(session, usuario)

    def trocar_propria_senha(
        self,
        session: Session,
        usuario: Usuario,
        senha_atual: str,
        senha_nova: str,
    ) -> tuple[Usuario, str]:
        if not verificar_senha(senha_atual, usuario.senha_hash):
            raise ValueError("A senha atual não confere.")

        if senha_atual == senha_nova:
            raise ValueError("A nova senha deve ser diferente da atual.")

        usuario.senha_hash = gerar_hash_senha(senha_nova)
        self.repository.salvar(session, usuario)

        # As outras sessões caem; esta recebe um token novo.
        return usuario, gerar_token_sessao(usuario.id, usuario.senha_hash)

    def alterar_senha(self, session: Session, login: str, senha: str) -> Usuario:
        usuario = self.repository.buscar_por_login(session, login.strip())

        if usuario is None:
            raise LookupError(f"Usuário '{login}' não encontrado.")

        usuario.senha_hash = gerar_hash_senha(senha)
        usuario.ativo = True
        return self.repository.salvar(session, usuario)
