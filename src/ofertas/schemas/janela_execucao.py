from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JanelaExecucaoCreate(BaseModel):
    hora_inicio: time
    hora_fim: time
    ativa: bool = True

    @model_validator(mode="after")
    def validar_horarios(self):
        if self.hora_inicio >= self.hora_fim:
            raise ValueError(
                "O horário de início deve ser anterior ao horário de fim."
            )
        return self


class JanelaExecucaoUpdate(BaseModel):
    hora_inicio: time | None = None
    hora_fim: time | None = None
    ativa: bool | None = None

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
