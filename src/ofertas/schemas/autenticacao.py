from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=60)
    senha: str = Field(min_length=1, max_length=200)


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    nome: str
    perfil: str
    ativo: bool
    ultimo_login_em: datetime | None


class SessaoResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_em_horas: int
    usuario: UsuarioResponse
