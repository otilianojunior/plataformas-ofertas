from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.janela_execucao import (
    JanelaExecucaoCreate,
    JanelaExecucaoResponse,
    JanelaExecucaoUpdate,
)
from ofertas.services.janela_execucao_service import JanelaExecucaoService


router = APIRouter(
    prefix="/janelas-execucao",
    tags=["Janelas de execução"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=list[JanelaExecucaoResponse],
)
def listar_janelas(
    db: DbSession,
) -> list[JanelaExecucaoResponse]:
    return JanelaExecucaoService().listar(db)


@router.get(
    "/{janela_id}",
    response_model=JanelaExecucaoResponse,
    responses={404: {"description": "Janela não encontrada."}},
)
def buscar_janela(
    janela_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> JanelaExecucaoResponse:
    try:
        return JanelaExecucaoService().buscar(db, janela_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=JanelaExecucaoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Sobreposição ou conflito com o banco."},
    },
)
def criar_janela(
    dados: JanelaExecucaoCreate,
    db: DbSession,
) -> JanelaExecucaoResponse:
    try:
        janela = JanelaExecucaoService().criar(
            db,
            hora_inicio=dados.hora_inicio,
            hora_fim=dados.hora_fim,
            ativa=dados.ativa,
        )
        db.commit()
        db.refresh(janela)
        return janela
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
            detail="A janela viola uma restrição do banco de dados.",
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{janela_id}",
    response_model=JanelaExecucaoResponse,
    responses={
        404: {"description": "Janela não encontrada."},
        409: {"description": "Sobreposição ou conflito com o banco."},
    },
)
def atualizar_janela(
    janela_id: Annotated[int, Path(gt=0)],
    dados: JanelaExecucaoUpdate,
    db: DbSession,
) -> JanelaExecucaoResponse:
    try:
        janela = JanelaExecucaoService().atualizar(
            db,
            janela_id,
            dados.model_dump(exclude_unset=True),
        )
        db.commit()
        db.refresh(janela)
        return janela
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
            detail="A janela viola uma restrição do banco de dados.",
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.delete(
    "/{janela_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Janela não encontrada."}},
)
def excluir_janela(
    janela_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> Response:
    try:
        JanelaExecucaoService().excluir(db, janela_id)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise
