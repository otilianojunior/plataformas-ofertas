from decimal import Decimal

from sqlalchemy.orm import Session

from ofertas.models.configuracao_coleta import ConfiguracaoColeta
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.repositories.configuracao_coleta_repository import (
    ConfiguracaoColetaRepository,
)
from ofertas.schemas.configuracao_coleta import (
    ConfiguracaoColetaCreate,
    ConfiguracaoColetaUpdate,
)


class ConfiguracaoColetaService:
    """Implementa as regras de negócio das configurações de coleta."""

    def __init__(
        self,
        repository: ConfiguracaoColetaRepository | None = None,
    ) -> None:
        self.repository = repository or ConfiguracaoColetaRepository()

    def listar(
        self,
        session: Session,
        plataforma_id: int | None = None,
    ) -> list[ConfiguracaoColeta]:
        return self.repository.listar(session, plataforma_id)

    def buscar_por_id(
        self,
        session: Session,
        configuracao_id: int,
    ) -> ConfiguracaoColeta | None:
        return self.repository.buscar_por_id(session, configuracao_id)

    def _validar_escopo(
        self,
        session: Session,
        plataforma_id: int,
        categoria_id: int | None,
    ) -> None:
        plataforma = session.get(Plataforma, plataforma_id)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de ID '{plataforma_id}' não encontrada."
            )

        if not plataforma.status_plataforma:
            raise ValueError(
                "Não é possível configurar a coleta de uma plataforma inativa."
            )

        if categoria_id is not None:
            categoria = session.get(PlataformaCategoria, categoria_id)

            if categoria is None:
                raise LookupError(
                    f"Categoria de ID '{categoria_id}' não encontrada."
                )

            if categoria.plataforma_id != plataforma_id:
                raise ValueError(
                    "A categoria informada não pertence à plataforma."
                )

    @staticmethod
    def _validar_faixa_preco(
        preco_minimo: Decimal | None,
        preco_maximo: Decimal | None,
    ) -> None:
        if (
            preco_minimo is not None
            and preco_maximo is not None
            and preco_maximo < preco_minimo
        ):
            raise ValueError(
                "O preço máximo não pode ser menor que o preço mínimo."
            )

    def criar(
        self,
        session: Session,
        dados: ConfiguracaoColetaCreate,
    ) -> ConfiguracaoColeta:
        self._validar_escopo(
            session,
            dados.plataforma_id,
            dados.categoria_id,
        )

        existente = self.repository.buscar_por_escopo(
            session,
            dados.plataforma_id,
            dados.categoria_id,
        )

        if existente is not None:
            raise ValueError(
                "Já existe uma configuração de coleta para esta plataforma "
                "e categoria."
            )

        self._validar_faixa_preco(
            dados.preco_minimo,
            dados.preco_maximo,
        )

        return self.repository.criar(
            session,
            dados.model_dump(),
        )

    def atualizar(
        self,
        session: Session,
        configuracao_id: int,
        dados: ConfiguracaoColetaUpdate,
    ) -> ConfiguracaoColeta | None:
        configuracao = self.repository.buscar_por_id(
            session,
            configuracao_id,
        )

        if configuracao is None:
            return None

        alteracoes = dados.model_dump(exclude_unset=True)

        categoria_id = alteracoes.get(
            "categoria_id",
            configuracao.categoria_id,
        )

        self._validar_escopo(
            session,
            configuracao.plataforma_id,
            categoria_id,
        )

        if categoria_id != configuracao.categoria_id:
            existente = self.repository.buscar_por_escopo(
                session,
                configuracao.plataforma_id,
                categoria_id,
            )

            if existente is not None and existente.id != configuracao.id:
                raise ValueError(
                    "Já existe uma configuração para esta plataforma "
                    "e categoria."
                )

        preco_minimo = alteracoes.get(
            "preco_minimo",
            configuracao.preco_minimo,
        )
        preco_maximo = alteracoes.get(
            "preco_maximo",
            configuracao.preco_maximo,
        )

        self._validar_faixa_preco(preco_minimo, preco_maximo)

        for campo, valor in alteracoes.items():
            setattr(configuracao, campo, valor)

        session.flush()
        return configuracao
