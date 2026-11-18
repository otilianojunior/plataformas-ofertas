from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.api.autenticacao import RESPOSTA_403, exigir_admin
from ofertas.db.session import get_db
from ofertas.models.usuario import Usuario
from ofertas.schemas.autenticacao import (
    SenhaRedefinir,
    UsuarioCreate,
    UsuarioResponse,
    UsuarioUpdate,
)
from ofertas.services.usuario_service import UsuarioService


# Gestão de usuários: só admin (o login é exigido em main.py).
router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários do painel"],
    responses=RESPOSTA_403,
)

DbSession = Annotated[Session, Depends(get_db)]
Admin = Annotated[Usuario, Depends(exigir_admin)]
UsuarioId = Annotated[int, Path(gt=0)]

usuario_service = UsuarioService()


def _erro(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, IntegrityError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O usuário viola uma restrição do banco de dados.",
        )
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("", response_model=list[UsuarioResponse], summary="Listar usuários")
def listar_usuarios(db: DbSession, _: Admin):
    return usuario_service.listar(db)


@router.post(
    "",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário",
    responses={409: {"description": "Login já existe."}},
)
def criar_usuario(dados: UsuarioCreate, db: DbSession, _: Admin):
    try:
        usuario = usuario_service.criar(db, **dados.model_dump())
        db.commit()
        return usuario
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise _erro(exc) from exc
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{usuario_id}",
    response_model=UsuarioResponse,
    summary="Alterar nome, perfil ou situação",
    responses={
        404: {"description": "Usuário não encontrado."},
        409: {"description": "Deixaria o sistema sem admin ativo ou desativaria a própria conta."},
    },
)
def atualizar_usuario(usuario_id: UsuarioId, dados: UsuarioUpdate, db: DbSession, admin: Admin):
    try:
        usuario = usuario_service.atualizar(
            db, usuario_id, dados.model_dump(exclude_unset=True), executor=admin
        )
        db.commit()
        return usuario
    except (LookupError, ValueError, IntegrityError) as exc:
        db.rollback()
        raise _erro(exc) from exc
    except Exception:
        db.rollback()
        raise


@router.put(
    "/{usuario_id}/senha",
    response_model=UsuarioResponse,
    summary="Redefinir a senha de um usuário",
    description="As sessões abertas desse usuário são encerradas.",
    responses={404: {"description": "Usuário não encontrado."}},
)
def redefinir_senha(usuario_id: UsuarioId, dados: SenhaRedefinir, db: DbSession, _: Admin):
    try:
        usuario = usuario_service.redefinir_senha(db, usuario_id, dados.senha)
        db.commit()
        return usuario
    except LookupError as exc:
        db.rollback()
        raise _erro(exc) from exc
    except Exception:
        db.rollback()
        raise
