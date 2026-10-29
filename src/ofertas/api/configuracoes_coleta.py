
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.configuracao_coleta import (
    ConfiguracaoColetaCreate,
    ConfiguracaoColetaResponse,
    ConfiguracaoColetaUpdate,
)
from ofertas.services.configuracao_coleta_service import (
    ConfiguracaoColetaService,
)


router = APIRouter(
    prefix="/configuracoes-coleta",
    tags=["Configurações de coleta"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ConfiguracaoColetaResponse])
def listar_configuracoes(
    db: DbSession,
    plataforma_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[ConfiguracaoColetaResponse]:
    return ConfiguracaoColetaService().listar(db, plataforma_id)


@router.get(
    "/{configuracao_id}",
    response_model=ConfiguracaoColetaResponse,
    responses={404: {"description": "Configuração não encontrada."}},
)
def buscar_configuracao(
    configuracao_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> ConfiguracaoColetaResponse:
    configuracao = ConfiguracaoColetaService().buscar_por_id(
        db,
        configuracao_id,
    )

    if configuracao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração de coleta não encontrada.",
        )

    return configuracao


@router.post(
    "",
    response_model=ConfiguracaoColetaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Plataforma ou categoria não encontrada."},
        409: {"description": "Configuração duplicada ou conflito com o banco."},
    },
)
def criar_configuracao(
    dados: ConfiguracaoColetaCreate,
    db: DbSession,
) -> ConfiguracaoColetaResponse:
    try:
        configuracao = ConfiguracaoColetaService().criar(db, dados)
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


@router.patch(
    "/{configuracao_id}",
    response_model=ConfiguracaoColetaResponse,
    responses={
        404: {"description": "Configuração, plataforma ou categoria não encontrada."},
        409: {"description": "Conflito com as regras ou o banco de dados."},
    },
)
def atualizar_configuracao(
    configuracao_id: Annotated[int, Path(gt=0)],
    dados: ConfiguracaoColetaUpdate,
    db: DbSession,
) -> ConfiguracaoColetaResponse:
    try:
        configuracao = ConfiguracaoColetaService().atualizar(
            db,
            configuracao_id,
            dados,
        )

        if configuracao is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuração de coleta não encontrada.",
            )

        db.commit()
        db.refresh(configuracao)
        return configuracao
    except HTTPException:
        db.rollback()
        raise
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
