from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.destino_divulgacao import DestinoDivulgacaoResponse
from ofertas.schemas.categoria import (
    CategoriaCreate,
    CategoriaDescontoUpdate,
    CategoriaDestinoDivulgacaoUpdate,
    CategoriaEtiquetaAfiliadoUpdate,
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
            detail=(
                "Não foi possível cadastrar a categoria "
                "devido a uma restrição do banco de dados."
            ),
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


@router.patch(
    "/{categoria_id}/desconto-minimo",
    response_model=CategoriaResponse,
)
def atualizar_desconto_minimo_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    dados: CategoriaDescontoUpdate,
    session: Session = Depends(get_db),
):
    try:
        categoria = service.atualizar_desconto_minimo(
            session,
            categoria_id,
            dados.desconto_minimo_percentual,
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
            detail=(
                "Não foi possível atualizar o desconto mínimo "
                "da categoria."
            ),
        ) from erro


@router.patch(
    "/{categoria_id}/etiqueta-afiliado",
    response_model=CategoriaResponse,
)
def atualizar_etiqueta_afiliado_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    dados: CategoriaEtiquetaAfiliadoUpdate,
    session: Session = Depends(get_db),
):
    try:
        categoria = service.atualizar_etiqueta_afiliado(
            session,
            categoria_id,
            dados.etiqueta_afiliado,
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
            detail=(
                "Não foi possível atualizar a etiqueta "
                "de afiliado da categoria."
            ),
        ) from erro


@router.patch(
    "/{categoria_id}/destino-divulgacao",
    response_model=CategoriaResponse,
)
def atualizar_destino_divulgacao_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    dados: CategoriaDestinoDivulgacaoUpdate,
    session: Session = Depends(get_db),
):
    try:
        categoria = service.atualizar_destino_divulgacao(
            session,
            categoria_id,
            dados.destino_divulgacao_id,
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
            detail=(
                "Não foi possível atualizar o destino "
                "de divulgação da categoria."
            ),
        ) from erro


@router.get(
    "/{categoria_id}/destinos",
    response_model=list[DestinoDivulgacaoResponse],
    summary="Listar grupos associados à categoria",
    description=(
        "Retorna os destinos Telegram e WhatsApp associados à categoria, "
        "incluindo nome, canal e status de cada grupo."
    ),
)
def listar_destinos_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    try:
        return service.listar_destinos(session, categoria_id)
    except LookupError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro),
        ) from erro


@router.post(
    "/{categoria_id}/destinos/{destino_id}",
    response_model=list[DestinoDivulgacaoResponse],
    summary="Associar grupo à categoria",
    description=(
        "Adiciona um destino Telegram ou WhatsApp à categoria. "
        "Os demais grupos associados são preservados."
    ),
)
def associar_destino_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    destino_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    try:
        service.associar_destino(session, categoria_id, destino_id)
        session.commit()
        return service.listar_destinos(session, categoria_id)

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
            detail="A associação viola uma restrição do banco de dados.",
        ) from erro

    except Exception:
        session.rollback()
        raise


@router.delete(
    "/{categoria_id}/destinos/{destino_id}",
    response_model=list[DestinoDivulgacaoResponse],
    summary="Desassociar grupo da categoria",
    description=(
        "Remove somente o destino informado. Os demais grupos da "
        "categoria continuam associados."
    ),
)
def desassociar_destino_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    destino_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    try:
        service.desassociar_destino(session, categoria_id, destino_id)
        session.commit()
        return service.listar_destinos(session, categoria_id)

    except LookupError as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro),
        ) from erro

    except Exception:
        session.rollback()
        raise
