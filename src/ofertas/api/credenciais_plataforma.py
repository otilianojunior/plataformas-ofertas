from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.credencial_plataforma import (
    CredencialPlataformaCreate,
    CredencialPlataformaResponse,
    CredencialPlataformaStatusUpdate,
)
from ofertas.services.credencial_plataforma_service import (
    CredencialPlataformaService,
)

router = APIRouter(
    prefix="/credenciais-plataforma",
    tags=["Credenciais de acesso às lojas"],
)

service = CredencialPlataformaService()


@router.get("", response_model=list[CredencialPlataformaResponse])
def listar_credenciais(
    plataforma_id: int | None = Query(default=None, gt=0),
    session: Session = Depends(get_db),
):
    try:
        return service.listar(session, plataforma_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{credencial_id}",
    response_model=CredencialPlataformaResponse,
)
def buscar_credencial(
    credencial_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    try:
        return service.buscar_por_id(session, credencial_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=CredencialPlataformaResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_credencial(
    dados: CredencialPlataformaCreate,
    session: Session = Depends(get_db),
):
    try:
        credencial = service.criar(
            session,
            plataforma_id=dados.plataforma_id,
            tipo_credencial=dados.tipo_credencial,
            valor=dados.valor,
        )
        session.commit()
        session.refresh(credencial)
        return credencial
    except LookupError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível salvar a credencial.",
        ) from exc


@router.patch(
    "/{credencial_id}/status",
    response_model=CredencialPlataformaResponse,
)
def atualizar_status_credencial(
    credencial_id: Annotated[int, Path(gt=0)],
    dados: CredencialPlataformaStatusUpdate,
    session: Session = Depends(get_db),
):
    try:
        credencial = service.atualizar_status(
            session,
            credencial_id,
            dados.status_credencial,
        )
        session.commit()
        session.refresh(credencial)
        return credencial
    except LookupError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível atualizar o status da credencial.",
        ) from exc
