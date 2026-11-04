from datetime import datetime

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

    def atualizar_status_coleta(
        self,
        session: Session,
        configuracao: ConfiguracaoSistema,
        ativa: bool,
    ) -> ConfiguracaoSistema:
        configuracao.coleta_automatica_ativa = ativa
        session.flush()
        return configuracao

    def registrar_sinal(
        self,
        session: Session,
        configuracao: ConfiguracaoSistema,
        horario: datetime,
    ) -> ConfiguracaoSistema:
        configuracao.agendador_ultimo_sinal_em = horario
        session.flush()
        return configuracao
