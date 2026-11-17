
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import get_db
from ofertas.models.publicacao import Publicacao
from ofertas.schemas.publicacao import (
    PublicacaoManualResponse,
    PublicacaoResponse,
)
from ofertas.services.publicacao_service import PublicacaoService


router = APIRouter(
    prefix="/publicacoes",
    tags=["Publicações"],
)

DbSession = Annotated[Session, Depends(get_db)]

service = PublicacaoService()


@router.post(
    "/produtos/{produto_id}",
    response_model=PublicacaoManualResponse,
    summary="Publicar produto em todos os grupos da categoria",
    description=(
        "Publicação manual. Localiza a categoria do produto e tenta "
        "publicar em cada grupo associado a ela cujo canal e grupo estejam "
        "ativos, aplicando todas as regras de publicação (elegibilidade, "
        "link afiliado, desconto mínimo, faixa de preço, republicação e "
        "tentativas). Não obedece às janelas de execução. O resultado de "
        "cada grupo vem em `resultados`. Grupos do WhatsApp são ignorados "
        "até o publisher ser implementado."
    ),
    responses={
        404: {"description": "Produto ou categoria não encontrado."},
        409: {
            "description": (
                "Nenhum grupo pôde receber a publicação (categoria inativa, "
                "sem grupos ou todos ignorados). O detalhe traz o motivo "
                "de cada grupo."
            )
        },
        502: {
            "description": (
                "Nenhuma publicação concluída e ao menos um envio falhou. "
                "As tentativas ficam registradas no banco."
            )
        },
    },
)
def publicar_produto(
    produto_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> PublicacaoManualResponse:
    try:
        resumo = service.publicar_em_todos_destinos(db, produto_id)

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

    except Exception:
        db.rollback()
        raise

    resposta = PublicacaoManualResponse.model_validate(resumo)

    if resposta.publicadas == 0:
        codigo = (
            status.HTTP_502_BAD_GATEWAY
            if resposta.falhas
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(
            status_code=codigo,
            detail={
                "mensagem": "O produto não foi publicado em nenhum grupo.",
                **resposta.model_dump(mode="json"),
            },
        )

    return resposta


@router.post(
    "/produtos/{produto_id}/grupos/{grupo_id}",
    response_model=PublicacaoResponse,
    summary="Publicar produto em um grupo específico",
    description=(
        "Publica o produto no destino informado, desde que o grupo "
        "esteja associado à categoria do produto."
    ),
    responses={
        404: {"description": "Produto, categoria ou destino não encontrado."},
        409: {"description": "Destino não associado ou publicação não permitida."},
        502: {"description": "Falha no envio ao Telegram."},
    },
)
def publicar_produto_em_grupo(
    produto_id: Annotated[int, Path(gt=0)],
    grupo_id: Annotated[int, Path(gt=0)],
    db: DbSession,
) -> Publicacao:
    try:
        publicacao = service.publicar_produto(
            db,
            produto_id,
            destino_id=grupo_id,
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
                "Falha ao publicar no destino informado. "
                "A tentativa foi registrada no banco."
            ),
        )

    return publicacao
