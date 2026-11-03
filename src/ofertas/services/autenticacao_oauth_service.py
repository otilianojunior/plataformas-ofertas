from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from ofertas.core.mercado_livre_oauth_client import MercadoLivreOAuthClient
from ofertas.core.security import (
    descriptografar_credencial,
    criptografar_credencial,
)
from ofertas.models.autenticacao_oauth import AutenticacaoOAuth
from ofertas.repositories.autenticacao_oauth_repository import (
    AutenticacaoOAuthRepository,
)
from ofertas.services.credencial_plataforma_service import (
    CredencialPlataformaService,
)


class AutenticacaoOAuthInvalidaError(Exception):
    """Indica que a autorização precisa ser refeita pelo usuário."""


class AutenticacaoOAuthService:
    """Gerencia os tokens OAuth das plataformas."""

    PLATAFORMA_CODIGO = "mercado_livre"
    MARGEM_RENOVACAO_SEGUNDOS = 300

    def __init__(
        self,
        repository: AutenticacaoOAuthRepository | None = None,
        credencial_service: CredencialPlataformaService | None = None,
        oauth_client: MercadoLivreOAuthClient | None = None,
    ) -> None:
        self.repository = repository or AutenticacaoOAuthRepository()
        self.credencial_service = (
            credencial_service or CredencialPlataformaService()
        )
        self.oauth_client = oauth_client or MercadoLivreOAuthClient()

    def salvar_tokens(
        self,
        session: Session,
        *,
        plataforma_id: int,
        access_token: str,
        refresh_token: str | None,
        expires_in: int,
        token_type: str | None = "Bearer",
        scope: str | None = None,
    ) -> AutenticacaoOAuth:
        if not access_token or not access_token.strip():
            raise ValueError("O access_token é obrigatório.")

        if not refresh_token or not refresh_token.strip():
            raise ValueError("O refresh_token é obrigatório.")

        if not isinstance(expires_in, int) or expires_in <= 0:
            raise ValueError("O tempo de expiração deve ser positivo.")

        expira_em = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )

        return self.repository.salvar_tokens(
            session,
            plataforma_id=plataforma_id,
            access_token_criptografado=criptografar_credencial(
                access_token
            ),
            refresh_token_criptografado=criptografar_credencial(
                refresh_token
            ),
            tipo_token=token_type,
            expira_em=expira_em,
            escopos=scope,
        )

    def obter_access_token(
        self,
        session: Session,
        plataforma_id: int,
    ) -> str:
        autenticacao = self.repository.buscar_ativa_por_plataforma(
            session,
            plataforma_id,
            bloquear=True,
        )

        if autenticacao is None:
            raise LookupError(
                "Não existe autenticação OAuth ativa para esta plataforma."
            )

        agora = datetime.now(timezone.utc)
        expira_em = autenticacao.expira_em

        if expira_em is not None:
            if expira_em.tzinfo is None:
                expira_em = expira_em.replace(tzinfo=timezone.utc)

            margem = timedelta(
                seconds=self.MARGEM_RENOVACAO_SEGUNDOS
            )

            if expira_em > agora + margem:
                return descriptografar_credencial(
                    autenticacao.access_token_criptografado
                )

        return self._renovar_access_token(session, autenticacao)

    def _renovar_access_token(
        self,
        session: Session,
        autenticacao: AutenticacaoOAuth,
    ) -> str:
        if not autenticacao.refresh_token_criptografado:
            self.repository.desativar(session, autenticacao)
            raise AutenticacaoOAuthInvalidaError(
                "Não existe refresh token. É necessária uma nova autorização."
            )

        client_id = self.credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo=self.PLATAFORMA_CODIGO,
            tipo_credencial="client_id",
        )

        client_secret = self.credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo=self.PLATAFORMA_CODIGO,
            tipo_credencial="client_secret",
        )

        refresh_token = descriptografar_credencial(
            autenticacao.refresh_token_criptografado
        )

        try:
            resposta = self.oauth_client.renovar_tokens(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
            )
        except httpx.HTTPStatusError as erro:
            codigo_erro = None

            try:
                codigo_erro = erro.response.json().get("error")
            except (ValueError, AttributeError):
                pass

            if codigo_erro == "invalid_grant":
                self.repository.desativar(session, autenticacao)
                raise AutenticacaoOAuthInvalidaError(
                    "O refresh token foi recusado. "
                    "É necessária uma nova autorização no Mercado Livre."
                ) from erro

            raise

        access_token = resposta.get("access_token")
        refresh_token_novo = resposta.get("refresh_token")
        expires_in = resposta.get("expires_in")

        if (
            not isinstance(access_token, str)
            or not access_token.strip()
            or not isinstance(refresh_token_novo, str)
            or not refresh_token_novo.strip()
            or not isinstance(expires_in, int)
            or expires_in <= 0
        ):
            raise ValueError(
                "A resposta de renovação do Mercado Livre está incompleta."
            )

        expira_em = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )

        self.repository.atualizar_tokens(
            session,
            autenticacao,
            access_token_criptografado=criptografar_credencial(
                access_token
            ),
            refresh_token_criptografado=criptografar_credencial(
                refresh_token_novo
            ),
            tipo_token=resposta.get("token_type", "Bearer"),
            expira_em=expira_em,
            escopos=resposta.get("scope"),
        )

        return access_token