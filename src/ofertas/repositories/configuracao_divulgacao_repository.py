from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.configuracao_divulgacao import ConfiguracaoDivulgacao


class ConfiguracaoDivulgacaoRepository:
    """Centraliza o acesso às configurações de divulgação."""

    def listar(
        self,
        session: Session,
    ) -> list[ConfiguracaoDivulgacao]:
        consulta = select(ConfiguracaoDivulgacao).order_by(
            ConfiguracaoDivulgacao.id
        )
        return list(session.scalars(consulta).all())

    def buscar_por_destino(
        self,
        session: Session,
        destino_id: int,
    ) -> ConfiguracaoDivulgacao | None:
        consulta = select(ConfiguracaoDivulgacao).where(
            ConfiguracaoDivulgacao.destino_divulgacao_id == destino_id
        )
        return session.scalars(consulta).one_or_none()

    def criar(
        self,
        session: Session,
        *,
        destino_id: int,
        desconto_minimo_percentual,
        preco_minimo,
        preco_maximo,
        intervalo_publicacao_minutos: int,
        identificador_rastreamento: str | None,
        status_configuracao: bool,
    ) -> ConfiguracaoDivulgacao:
        configuracao = ConfiguracaoDivulgacao(
            destino_divulgacao_id=destino_id,
            desconto_minimo_percentual=desconto_minimo_percentual,
            preco_minimo=preco_minimo,
            preco_maximo=preco_maximo,
            intervalo_publicacao_minutos=intervalo_publicacao_minutos,
            identificador_rastreamento=identificador_rastreamento,
            status_configuracao=status_configuracao,
        )
        session.add(configuracao)
        session.flush()
        return configuracao

    def atualizar(
        self,
        session: Session,
        configuracao: ConfiguracaoDivulgacao,
        dados: dict,
    ) -> ConfiguracaoDivulgacao:
        campos_permitidos = {
            "desconto_minimo_percentual",
            "preco_minimo",
            "preco_maximo",
            "intervalo_publicacao_minutos",
            "identificador_rastreamento",
            "status_configuracao",
        }

        for campo, valor in dados.items():
            if campo in campos_permitidos:
                setattr(configuracao, campo, valor)

        session.flush()
        return configuracao

    def registrar_execucao(
        self,
        session: Session,
        configuracao: ConfiguracaoDivulgacao,
        horario,
    ) -> ConfiguracaoDivulgacao:
        """Registra o término do último ciclo de publicação."""

        configuracao.ultima_execucao_publicacao_em = horario
        session.flush()
        return configuracao
