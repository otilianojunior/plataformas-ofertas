from sqlalchemy.orm import Session

from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.repositories.configuracao_sistema_repository import (
    ConfiguracaoSistemaRepository,
)


class ConfiguracaoSistemaService:
    def __init__(self) -> None:
        self.repository = ConfiguracaoSistemaRepository()

    def buscar(self, session: Session) -> ConfiguracaoSistema:
        configuracao = self.repository.buscar(session)

        if configuracao is None:
            raise LookupError("Configuração global do sistema não encontrada.")

        return configuracao

    def atualizar(
        self,
        session: Session,
        intervalo_coleta_minutos: int,
    ) -> ConfiguracaoSistema:
        if intervalo_coleta_minutos <= 0:
            raise ValueError("O intervalo de coleta deve ser maior que zero.")

        configuracao = self.buscar(session)

        return self.repository.atualizar(
            session,
            configuracao,
            intervalo_coleta_minutos,
        )
