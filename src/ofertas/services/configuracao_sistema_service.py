from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.repositories.configuracao_sistema_repository import (
    ConfiguracaoSistemaRepository,
)


# Flag de configuracoes_sistema que liga a publicação automática de cada canal.
CAMPO_PUBLICACAO_POR_CANAL = {
    "telegram": "publicacao_telegram_ativa",
    "whatsapp": "publicacao_whatsapp_ativa",
}


def publicacao_do_canal_ativa(
    configuracao: ConfiguracaoSistema,
    codigo_canal: str,
) -> bool:
    """Automações gerais ligadas e a publicação do canal ligada."""

    campo = CAMPO_PUBLICACAO_POR_CANAL.get(codigo_canal.lower())

    return bool(
        campo
        and configuracao.automacoes_ativas
        and getattr(configuracao, campo)
    )


class ConfiguracaoSistemaService:
    TEMPO_LIMITE_AGENDADOR_MINUTOS = 3

    AUTOMACOES_VALIDAS = {
        "coleta_mercado_livre",
        "coleta_shopee",
        "publicacao_telegram",
        "publicacao_whatsapp",
    }

    def __init__(self) -> None:
        self.repository = ConfiguracaoSistemaRepository()

    def buscar(self, session: Session) -> ConfiguracaoSistema:
        configuracao = self.repository.buscar(session)

        if configuracao is None:
            raise LookupError(
                "Configuração global do sistema não encontrada."
            )

        return configuracao

    def atualizar(
        self,
        session: Session,
        dados: dict[str, int],
    ) -> ConfiguracaoSistema:
        if not dados:
            raise ValueError(
                "Informe ao menos uma configuração para atualizar."
            )

        if (
            "intervalo_coleta_minutos" in dados
            and dados["intervalo_coleta_minutos"] <= 0
        ):
            raise ValueError(
                "O intervalo de coleta deve ser maior que zero."
            )

        if (
            "limite_produtos_por_categoria" in dados
            and dados["limite_produtos_por_categoria"] < 1
        ):
            raise ValueError(
                "O limite de produtos por categoria deve ser pelo menos 1."
            )

        configuracao = self.buscar(session)

        return self.repository.atualizar(
            session,
            configuracao,
            dados,
        )

    def atualizar_status_automacao(
        self,
        session: Session,
        automacao: str,
        ativa: bool,
    ) -> ConfiguracaoSistema:
        """Atualiza o estado de uma automação específica."""

        if automacao not in self.AUTOMACOES_VALIDAS:
            raise ValueError("Automação não reconhecida.")

        configuracao = self.buscar(session)

        return self.repository.atualizar_status_automacao(
            session,
            configuracao,
            automacao,
            ativa,
        )

    def registrar_sinal(
        self,
        session: Session,
    ) -> ConfiguracaoSistema:
        configuracao = self.buscar(session)

        return self.repository.registrar_sinal(
            session,
            configuracao,
            datetime.now(timezone.utc),
        )

    def atualizar_status_geral(
        self,
        session: Session,
        ativa: bool,
    ) -> ConfiguracaoSistema:
        """Ativa ou pausa globalmente as automações."""

        configuracao = self.buscar(session)

        return self.repository.atualizar_status_geral(
            session,
            configuracao,
            ativa,
        )
