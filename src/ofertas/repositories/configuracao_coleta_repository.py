from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.configuracao_coleta import ConfiguracaoColeta


class ConfiguracaoColetaRepository:
    """Centraliza o acesso aos dados das configurações de coleta."""

    def listar(
        self,
        session: Session,
        plataforma_id: int | None = None,
    ) -> list[ConfiguracaoColeta]:
        consulta = select(ConfiguracaoColeta).order_by(
            ConfiguracaoColeta.plataforma_id,
            ConfiguracaoColeta.categoria_id,
            ConfiguracaoColeta.id,
        )

        if plataforma_id is not None:
            consulta = consulta.where(
                ConfiguracaoColeta.plataforma_id == plataforma_id
            )

        return list(session.scalars(consulta).all())

    def buscar_por_id(
        self,
        session: Session,
        configuracao_id: int,
    ) -> ConfiguracaoColeta | None:
        consulta = select(ConfiguracaoColeta).where(
            ConfiguracaoColeta.id == configuracao_id
        )
        return session.scalars(consulta).one_or_none()

    def buscar_por_escopo(
        self,
        session: Session,
        plataforma_id: int,
        categoria_id: int | None,
    ) -> ConfiguracaoColeta | None:
        consulta = select(ConfiguracaoColeta).where(
            ConfiguracaoColeta.plataforma_id == plataforma_id,
            ConfiguracaoColeta.categoria_id == categoria_id,
        )
        return session.scalars(consulta).one_or_none()

    def criar(
        self,
        session: Session,
        dados: dict,
    ) -> ConfiguracaoColeta:
        configuracao = ConfiguracaoColeta(**dados)
        session.add(configuracao)
        session.flush()
        return configuracao
