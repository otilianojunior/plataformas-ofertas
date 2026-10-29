from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao


class PlataformaDivulgacaoRepository:
    """Centraliza o acesso aos dados das plataformas de divulgação."""

    def listar(self, session: Session) -> list[PlataformaDivulgacao]:
        consulta = select(PlataformaDivulgacao).order_by(
            PlataformaDivulgacao.nome
        )
        return list(session.scalars(consulta).all())

    def buscar_por_id(
        self,
        session: Session,
        plataforma_id: int,
    ) -> PlataformaDivulgacao | None:
        return session.get(PlataformaDivulgacao, plataforma_id)

    def buscar_por_codigo(
        self,
        session: Session,
        codigo: str,
    ) -> PlataformaDivulgacao | None:
        consulta = select(PlataformaDivulgacao).where(
            PlataformaDivulgacao.codigo == codigo
        )
        return session.scalars(consulta).one_or_none()

    def criar(
        self,
        session: Session,
        *,
        codigo: str,
        nome: str,
        status_plataforma: bool = True,
    ) -> PlataformaDivulgacao:
        plataforma = PlataformaDivulgacao(
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
        plataforma: PlataformaDivulgacao,
        ativo: bool,
    ) -> PlataformaDivulgacao:
        plataforma.status_plataforma = ativo
        session.flush()
        return plataforma
