from datetime import datetime, time

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


DESCRICAO_HORA_INICIO = (
    "Horário local (America/Sao_Paulo) em que a janela começa, sem fuso. "
    "Exemplo: 08:00."
)
DESCRICAO_HORA_FIM = (
    "Horário local (America/Sao_Paulo) em que a janela termina, sem fuso, "
    "exclusivo. Janelas não atravessam a meia-noite: para cobrir até o fim "
    "do dia use 23:59:59."
)


def _validar_sem_fuso(valor: time | None) -> time | None:
    if valor is not None and valor.tzinfo is not None:
        raise ValueError(
            "Informe o horário sem fuso horário; ele é interpretado "
            "como horário de Brasília (America/Sao_Paulo)."
        )
    return valor


class JanelaExecucaoCreate(BaseModel):
    hora_inicio: time = Field(description=DESCRICAO_HORA_INICIO)
    hora_fim: time = Field(description=DESCRICAO_HORA_FIM)
    ativa: bool = True

    _validar_fuso = field_validator("hora_inicio", "hora_fim")(
        _validar_sem_fuso
    )

    @model_validator(mode="after")
    def validar_horarios(self):
        if self.hora_inicio >= self.hora_fim:
            raise ValueError(
                "O horário de início deve ser anterior ao horário de fim."
            )
        return self


class JanelaExecucaoUpdate(BaseModel):
    hora_inicio: time | None = Field(
        default=None,
        description=DESCRICAO_HORA_INICIO,
    )
    hora_fim: time | None = Field(
        default=None,
        description=DESCRICAO_HORA_FIM,
    )
    ativa: bool | None = None

    _validar_fuso = field_validator("hora_inicio", "hora_fim")(
        _validar_sem_fuso
    )

    @model_validator(mode="after")
    def validar_atualizacao(self):
        if not self.model_fields_set:
            raise ValueError(
                "Informe ao menos um campo para atualizar."
            )

        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")

        if (
            self.hora_inicio is not None
            and self.hora_fim is not None
            and self.hora_inicio >= self.hora_fim
        ):
            raise ValueError(
                "O horário de início deve ser anterior ao horário de fim."
            )

        return self


class JanelaExecucaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hora_inicio: time
    hora_fim: time
    ativa: bool
    created_at: datetime
    updated_at: datetime
