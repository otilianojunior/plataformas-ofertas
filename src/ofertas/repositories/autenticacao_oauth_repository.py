from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ofertas.models.autenticacao_oauth import AutenticacaoOAuth


class AutenticacaoOAuthRepository:
    """Centraliza o acesso aos registros de autenticação OAuth."""

    def buscar_ativa_por_plataforma(
        self,
        session: Session,
        plataforma_id: int,
        *,
        bloquear: bool = False,
    ) -> AutenticacaoOAuth | None:
        consulta = (
            select(AutenticacaoOAuth)
            .where(
                AutenticacaoOAuth.plataforma_id == plataforma_id,
                AutenticacaoOAuth.status_autenticacao == "ativa",
            )
            .order_by(AutenticacaoOAuth.id.desc())
            .limit(1)
        )

        if bloquear:
            consulta = consulta.with_for_update()

        return session.scalar(consulta)

    def desativar_outras_ativas(
        self,
        session: Session,
        *,
        plataforma_id: int,
        autenticacao_id: int,
    ) -> None:
        comando = (
            update(AutenticacaoOAuth)
            .where(
                AutenticacaoOAuth.plataforma_id == plataforma_id,
                AutenticacaoOAuth.status_autenticacao == "ativa",
                AutenticacaoOAuth.id != autenticacao_id,
            )
            .values(status_autenticacao="inativa")
        )
        session.execute(comando)

    def desativar(
        self,
        session: Session,
        autenticacao: AutenticacaoOAuth,
    ) -> None:
        autenticacao.status_autenticacao = "inativa"
        session.flush()

    def atualizar_tokens(
        self,
        session: Session,
        autenticacao: AutenticacaoOAuth,
        *,
        access_token_criptografado: str,
        refresh_token_criptografado: str,
        tipo_token: str | None,
        expira_em: datetime,
        escopos: str | None,
    ) -> AutenticacaoOAuth:
        autenticacao.access_token_criptografado = access_token_criptografado
        autenticacao.refresh_token_criptografado = refresh_token_criptografado
        autenticacao.tipo_token = tipo_token
        autenticacao.expira_em = expira_em

        if escopos is not None:
            autenticacao.escopos = escopos

        session.flush()
        return autenticacao

    def salvar_tokens(
        self,
        session: Session,
        *,
        plataforma_id: int,
        access_token_criptografado: str,
        refresh_token_criptografado: str | None,
        tipo_token: str | None,
        expira_em: datetime | None,
        escopos: str | None,
    ) -> AutenticacaoOAuth:
        autenticacao = self.buscar_ativa_por_plataforma(
            session,
            plataforma_id,
            bloquear=True,
        )

        if autenticacao is None:
            autenticacao = AutenticacaoOAuth(
                plataforma_id=plataforma_id,
                access_token_criptografado=access_token_criptografado,
                refresh_token_criptografado=refresh_token_criptografado,
                tipo_token=tipo_token,
                expira_em=expira_em,
                escopos=escopos,
                status_autenticacao="ativa",
            )
            session.add(autenticacao)
            session.flush()
        else:
            autenticacao.access_token_criptografado = (
                access_token_criptografado
            )
            autenticacao.refresh_token_criptografado = (
                refresh_token_criptografado
            )
            autenticacao.tipo_token = tipo_token
            autenticacao.expira_em = expira_em
            autenticacao.escopos = escopos

        self.desativar_outras_ativas(
            session,
            plataforma_id=plataforma_id,
            autenticacao_id=autenticacao.id,
        )

        session.flush()
        return autenticacao