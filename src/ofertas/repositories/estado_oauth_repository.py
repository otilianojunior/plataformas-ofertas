from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ofertas.models.estado_oauth import EstadoOAuth


class EstadoOAuthRepository:
    """Centraliza o acesso aos estados temporários de autorização OAuth."""

    def criar(
        self,
        session: Session,
        *,
        plataforma_id: int,
        state: str,
        expira_em: datetime,
    ) -> EstadoOAuth:
        estado = EstadoOAuth(
            plataforma_id=plataforma_id,
            state=state,
            expira_em=expira_em,
        )

        session.add(estado)
        session.flush()

        return estado

    def consumir_valido(
        self,
        session: Session,
        *,
        plataforma_id: int,
        state: str,
        agora: datetime,
    ) -> bool:
        comando = (
            delete(EstadoOAuth)
            .where(
                EstadoOAuth.plataforma_id == plataforma_id,
                EstadoOAuth.state == state,
                EstadoOAuth.expira_em > agora,
            )
            .returning(EstadoOAuth.id)
        )

        resultado = session.execute(comando)
        return resultado.scalar_one_or_none() is not None

    def limpar_expirados(
        self,
        session: Session,
        *,
        agora: datetime,
    ) -> int:
        comando = (
            delete(EstadoOAuth)
            .where(EstadoOAuth.expira_em <= agora)
        )

        resultado = session.execute(comando)
        return resultado.rowcount or 0
