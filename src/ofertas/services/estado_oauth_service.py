import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ofertas.models.estado_oauth import EstadoOAuth
from ofertas.repositories.estado_oauth_repository import (
    EstadoOAuthRepository,
)


class EstadoOAuthService:
    """Gerencia a geração e validação dos estados temporários OAuth."""

    VALIDADE_MINUTOS = 10

    def __init__(
        self,
        repository: EstadoOAuthRepository | None = None,
    ) -> None:
        self.repository = repository or EstadoOAuthRepository()

    def gerar(
        self,
        session: Session,
        plataforma_id: int,
    ) -> EstadoOAuth:
        state = secrets.token_urlsafe(32)
        agora = datetime.now(timezone.utc)
        expira_em = agora + timedelta(
            minutes=self.VALIDADE_MINUTOS
        )

        return self.repository.criar(
            session,
            plataforma_id=plataforma_id,
            state=state,
            expira_em=expira_em,
        )

    def consumir(
        self,
        session: Session,
        *,
        plataforma_id: int,
        state: str,
    ) -> bool:
        if not state or not state.strip():
            return False

        agora = datetime.now(timezone.utc)

        return self.repository.consumir_valido(
            session,
            plataforma_id=plataforma_id,
            state=state,
            agora=agora,
        )

    def limpar_expirados(self, session: Session) -> int:
        agora = datetime.now(timezone.utc)

        return self.repository.limpar_expirados(
            session,
            agora=agora,
        )
