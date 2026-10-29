from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.plataforma import (
    PlataformaCreate,
    PlataformaResponse,
    PlataformaStatusUpdate,
)
from ofertas.services.plataforma_service import PlataformaService


router = APIRouter(prefix="/plataformas", tags=["Lojas de origem das ofertas"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[PlataformaResponse])
def listar_plataformas(db: DbSession) -> list[PlataformaResponse]:
    return PlataformaService().listar(db)


@router.get("/{codigo}", response_model=PlataformaResponse)
def buscar_plataforma(
    codigo: str,
    db: DbSession,
) -> PlataformaResponse:
    plataforma = PlataformaService().buscar_por_codigo(db, codigo)

    if plataforma is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plataforma não encontrada.",
        )

    return plataforma


@router.post(
    "",
    response_model=PlataformaResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_plataforma(
    dados: PlataformaCreate,
    db: DbSession,
) -> PlataformaResponse:
    try:
        plataforma = PlataformaService().criar(db, dados)
        db.commit()
        db.refresh(plataforma)
        return plataforma
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
            detail="Já existe uma plataforma com esse código.",
        ) from exc


@router.patch("/{codigo}/status", response_model=PlataformaResponse)
def atualizar_status_plataforma(
    codigo: str,
    dados: PlataformaStatusUpdate,
    db: DbSession,
) -> PlataformaResponse:
    try:
        plataforma = PlataformaService().atualizar_status(
            db,
            codigo,
            dados.status_plataforma,
        )
        db.commit()
        db.refresh(plataforma)
        return plataforma
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise
