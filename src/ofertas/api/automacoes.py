from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.schemas.automacao_status import AutomacoesStatusResponse
from ofertas.services.automacao_status_service import (
    AutomacaoStatusService,
)


router = APIRouter(
    prefix="/automacoes",
    tags=["Automações"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/status",
    response_model=AutomacoesStatusResponse,
    summary="Consultar o status geral das automações",
    responses={
        404: {"description": "Configuração global não encontrada."},
    },
)
def consultar_status_automacoes(
    db: DbSession,
) -> AutomacoesStatusResponse:
    try:
        return AutomacaoStatusService().consultar(db)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
