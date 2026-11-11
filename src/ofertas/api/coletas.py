
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.execucao_coleta import ExecucaoColetaResponse
from ofertas.services.execucao_coleta_service import ExecucaoColetaService
from ofertas.schemas.status_coleta import StatusColetaResponse
from ofertas.services.configuracao_sistema_service import (
    ConfiguracaoSistemaService,
)


router = APIRouter(prefix="/coletas", tags=["Coletas"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/mercado-livre/{plataforma_id}",
    response_model=ExecucaoColetaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Plataforma não encontrada."},
        409: {"description": "Plataforma inativa ou conflito na coleta."},
    },
)
def executar_coleta_mercado_livre(
    plataforma_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> ExecucaoColetaResponse:
    servico = ExecucaoColetaService()

    try:
        execucao = servico.executar(
            db,
            plataforma_id,
        )
        db.commit()

        servico.gerar_afiliados_pendentes(plataforma_id)

        db.refresh(execucao)
        return execucao

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
            detail="A coleta violou uma restrição do banco de dados.",
        ) from exc

    except Exception:
        db.rollback()
        raise
    
@router.get(
    "/status",
    response_model=StatusColetaResponse,
    summary="Consultar status da coleta automática",
)
def consultar_status_coleta(
    db: DbSession,
) -> StatusColetaResponse:
    try:
        return ConfiguracaoSistemaService().consultar_status_coleta(db)

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc