
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.produto import (
    ProdutoCreate,
    ProdutoResponse,
    ProdutoUpdate,
)
from ofertas.services.produto_service import ProdutoService


router = APIRouter(prefix="/produtos", tags=["Produtos"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ProdutoResponse])
def listar_produtos(db: DbSession) -> list[ProdutoResponse]:
    return ProdutoService().listar(db)


@router.get(
    "/{produto_id}",
    response_model=ProdutoResponse,
    responses={404: {"description": "Produto não encontrado."}},
)
def buscar_produto(
    produto_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> ProdutoResponse:
    produto = ProdutoService().buscar_por_id(db, produto_id)

    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    return produto


@router.post(
    "",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Plataforma ou categoria não encontrada."},
        409: {"description": "Produto duplicado ou conflito com o banco."},
    },
)
def criar_produto(
    dados: ProdutoCreate,
    db: DbSession,
) -> ProdutoResponse:
    try:
        produto = ProdutoService().criar(db, dados)
        db.commit()
        db.refresh(produto)
        return produto

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
            detail="O produto viola uma restrição do banco de dados.",
        ) from exc

    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{produto_id}",
    response_model=ProdutoResponse,
    responses={
        404: {"description": "Produto ou categoria não encontrada."},
        409: {"description": "Dados incompatíveis com as regras do sistema."},
    },
)
def atualizar_produto(
    produto_id: Annotated[int, Path(gt=0)],
    dados: ProdutoUpdate,
    db: DbSession,
) -> ProdutoResponse:
    try:
        produto = ProdutoService().atualizar(db, produto_id, dados)

        if produto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado.",
            )

        db.commit()
        db.refresh(produto)
        return produto

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

    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{produto_id}/monitoramento",
    response_model=ProdutoResponse,
    responses={404: {"description": "Produto não encontrado."}},
)
def atualizar_monitoramento_produto(
    produto_id: Annotated[int, Path(gt=0)],
    dados: ProdutoUpdate,
    db: DbSession,
) -> ProdutoResponse:
    if dados.status_monitoramento is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe o status_monitoramento.",
        )

    try:
        produto = ProdutoService().atualizar_status_monitoramento(
            db,
            produto_id,
            dados.status_monitoramento,
        )

        if produto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado.",
            )

        db.commit()
        db.refresh(produto)
        return produto

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
            detail="Não foi possível atualizar o monitoramento do produto.",
        ) from exc

    except Exception:
        db.rollback()
        raise
