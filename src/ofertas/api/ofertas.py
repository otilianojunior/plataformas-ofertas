
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.oferta import (
    OfertaCreate,
    OfertaResponse,
    OfertaStatusUpdate,
    OfertaUpdate,
)
from ofertas.services.oferta_service import OfertaService


router = APIRouter(prefix="/ofertas", tags=["Ofertas e categorias"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[OfertaResponse])
def listar_ofertas(db: DbSession) -> list[OfertaResponse]:
    return OfertaService().listar(db)


@router.get(
    "/{oferta_id}",
    response_model=OfertaResponse,
    responses={404: {"description": "Oferta não encontrada."}},
)
def buscar_oferta(
    oferta_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> OfertaResponse:
    oferta = OfertaService().buscar_por_id(db, oferta_id)

    if oferta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta não encontrada.",
        )

    return oferta


@router.post(
    "",
    response_model=OfertaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Plataforma não encontrada."},
        409: {"description": "Oferta duplicada ou conflito com o banco."},
        422: {"description": "Dados inválidos."},
    },
)
def criar_oferta(dados: OfertaCreate, db: DbSession) -> OfertaResponse:
    try:
        oferta = OfertaService().criar(db, dados)
        db.commit()
        db.refresh(oferta)
        return oferta
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
            detail="A oferta viola uma restrição do banco de dados.",
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{oferta_id}",
    response_model=OfertaResponse,
    responses={
        404: {"description": "Oferta ou categoria não encontrada."},
        409: {"description": "Dados incompatíveis com as regras do sistema."},
    },
)
def atualizar_oferta(
    oferta_id: Annotated[int, Path(gt=0)],
    dados: OfertaUpdate,
    db: DbSession,
) -> OfertaResponse:
    try:
        oferta = OfertaService().atualizar(db, oferta_id, dados)

        if oferta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Oferta não encontrada.",
            )

        db.commit()
        db.refresh(oferta)
        return oferta

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
            detail="A atualização viola uma restrição do banco de dados.",
        ) from exc


@router.patch(
    "/{oferta_id}/status",
    response_model=OfertaResponse,
    responses={404: {"description": "Oferta não encontrada."}},
)
def atualizar_status_oferta(
    oferta_id: Annotated[int, Path(gt=0)],
    dados: OfertaStatusUpdate,
    db: DbSession,
) -> OfertaResponse:
    oferta = OfertaService().atualizar_status(
        db,
        oferta_id,
        dados.status_oferta,
    )

    if oferta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta não encontrada.",
        )

    try:
        db.commit()
        db.refresh(oferta)
        return oferta
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível atualizar o status da oferta.",
        ) from exc
