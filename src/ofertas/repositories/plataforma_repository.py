from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.plataforma import Plataforma


class PlataformaRepository:
    """Centraliza o acesso aos dados das plataformas."""

    def listar(self, session: Session) -> list[Plataforma]:
        """Retorna todas as plataformas cadastradas."""
        consulta = select(Plataforma).order_by(Plataforma.nome)
        return list(session.scalars(consulta).all())

    def buscar_por_codigo(
        self,
        session: Session,
        codigo: str,
    ) -> Plataforma | None:
        """Busca uma plataforma pelo código único."""
        consulta = select(Plataforma).where(
            Plataforma.codigo == codigo
        )
        return session.scalars(consulta).one_or_none()

    def criar(
        self,
        session: Session,
        *,
        codigo: str,
        nome: str,
        status_plataforma: bool = True,
    ) -> Plataforma:
        """Adiciona uma plataforma à sessão atual."""
        plataforma = Plataforma(
            codigo=codigo,
            nome=nome,
            status_plataforma=status_plataforma,
        )
        session.add(plataforma)
        session.flush()
        return plataforma

    def atualizar_status(
        self,
        session: Session,
        plataforma: Plataforma,
        ativo: bool,
    ) -> Plataforma:
        """Atualiza o status de ativação de uma plataforma."""
        plataforma.status_plataforma = ativo
        session.flush()
        return plataforma
