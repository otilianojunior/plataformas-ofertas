from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.oferta import Oferta
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.publishers.telegram import TelegramPublisher
from ofertas.schemas.publicacao import PublicacaoResponse


router = APIRouter(
    prefix="/publicacoes",
    tags=["Publicações"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/ofertas/{oferta_id}/destinos/{destino_id}",
    response_model=PublicacaoResponse,
    responses={
        404: {"description": "Oferta ou destino não encontrado."},
        409: {"description": "Publicação não permitida ou duplicada."},
        500: {"description": "Erro interno ao processar a publicação."},
        502: {"description": "Falha ao publicar no Telegram."},
    },
)
def publicar_oferta(
    oferta_id: Annotated[int, Path(gt=0)],
    destino_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> PublicacaoResponse:
    oferta = db.get(Oferta, oferta_id)

    if oferta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta não encontrada.",
        )

    try:
        publicacao = TelegramPublisher().publicar(
            db,
            oferta,
            destino_id,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except Exception:
        raise

    if publicacao.status_publicacao == "falhou":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Falha ao publicar no Telegram. "
                "A tentativa foi registrada no banco."
            ),
        )

    return publicacao
