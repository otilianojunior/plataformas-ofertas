from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.configuracao_divulgacao import (
    ConfiguracaoDivulgacaoCreate,
    ConfiguracaoDivulgacaoResponse,
    ConfiguracaoDivulgacaoUpdate,
)
from ofertas.services.configuracao_divulgacao_service import (
    ConfiguracaoDivulgacaoService,
)


# Rotas aninhadas em /grupos. Este router é incluído antes do router de
# grupos para que /grupos/configuracoes não seja lido como /grupos/{grupo_id}.
router = APIRouter(
    prefix="/grupos",
    tags=["Configurações de divulgação"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/configuracoes",
    response_model=list[ConfiguracaoDivulgacaoResponse],
    summary="Listar a configuração de divulgação de todos os grupos",
)
def listar_configuracoes(
    db: DbSession,
) -> list[ConfiguracaoDivulgacaoResponse]:
    return ConfiguracaoDivulgacaoService().listar(db)


@router.get(
    "/{grupo_id}/configuracao",
    summary="Consultar a configuração de divulgação do grupo",
    response_model=ConfiguracaoDivulgacaoResponse,
    responses={404: {"description": "Configuração de divulgação não encontrada."}},
)
def buscar_configuracao(
    grupo_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> ConfiguracaoDivulgacaoResponse:
    configuracao = ConfiguracaoDivulgacaoService().buscar_por_destino(
        db,
        grupo_id,
    )

    if configuracao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração de divulgação não encontrada.",
        )

    return configuracao


@router.post(
    "/{grupo_id}/configuracao",
    summary="Criar a configuração de divulgação do grupo",
    response_model=ConfiguracaoDivulgacaoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Grupo não encontrado."},
        409: {"description": "Configuração duplicada ou conflito com o banco."},
    },
)
def criar_configuracao(
    grupo_id: Annotated[int, Path(gt=0)],
    dados: ConfiguracaoDivulgacaoCreate,
    db: DbSession,
) -> ConfiguracaoDivulgacaoResponse:
    try:
        configuracao = ConfiguracaoDivulgacaoService().criar(
            db,
            destino_id=grupo_id,
            desconto_minimo_percentual=dados.desconto_minimo_percentual,
            preco_minimo=dados.preco_minimo,
            preco_maximo=dados.preco_maximo,
            intervalo_publicacao_minutos=dados.intervalo_publicacao_minutos,
            identificador_rastreamento=dados.identificador_rastreamento,
            status_configuracao=dados.status_configuracao,
        )
        db.commit()
        db.refresh(configuracao)
        return configuracao
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
            detail="A configuração viola uma restrição do banco de dados.",
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{grupo_id}/configuracao",
    summary="Alterar a configuração de divulgação do grupo",
    response_model=ConfiguracaoDivulgacaoResponse,
    responses={
        404: {"description": "Configuração não encontrada."},
        409: {"description": "Dados inválidos ou conflito com o banco."},
    },
)
def atualizar_configuracao(
    grupo_id: Annotated[int, Path(gt=0)],
    dados: ConfiguracaoDivulgacaoUpdate,
    db: DbSession,
) -> ConfiguracaoDivulgacaoResponse:
    try:
        configuracao = ConfiguracaoDivulgacaoService().atualizar(
            db,
            grupo_id,
            dados.model_dump(exclude_unset=True),
        )
        db.commit()
        db.refresh(configuracao)
        return configuracao
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
            detail="A configuração viola uma restrição do banco de dados.",
        ) from exc
    except Exception:
        db.rollback()
        raise
