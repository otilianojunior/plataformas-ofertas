from sqlalchemy.orm import Session

from ofertas.models.configuracao_sistema import ConfiguracaoSistema


class ConfiguracaoSistemaRepository:
    """Centraliza o acesso à configuração global do sistema."""

    def buscar(self, session: Session) -> ConfiguracaoSistema | None:
        return session.get(ConfiguracaoSistema, 1)

    def atualizar(
        self,
        session: Session,
        configuracao: ConfiguracaoSistema,
        intervalo_coleta_minutos: int,
    ) -> ConfiguracaoSistema:
        configuracao.intervalo_coleta_minutos = intervalo_coleta_minutos
        session.flush()
        return configuracao
