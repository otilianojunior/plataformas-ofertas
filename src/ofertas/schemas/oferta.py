
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class OfertaCreate(BaseModel):
    plataforma_id: int = Field(gt=0)
    categoria_id: int | None = Field(default=None, gt=0)
    id_item_plataforma: str = Field(min_length=1, max_length=150)
    titulo: str = Field(min_length=1, max_length=500)
    descricao: str | None = None
    url: HttpUrl
    affiliate_url: HttpUrl | None = None
    imagem_url: HttpUrl | None = None
    preco_atual: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    preco_original: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    percentual_desconto: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    expira_em: datetime


class OfertaUpdate(BaseModel):
    categoria_id: int | None = Field(default=None, gt=0)
    titulo: str | None = Field(default=None, min_length=1, max_length=500)
    descricao: str | None = None
    url: HttpUrl | None = None
    affiliate_url: HttpUrl | None = None
    imagem_url: HttpUrl | None = None
    preco_atual: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    preco_original: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    percentual_desconto: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    expira_em: datetime | None = None

    @model_validator(mode="after")
    def validar_campos_informados(self):
        if not self.model_fields_set:
            raise ValueError("Informe pelo menos um campo para atualizar.")
        return self


class OfertaStatusUpdate(BaseModel):
    status_oferta: bool


class OfertaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_id: int
    categoria_id: int | None
    id_item_plataforma: str
    titulo: str
    descricao: str | None
    url: str
    affiliate_url: str | None
    imagem_url: str | None
    preco_atual: Decimal
    preco_original: Decimal | None
    percentual_desconto: Decimal | None
    status_oferta: bool
    coletada_em: datetime
    expira_em: datetime
    created_at: datetime
    updated_at: datetime
