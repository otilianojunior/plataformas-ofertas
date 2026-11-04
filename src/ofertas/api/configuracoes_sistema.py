from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.configuracao_sistema import (
    ConfiguracaoSistemaResponse,
    ConfiguracaoSistemaUpdate,
)
from ofertas.services.configuracao_sistema_service import (
    ConfiguracaoSistemaService,
)


router = APIRouter(
    prefix="/configuracoes-sistema",
    tags=["Configurações do sistema"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=ConfiguracaoSistemaResponse,
    responses={404: {"description": "Configuração global não encontrada."}},
)
def buscar_configuracao_sistema(
    db: DbSession,
) -> ConfiguracaoSistemaResponse:
    try:
        return ConfiguracaoSistemaService().buscar(db)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "",
    response_model=ConfiguracaoSistemaResponse,
    responses={
        404: {"description": "Configuração global não encontrada."},
        409: {"description": "Conflito com as regras ou o banco de dados."},
    },
)
def atualizar_configuracao_sistema(
    dados: ConfiguracaoSistemaUpdate,
    db: DbSession,
) -> ConfiguracaoSistemaResponse:
    try:
        configuracao = ConfiguracaoSistemaService().atualizar(
            db,
            dados.intervalo_coleta_minutos,
        )
        db.commit()
        db.refresh(configuracao)
        return configuracao
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A configuração viola uma restrição do banco de dados.",
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.post(
    "/coleta-automatica/iniciar",
    response_model=ConfiguracaoSistemaResponse,
    responses={404: {"description": "Configuração global não encontrada."}},
)
def iniciar_coleta_automatica(
    db: DbSession,
) -> ConfiguracaoSistemaResponse:
    try:
        configuracao = (
            ConfiguracaoSistemaService().iniciar_coleta_automatica(db)
        )
        db.commit()
        db.refresh(configuracao)
        return configuracao
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.post(
    "/coleta-automatica/pausar",
    response_model=ConfiguracaoSistemaResponse,
    responses={404: {"description": "Configuração global não encontrada."}},
)
def pausar_coleta_automatica(
    db: DbSession,
) -> ConfiguracaoSistemaResponse:
    try:
        configuracao = (
            ConfiguracaoSistemaService().pausar_coleta_automatica(db)
        )
        db.commit()
        db.refresh(configuracao)
        return configuracao
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise
