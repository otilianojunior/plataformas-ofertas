from datetime import datetime

from sqlalchemy.orm import Session

from ofertas.models.configuracao_sistema import ConfiguracaoSistema


class ConfiguracaoSistemaRepository:
    """Centraliza o acesso à configuração global do sistema."""

    CAMPOS_AUTOMACAO = {
        "coleta_mercado_livre": "coleta_mercado_livre_ativa",
        "coleta_shopee": "coleta_shopee_ativa",
        "publicacao_telegram": "publicacao_telegram_ativa",
        "publicacao_whatsapp": "publicacao_whatsapp_ativa",
    }

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

    def atualizar_status_automacao(
        self,
        session: Session,
        configuracao: ConfiguracaoSistema,
        automacao: str,
        ativa: bool,
    ) -> ConfiguracaoSistema:
        """Atualiza o estado de uma automação conhecida."""
        campo = self.CAMPOS_AUTOMACAO.get(automacao)

        if campo is None:
            raise ValueError("Automação não reconhecida.")

        setattr(configuracao, campo, ativa)
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
