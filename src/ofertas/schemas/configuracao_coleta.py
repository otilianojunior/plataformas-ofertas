from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfiguracaoColetaCreate(BaseModel):
    plataforma_id: int = Field(gt=0)
    categoria_id: int | None = Field(default=None, gt=0)
    desconto_minimo_percentual: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )
    preco_minimo: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    preco_maximo: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    intervalo_coleta_minutos: int = Field(default=60, gt=0)
    status_coleta: bool = True

    @model_validator(mode="after")
    def validar_faixa_de_preco(self):
        if (
            self.preco_minimo is not None
            and self.preco_maximo is not None
            and self.preco_maximo < self.preco_minimo
        ):
            raise ValueError(
                "O preço máximo não pode ser menor que o preço mínimo."
            )
        return self


class ConfiguracaoColetaUpdate(BaseModel):
    categoria_id: int | None = Field(default=None, gt=0)
    desconto_minimo_percentual: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )
    preco_minimo: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    preco_maximo: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    intervalo_coleta_minutos: int | None = Field(default=None, gt=0)
    status_coleta: bool | None = None

    @model_validator(mode="after")
    def validar_campos_e_faixa(self):
        if not self.model_fields_set:
            raise ValueError("Informe pelo menos um campo para atualizar.")

        if (
            self.preco_minimo is not None
            and self.preco_maximo is not None
            and self.preco_maximo < self.preco_minimo
        ):
            raise ValueError(
                "O preço máximo não pode ser menor que o preço mínimo."
            )

        return self


class ConfiguracaoColetaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plataforma_id: int
    categoria_id: int | None
    desconto_minimo_percentual: Decimal
    preco_minimo: Decimal | None
    preco_maximo: Decimal | None
    intervalo_coleta_minutos: int
    status_coleta: bool
    created_at: datetime
    updated_at: datetime
