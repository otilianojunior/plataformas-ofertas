from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ofertas.core.autenticacao import SENHA_TAMANHO_MINIMO


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


PerfilUsuario = Literal["admin", "operador"]
SenhaNova = Field(min_length=SENHA_TAMANHO_MINIMO, max_length=200)


class UsuarioCreate(BaseModel):
    login: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9._-]+$")
    nome: str = Field(min_length=1, max_length=120)
    senha: str = SenhaNova
    perfil: PerfilUsuario = "operador"


class UsuarioUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    perfil: PerfilUsuario | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def validar_atualizacao(self):
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar.")

        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")

        return self


class SenhaRedefinir(BaseModel):
    senha: str = SenhaNova


class SenhaTrocar(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=200)
    senha_nova: str = SenhaNova
