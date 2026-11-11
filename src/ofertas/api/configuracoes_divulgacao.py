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


router = APIRouter(
    prefix="/configuracoes-divulgacao",
    tags=["Configurações de divulgação"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=list[ConfiguracaoDivulgacaoResponse],
)
def listar_configuracoes(
    db: DbSession,
) -> list[ConfiguracaoDivulgacaoResponse]:
    return ConfiguracaoDivulgacaoService().listar(db)


@router.get(
    "/{destino_id}",
    response_model=ConfiguracaoDivulgacaoResponse,
)
def buscar_configuracao(
    destino_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> ConfiguracaoDivulgacaoResponse:
    configuracao = ConfiguracaoDivulgacaoService().buscar_por_destino(
        db,
        destino_id,
    )

    if configuracao is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração de divulgação não encontrada.",
        )

    return configuracao


@router.post(
    "",
    response_model=ConfiguracaoDivulgacaoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Destino não encontrado."},
        409: {"description": "Configuração duplicada ou conflito com o banco."},
    },
)
def criar_configuracao(
    dados: ConfiguracaoDivulgacaoCreate,
    db: DbSession,
) -> ConfiguracaoDivulgacaoResponse:
    try:
        configuracao = ConfiguracaoDivulgacaoService().criar(
            db,
            destino_id=dados.destino_divulgacao_id,
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
    "/{destino_id}",
    response_model=ConfiguracaoDivulgacaoResponse,
    responses={
        404: {"description": "Configuração não encontrada."},
        409: {"description": "Dados inválidos ou conflito com o banco."},
    },
)
def atualizar_configuracao(
    destino_id: Annotated[int, Path(gt=0)],
    dados: ConfiguracaoDivulgacaoUpdate,
    db: DbSession,
) -> ConfiguracaoDivulgacaoResponse:
    try:
        configuracao = ConfiguracaoDivulgacaoService().atualizar(
            db,
            destino_id,
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
