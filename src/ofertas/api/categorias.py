
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.categoria import (
    CategoriaCreate,
    CategoriaResponse,
    CategoriaStatusUpdate,
)
from ofertas.services.categoria_service import CategoriaService


router = APIRouter(prefix="/categorias", tags=["Ofertas e categorias"])
service = CategoriaService()


@router.get("/", response_model=list[CategoriaResponse])
def listar_categorias(
    plataforma_id: int | None = Query(default=None, gt=0),
    session: Session = Depends(get_db),
):
    return service.listar(session, plataforma_id)


@router.get("/{categoria_id}", response_model=CategoriaResponse)
def buscar_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    categoria = service.buscar_por_id(session, categoria_id)

    if categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada.",
        )

    return categoria


@router.post(
    "/",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_categoria(
    dados: CategoriaCreate,
    session: Session = Depends(get_db),
):
    try:
        categoria = service.criar(session, dados)
        session.commit()
        session.refresh(categoria)
        return categoria

    except LookupError as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro),
        ) from erro

    except ValueError as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro),
        ) from erro

    except IntegrityError as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível cadastrar a categoria devido a uma restrição do banco de dados.",
        ) from erro


@router.patch(
    "/{categoria_id}/status",
    response_model=CategoriaResponse,
)
def atualizar_status_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    dados: CategoriaStatusUpdate,
    session: Session = Depends(get_db),
):
    try:
        categoria = service.atualizar_status(
            session,
            categoria_id,
            dados.status_categoria,
        )
        session.commit()
        session.refresh(categoria)
        return categoria

    except LookupError as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro),
        ) from erro

    except IntegrityError as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível atualizar o status da categoria.",
        ) from erro
