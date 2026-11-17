from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.repositories.plataforma_repository import PlataformaRepository
from ofertas.schemas.execucao_coleta import ExecucaoColetaResponse
from ofertas.services.execucao_coleta_service import ExecucaoColetaService


router = APIRouter(prefix="/coletas", tags=["Coletas"])
DbSession = Annotated[Session, Depends(get_db)]

RESPOSTAS_COLETA = {
    404: {"description": "Loja não cadastrada."},
    409: {
        "description": (
            "Loja inativa ou já existe uma coleta em andamento para ela."
        )
    },
}


def _executar_coleta(
    db: Session,
    codigo_loja: str,
) -> ExecucaoColetaResponse:
    """Executa a coleta manual da loja e gera os afiliados pendentes."""

    servico = ExecucaoColetaService()

    try:
        loja = PlataformaRepository().buscar_por_codigo(db, codigo_loja)

        if loja is None:
            raise LookupError(f"Loja '{codigo_loja}' não cadastrada.")

        loja_id = loja.id
        executar = (
            servico.executar_shopee
            if codigo_loja == ExecucaoColetaService.CODIGO_SHOPEE
            else servico.executar
        )

        execucao = executar(db, loja_id)
        db.commit()

        servico.gerar_afiliados_pendentes(loja_id)

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


@router.post(
    "/mercado-livre",
    response_model=ExecucaoColetaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Executar coleta manual do Mercado Livre",
    description="Não obedece às janelas de execução.",
    responses=RESPOSTAS_COLETA,
)
def executar_coleta_mercado_livre(db: DbSession) -> ExecucaoColetaResponse:
    return _executar_coleta(db, ExecucaoColetaService.CODIGO_MERCADO_LIVRE)


@router.post(
    "/shopee",
    response_model=ExecucaoColetaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Executar coleta manual da Shopee",
    description="Não obedece às janelas de execução.",
    responses=RESPOSTAS_COLETA,
)
def executar_coleta_shopee(db: DbSession) -> ExecucaoColetaResponse:
    return _executar_coleta(db, ExecucaoColetaService.CODIGO_SHOPEE)
