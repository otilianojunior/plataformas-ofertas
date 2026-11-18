from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ofertas.models.usuario import Usuario


class UsuarioRepository:
    """Acesso aos usuários do painel."""

    def buscar(self, session: Session, usuario_id: int) -> Usuario | None:
        return session.get(Usuario, usuario_id)

    def buscar_por_login(self, session: Session, login: str) -> Usuario | None:
        return session.scalar(
            select(Usuario).where(func.lower(Usuario.login) == login.lower())
        )

    def listar(self, session: Session) -> list[Usuario]:
        return list(
            session.scalars(
                select(Usuario).order_by(Usuario.ativo.desc(), Usuario.nome)
            ).all()
        )

    def contar_admins_ativos(self, session: Session) -> int:
        return session.scalar(
            select(func.count(Usuario.id)).where(
                Usuario.perfil == "admin",
                Usuario.ativo.is_(True),
            )
        ) or 0

    def criar(self, session: Session, usuario: Usuario) -> Usuario:
        session.add(usuario)
        session.flush()
        session.refresh(usuario)
        return usuario

    def salvar(self, session: Session, usuario: Usuario) -> Usuario:
        session.flush()
        session.refresh(usuario)
        return usuario
