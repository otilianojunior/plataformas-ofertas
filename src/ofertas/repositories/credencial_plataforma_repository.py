from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.credencial_plataforma import CredencialPlataforma


class CredencialPlataformaRepository:
    def listar(
        self,
        session: Session,
        plataforma_id: int | None = None,
    ) -> list[CredencialPlataforma]:
        consulta = select(CredencialPlataforma)

        if plataforma_id is not None:
            consulta = consulta.where(
                CredencialPlataforma.plataforma_id == plataforma_id
            )

        consulta = consulta.order_by(CredencialPlataforma.id)

        return list(session.scalars(consulta).all())

    def buscar_por_id(
        self,
        session: Session,
        credencial_id: int,
    ) -> CredencialPlataforma | None:
        return session.get(CredencialPlataforma, credencial_id)

    def criar(
        self,
        session: Session,
        *,
        plataforma_id: int,
        tipo_credencial: str,
        valor_criptografado: str,
        status_credencial: str = "ativa",
    ) -> CredencialPlataforma:
        credencial = CredencialPlataforma(
            plataforma_id=plataforma_id,
            tipo_credencial=tipo_credencial,
            valor_criptografado=valor_criptografado,
            status_credencial=status_credencial,
        )

        session.add(credencial)
        session.flush()

        return credencial

    def atualizar_status(
        self,
        session: Session,
        credencial: CredencialPlataforma,
        status_credencial: str,
    ) -> CredencialPlataforma:
        credencial.status_credencial = status_credencial
        session.flush()

        return credencial
