from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.destino_divulgacao import (
    DestinoDivulgacaoCreate,
    DestinoDivulgacaoResponse,
    DestinoDivulgacaoStatusUpdate,
)
from ofertas.services.destino_divulgacao_service import (
    DestinoDivulgacaoService,
)


router = APIRouter(
    prefix="/destinos-divulgacao",
    tags=["Destinos de publicação"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[DestinoDivulgacaoResponse])
def listar_destinos(
    db: DbSession,
) -> list[DestinoDivulgacaoResponse]:
    return DestinoDivulgacaoService().listar(db)


@router.get(
    "/{destino_id}",
    response_model=DestinoDivulgacaoResponse,
)
def buscar_destino(
    destino_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> DestinoDivulgacaoResponse:
    destino = DestinoDivulgacaoService().buscar_por_id(
        db,
        destino_id,
    )

    if destino is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destino de divulgação não encontrado.",
        )

    return destino


@router.post(
    "",
    response_model=DestinoDivulgacaoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Plataforma ou credencial não encontrada."},
        409: {"description": "Destino duplicado ou conflito com o banco."},
    },
)
def criar_destino(
    dados: DestinoDivulgacaoCreate,
    db: DbSession,
) -> DestinoDivulgacaoResponse:
    try:
        destino = DestinoDivulgacaoService().criar(db, dados)
        db.commit()
        db.refresh(destino)
        return destino
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
            detail="O destino viola uma restrição do banco de dados.",
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{destino_id}/status",
    response_model=DestinoDivulgacaoResponse,
)
def atualizar_status_destino(
    destino_id: Annotated[int, Path(gt=0)],
    dados: DestinoDivulgacaoStatusUpdate,
    db: DbSession,
) -> DestinoDivulgacaoResponse:
    try:
        destino = DestinoDivulgacaoService().atualizar_status(
            db,
            destino_id,
            dados.status_destino,
        )
        db.commit()
        db.refresh(destino)
        return destino
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise
