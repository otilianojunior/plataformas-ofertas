from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.plataforma_divulgacao import (
    PlataformaDivulgacaoCreate,
    PlataformaDivulgacaoResponse,
    PlataformaDivulgacaoStatusUpdate,
)
from ofertas.services.plataforma_divulgacao_service import (
    PlataformaDivulgacaoService,
)


router = APIRouter(
    prefix="/plataformas-divulgacao",
    tags=["Canais de divulgação"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[PlataformaDivulgacaoResponse])
def listar_plataformas_divulgacao(
    db: DbSession,
) -> list[PlataformaDivulgacaoResponse]:
    return PlataformaDivulgacaoService().listar(db)


@router.get(
    "/{codigo}",
    response_model=PlataformaDivulgacaoResponse,
)
def buscar_plataforma_divulgacao(
    codigo: str,
    db: DbSession,
) -> PlataformaDivulgacaoResponse:
    plataforma = PlataformaDivulgacaoService().buscar_por_codigo(
        db,
        codigo,
    )

    if plataforma is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plataforma de divulgação não encontrada.",
        )

    return plataforma


@router.post(
    "",
    response_model=PlataformaDivulgacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_plataforma_divulgacao(
    dados: PlataformaDivulgacaoCreate,
    db: DbSession,
) -> PlataformaDivulgacaoResponse:
    try:
        plataforma = PlataformaDivulgacaoService().criar(db, dados)
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
            detail="Já existe uma plataforma de divulgação com esse código.",
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{codigo}/status",
    response_model=PlataformaDivulgacaoResponse,
)
def atualizar_status_plataforma_divulgacao(
    codigo: str,
    dados: PlataformaDivulgacaoStatusUpdate,
    db: DbSession,
) -> PlataformaDivulgacaoResponse:
    try:
        plataforma = PlataformaDivulgacaoService().atualizar_status(
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
