from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.credencial_divulgacao import (
    CredencialDivulgacaoCreate,
    CredencialDivulgacaoResponse,
    CredencialDivulgacaoStatusUpdate,
)
from ofertas.services.credencial_divulgacao_service import (
    CredencialDivulgacaoService,
)

router = APIRouter(
    prefix="/credenciais-divulgacao",
    tags=["Credenciais dos canais de divulgação"],
)

service = CredencialDivulgacaoService()


@router.get(
    "",
    responses={404: {"description": "Canal de divulgação não encontrado(a)."}},
    response_model=list[CredencialDivulgacaoResponse])
def listar_credenciais(
    plataforma_divulgacao_id: int | None = Query(default=None, gt=0),
    session: Session = Depends(get_db),
):
    try:
        return service.listar(session, plataforma_divulgacao_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{credencial_id}",
    responses={404: {"description": "Credencial não encontrada."}},
    response_model=CredencialDivulgacaoResponse,
)
def buscar_credencial(
    credencial_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    try:
        return service.buscar_por_id(session, credencial_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "",
    responses={
        404: {"description": "Canal de divulgação não encontrado(a)."},
        409: {"description": "Regra de negócio violada (ex.: canal inativo ou credencial ativa duplicada)."},
    },
    response_model=CredencialDivulgacaoResponse,
    status_code=201,
)
def criar_credencial(
    dados: CredencialDivulgacaoCreate,
    session: Session = Depends(get_db),
):
    try:
        credencial = service.criar(
            session,
            plataforma_divulgacao_id=dados.plataforma_divulgacao_id,
            nome_credencial=dados.nome_credencial,
            tipo_credencial=dados.tipo_credencial,
            valor=dados.valor,
        )
        session.commit()
        session.refresh(credencial)
        return credencial
    except LookupError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A credencial viola uma restrição do banco de dados.",
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Não foi possível salvar a credencial de divulgação.",
        ) from exc


@router.patch(
    "/{credencial_id}/status",
    responses={
        404: {"description": "Credencial não encontrada."},
        409: {"description": "Já existe outra credencial ativa do mesmo tipo."},
    },
    response_model=CredencialDivulgacaoResponse,
)
def atualizar_status_credencial(
    credencial_id: Annotated[int, Path(gt=0)],
    dados: CredencialDivulgacaoStatusUpdate,
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
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A credencial viola uma restrição do banco de dados.",
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Não foi possível atualizar a credencial de divulgação.",
        ) from exc
