from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfiguracaoSistemaUpdate(BaseModel):
    intervalo_coleta_minutos: int | None = Field(default=None, gt=0)
    limite_produtos_por_categoria: int | None = Field(
        default=None,
        ge=1,
    )
    limite_publicacoes_por_ciclo: int | None = Field(
        default=None,
        ge=1,
        description="Máximo de mensagens por ciclo em cada grupo, somando as categorias.",
    )
    validade_preco_minutos: int | None = Field(
        default=None,
        ge=10,
        description="Só publica produto com preço confirmado por coleta há no máximo este tempo.",
    )

    @model_validator(mode="after")
    def validar_atualizacao(self):
        if not self.model_fields_set:
            raise ValueError(
                "Informe ao menos uma configuração para atualizar."
            )

        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")

        return self


class ConfiguracaoSistemaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    automacoes_ativas: bool
    intervalo_coleta_minutos: int
    limite_produtos_por_categoria: int
    limite_publicacoes_por_ciclo: int
    validade_preco_minutos: int
    coleta_mercado_livre_ativa: bool
    coleta_shopee_ativa: bool
    publicacao_telegram_ativa: bool
    publicacao_whatsapp_ativa: bool
    agendador_ultimo_sinal_em: datetime | None
    created_at: datetime
    updated_at: datetime
