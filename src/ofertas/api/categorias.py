from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.destino_divulgacao import DestinoDivulgacaoResponse
from ofertas.schemas.categoria import (
    CategoriaCreate,
    CategoriaDescontoUpdate,
    CategoriaEtiquetaAfiliadoUpdate,
    CategoriaExclusaoResponse,
    CategoriaPrioridadeUpdate,
    CategoriaResponse,
    CategoriaStatusUpdate,
)
from ofertas.services.categoria_service import CategoriaService


router = APIRouter(prefix="/categorias", tags=["Ofertas e categorias"])
service = CategoriaService()


@router.get("", response_model=list[CategoriaResponse])
def listar_categorias(
    plataforma_id: int | None = Query(default=None, gt=0),
    session: Session = Depends(get_db),
):
    return service.listar(session, plataforma_id)


@router.get(
    "/{categoria_id}",
    response_model=CategoriaResponse,
    responses={404: {"description": "Categoria não encontrada."}},
)
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
    "",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Loja ou grupo não encontrado."},
        409: {"description": "Categoria duplicada ou conflito com o banco."},
    },
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
    responses={
        404: {"description": "Categoria não encontrada."},
        409: {"description": "Conflito com as regras ou o banco de dados."},
    },
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
    "/{categoria_id}/prioridade",
    response_model=CategoriaResponse,
    summary="Favoritar categoria (prioridade na publicação)",
    description=(
        "Categorias favoritas entram antes das outras no rodízio de cada ciclo, "
        "respeitando todas as regras de publicação."
    ),
    responses={404: {"description": "Categoria não encontrada."}},
)
def atualizar_prioridade_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    dados: CategoriaPrioridadeUpdate,
    session: Session = Depends(get_db),
):
    try:
        categoria = service.atualizar_prioridade(session, categoria_id, dados.prioritaria)
        session.commit()
        session.refresh(categoria)
        return categoria

    except LookupError as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro),
        ) from erro

    except Exception:
        session.rollback()
        raise


@router.patch(
    "/{categoria_id}/desconto-minimo",
    response_model=CategoriaResponse,
    responses={
        404: {"description": "Categoria não encontrada."},
        409: {"description": "Conflito com as regras ou o banco de dados."},
    },
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
    responses={
        404: {"description": "Categoria não encontrada."},
        409: {"description": "Conflito com as regras ou o banco de dados."},
    },
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


@router.get(
    "/{categoria_id}/grupos",
    response_model=list[DestinoDivulgacaoResponse],
    responses={404: {"description": "Categoria não encontrada."}},
    summary="Listar grupos associados à categoria",
    description=(
        "Retorna os grupos (Telegram e WhatsApp) que recebem as "
        "publicações da categoria, com canal e status de cada um."
    ),
)
def listar_grupos_categoria(
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
    "/{categoria_id}/grupos/{grupo_id}",
    response_model=list[DestinoDivulgacaoResponse],
    summary="Associar grupo à categoria",
    responses={
        404: {"description": "Categoria ou grupo não encontrado."},
        409: {"description": "Associação inválida ou já existente."},
    },
    description=(
        "Adiciona um grupo Telegram ou WhatsApp à categoria. "
        "Os demais grupos associados são preservados."
    ),
)
def associar_grupo_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    grupo_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    try:
        service.associar_destino(session, categoria_id, grupo_id)
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
    "/{categoria_id}/grupos/{grupo_id}",
    response_model=list[DestinoDivulgacaoResponse],
    summary="Desassociar grupo da categoria",
    responses={
        404: {"description": "Categoria não encontrada ou grupo não associado."},
    },
    description=(
        "Remove somente o grupo informado. Os demais grupos da "
        "categoria continuam associados."
    ),
)
def desassociar_grupo_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    grupo_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    try:
        service.desassociar_destino(session, categoria_id, grupo_id)
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


@router.delete(
    "/{categoria_id}",
    response_model=CategoriaExclusaoResponse,
    summary="Excluir categoria e os produtos dela",
    description=(
        "Apaga a categoria, todos os produtos dela e, em cascata, o histórico "
        "de preços e as publicações desses produtos. Não pode ser desfeito."
    ),
    responses={
        404: {"description": "Categoria não encontrada."},
        409: {"description": "Uma coleta está gravando produtos da categoria agora."},
    },
)
def excluir_categoria(
    categoria_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
):
    try:
        excluidos = service.excluir(session, categoria_id)
        session.commit()
        return CategoriaExclusaoResponse(
            categoria_id=categoria_id,
            produtos_excluidos=excluidos,
        )

    except LookupError as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro),
        ) from erro

    except (OperationalError, IntegrityError) as erro:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Uma coleta está gravando produtos desta categoria agora. "
                "Tente de novo em alguns minutos."
            ),
        ) from erro

    except Exception:
        session.rollback()
        raise
