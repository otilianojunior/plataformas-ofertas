from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ofertas.core.config import get_settings
from ofertas.db.session import get_db
from ofertas.models.usuario import Usuario
from ofertas.schemas.autenticacao import (
    LoginRequest,
    SessaoResponse,
    UsuarioResponse,
)
from ofertas.services.usuario_service import (
    CredenciaisInvalidasError,
    UsuarioService,
)


router = APIRouter(prefix="/auth", tags=["Autenticação do painel"])

usuario_service = UsuarioService()
_bearer = HTTPBearer(auto_error=False, description="Token devolvido por POST /auth/login.")

RESPOSTA_401 = {401: {"description": "Sem login, sessão expirada ou usuário inativo."}}


def _nao_autorizado(mensagem: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=mensagem,
        headers={"WWW-Authenticate": "Bearer"},
    )


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_db),
) -> Usuario:
    """Exige `Authorization: Bearer <token>` válido."""

    if credenciais is None:
        raise _nao_autorizado("Faça login para continuar.")

    try:
        return usuario_service.usuario_do_token(session, credenciais.credentials)
    except CredenciaisInvalidasError as exc:
        raise _nao_autorizado(str(exc)) from exc


@router.post(
    "/login",
    response_model=SessaoResponse,
    summary="Entrar no painel",
    responses={401: {"description": "Login ou senha inválidos."}},
)
def entrar(dados: LoginRequest, session: Session = Depends(get_db)):
    try:
        usuario, token = usuario_service.autenticar(session, dados.login, dados.senha)
        session.commit()
    except CredenciaisInvalidasError as exc:
        session.rollback()
        raise _nao_autorizado(str(exc)) from exc
    except Exception:
        session.rollback()
        raise

    return SessaoResponse(
        access_token=token,
        expira_em_horas=get_settings().sessao_duracao_horas,
        usuario=UsuarioResponse.model_validate(usuario),
    )


@router.get(
    "/eu",
    response_model=UsuarioResponse,
    summary="Usuário da sessão atual",
    responses=RESPOSTA_401,
)
def eu(usuario: Usuario = Depends(usuario_atual)):
    return usuario
