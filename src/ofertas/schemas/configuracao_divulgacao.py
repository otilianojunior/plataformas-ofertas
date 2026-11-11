from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfiguracaoDivulgacaoCreate(BaseModel):
    destino_divulgacao_id: int = Field(gt=0)
    desconto_minimo_percentual: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        decimal_places=2,
    )
    preco_minimo: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )
    preco_maximo: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )
    intervalo_publicacao_minutos: int = Field(default=0, ge=0)
    identificador_rastreamento: str | None = Field(
        default=None,
        max_length=150,
    )
    status_configuracao: bool = True


class ConfiguracaoDivulgacaoUpdate(BaseModel):
    desconto_minimo_percentual: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        decimal_places=2,
    )
    preco_minimo: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )
    preco_maximo: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )
    intervalo_publicacao_minutos: int | None = Field(
        default=None,
        ge=0,
    )
    identificador_rastreamento: str | None = Field(
        default=None,
        max_length=150,
    )
    status_configuracao: bool | None = None


    @model_validator(mode="after")
    def validar_campos_nao_nulos(self):
        campos_obrigatorios = {
            "desconto_minimo_percentual",
            "intervalo_publicacao_minutos",
            "status_configuracao",
        }

        for campo in campos_obrigatorios:
            if (
                campo in self.model_fields_set
                and getattr(self, campo) is None
            ):
                raise ValueError(f"{campo} não pode ser nulo.")

        return self


class ConfiguracaoDivulgacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    destino_divulgacao_id: int
    desconto_minimo_percentual: Decimal
    preco_minimo: Decimal | None
    preco_maximo: Decimal | None
    intervalo_publicacao_minutos: int
    identificador_rastreamento: str | None
    status_configuracao: bool
    created_at: datetime
    updated_at: datetime
