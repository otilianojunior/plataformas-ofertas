from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.repositories.ciclo_publicacao_repository import (
    CicloPublicacaoRepository,
)
from ofertas.schemas.ciclo_publicacao import CicloPublicacaoResponse


router = APIRouter(
    prefix="/ciclos-publicacao",
    tags=["Ciclos de publicação"],
)

DbSession = Annotated[Session, Depends(get_db)]

StatusCiclo = Literal[
    "em_andamento",
    "concluido",
    "pausado",
    "falhou",
    "interrompido",
]


@router.get(
    "",
    response_model=list[CicloPublicacaoResponse],
    summary="Listar os ciclos de publicação mais recentes",
)
def listar_ciclos_publicacao(
    db: DbSession,
    destino_id: Annotated[int | None, Query(gt=0)] = None,
    status: StatusCiclo | None = None,
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[CicloPublicacaoResponse]:
    return CicloPublicacaoRepository().listar(
        db,
        destino_id=destino_id,
        status=status,
        limite=limite,
    )
