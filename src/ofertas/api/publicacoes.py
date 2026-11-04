
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.models.produto import Produto
from ofertas.publishers.telegram import TelegramPublisher
from ofertas.schemas.publicacao import PublicacaoResponse


router = APIRouter(
    prefix="/publicacoes",
    tags=["Publicações"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/produtos/{produto_id}/destinos/{destino_id}",
    response_model=PublicacaoResponse,
    responses={
        404: {"description": "Produto ou destino não encontrado."},
        409: {"description": "Publicação não permitida ou duplicada."},
        502: {"description": "Falha ao publicar no Telegram."},
    },
)
def publicar_produto(
    produto_id: Annotated[int, Path(gt=0)],
    destino_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> PublicacaoResponse:
    produto = db.get(Produto, produto_id)

    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    try:
        publicacao = TelegramPublisher().publicar(
            db,
            produto,
            destino_id,
        )

        db.commit()
        db.refresh(publicacao)

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
            detail="A publicação viola uma restrição do banco de dados.",
        ) from exc

    except Exception:
        db.rollback()
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
