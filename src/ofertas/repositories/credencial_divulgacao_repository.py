from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.credencial_divulgacao import CredencialDivulgacao


class CredencialDivulgacaoRepository:
    def listar(
        self,
        session: Session,
        plataforma_divulgacao_id: int | None = None,
    ) -> list[CredencialDivulgacao]:
        consulta = select(CredencialDivulgacao)

        if plataforma_divulgacao_id is not None:
            consulta = consulta.where(
                CredencialDivulgacao.plataforma_divulgacao_id
                == plataforma_divulgacao_id
            )

        consulta = consulta.order_by(CredencialDivulgacao.id)
        return list(session.scalars(consulta).all())

    def buscar_por_id(
        self,
        session: Session,
        credencial_id: int,
    ) -> CredencialDivulgacao | None:
        return session.get(CredencialDivulgacao, credencial_id)

    def criar(
        self,
        session: Session,
        *,
        plataforma_divulgacao_id: int,
        tipo_credencial: str,
        valor_criptografado: str,
        status_credencial: str = "ativa",
    ) -> CredencialDivulgacao:
        credencial = CredencialDivulgacao(
            plataforma_divulgacao_id=plataforma_divulgacao_id,
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
        credencial: CredencialDivulgacao,
        status_credencial: str,
    ) -> CredencialDivulgacao:
        credencial.status_credencial = status_credencial
        session.flush()
        return credencial
