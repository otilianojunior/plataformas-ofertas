from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.repositories.plataforma_repository import PlataformaRepository
from ofertas.services.autenticacao_oauth_service import (
    AutenticacaoOAuthService,
)
from ofertas.services.credencial_plataforma_service import (
    CredencialPlataformaService,
)
from ofertas.services.estado_oauth_service import EstadoOAuthService


router = APIRouter(
    prefix="/oauth/mercado-livre",
    tags=["Autenticação OAuth - Mercado Livre"],
)

CODIGO_PLATAFORMA = "mercado_livre"
URL_AUTORIZACAO = "https://auth.mercadolivre.com.br/authorization"

plataforma_repository = PlataformaRepository()
credencial_service = CredencialPlataformaService()
estado_service = EstadoOAuthService()
autenticacao_service = AutenticacaoOAuthService(
    credencial_service=credencial_service,
)


@router.get("/autorizar")
def autorizar_mercado_livre(
    session: Session = Depends(get_db),
):
    try:
        plataforma = plataforma_repository.buscar_por_codigo(
            session,
            CODIGO_PLATAFORMA,
        )

        if plataforma is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plataforma Mercado Livre não encontrada.",
            )

        if not plataforma.status_plataforma:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A plataforma Mercado Livre está inativa.",
            )

        client_id = credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo=CODIGO_PLATAFORMA,
            tipo_credencial="client_id",
        )

        redirect_uri = credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo=CODIGO_PLATAFORMA,
            tipo_credencial="redirect_uri",
        )

        estado = estado_service.gerar(
            session,
            plataforma.id,
        )

        session.commit()

        parametros = urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": estado.state,
            }
        )

        return RedirectResponse(
            url=f"{URL_AUTORIZACAO}?{parametros}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    except HTTPException:
        session.rollback()
        raise
    except (LookupError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível iniciar a autorização.",
        ) from exc


@router.get("/callback")
def callback_mercado_livre(
    code: str | None = Query(default=None),
    state: str = Query(...),
    error: str | None = Query(default=None),
    session: Session = Depends(get_db),
):
    try:
        plataforma = plataforma_repository.buscar_por_codigo(
            session,
            CODIGO_PLATAFORMA,
        )

        if plataforma is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plataforma Mercado Livre não encontrada.",
            )

        estado_valido = estado_service.consumir(
            session,
            plataforma_id=plataforma.id,
            state=state,
        )

        if not estado_valido:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estado OAuth inválido, expirado ou já utilizado.",
            )

        # Consome o state antes da comunicação externa.
        session.commit()

        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A autorização foi recusada pelo Mercado Livre.",
            )

        if not code or not code.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O código de autorização não foi informado.",
            )

        client_id = credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo=CODIGO_PLATAFORMA,
            tipo_credencial="client_id",
        )

        client_secret = credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo=CODIGO_PLATAFORMA,
            tipo_credencial="client_secret",
        )

        redirect_uri = credencial_service.buscar_valor_ativo(
            session,
            plataforma_codigo=CODIGO_PLATAFORMA,
            tipo_credencial="redirect_uri",
        )

        oauth_client = autenticacao_service.oauth_client

        resposta = oauth_client.trocar_codigo_por_tokens(
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )

        autenticacao_service.salvar_tokens(
            session,
            plataforma_id=plataforma.id,
            access_token=resposta.get("access_token"),
            refresh_token=resposta.get("refresh_token"),
            expires_in=resposta.get("expires_in"),
            token_type=resposta.get("token_type", "Bearer"),
            scope=resposta.get("scope"),
        )

        session.commit()

        return {
            "status": "autorizado",
            "mensagem": "Autorização do Mercado Livre concluída.",
        }

    except HTTPException:
        session.rollback()
        raise
    except httpx.HTTPError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível concluir a comunicação com o Mercado Livre.",
        ) from exc
    except (LookupError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível salvar a autenticação OAuth.",
        ) from exc