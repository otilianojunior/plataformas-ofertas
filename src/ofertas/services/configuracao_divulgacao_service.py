from decimal import Decimal

from sqlalchemy.orm import Session

from ofertas.models.configuracao_divulgacao import ConfiguracaoDivulgacao
from ofertas.repositories.configuracao_divulgacao_repository import (
    ConfiguracaoDivulgacaoRepository,
)
from ofertas.repositories.destino_divulgacao_repository import (
    DestinoDivulgacaoRepository,
)


class ConfiguracaoDivulgacaoService:
    """Implementa as regras de negócio das configurações de divulgação."""

    def __init__(
        self,
        repository: ConfiguracaoDivulgacaoRepository | None = None,
        destino_repository: DestinoDivulgacaoRepository | None = None,
    ) -> None:
        self.repository = (
            repository or ConfiguracaoDivulgacaoRepository()
        )
        self.destino_repository = (
            destino_repository or DestinoDivulgacaoRepository()
        )

    def buscar_por_destino(
        self,
        session: Session,
        destino_id: int,
    ) -> ConfiguracaoDivulgacao | None:
        return self.repository.buscar_por_destino(
            session,
            destino_id,
        )

    def listar(
        self,
        session: Session,
    ) -> list[ConfiguracaoDivulgacao]:
        return self.repository.listar(session)

    def _validar_dados(
        self,
        *,
        desconto_minimo_percentual: Decimal,
        preco_minimo: Decimal | None,
        preco_maximo: Decimal | None,
        intervalo_publicacao_minutos: int,
        identificador_rastreamento: str | None,
    ) -> None:
        if not Decimal("0") <= desconto_minimo_percentual <= Decimal("100"):
            raise ValueError(
                "O desconto mínimo deve estar entre 0 e 100."
            )

        if preco_minimo is not None and preco_minimo < 0:
            raise ValueError("O preço mínimo não pode ser negativo.")

        if preco_maximo is not None and preco_maximo < 0:
            raise ValueError("O preço máximo não pode ser negativo.")

        if (
            preco_minimo is not None
            and preco_maximo is not None
            and preco_maximo < preco_minimo
        ):
            raise ValueError(
                "O preço máximo não pode ser menor que o preço mínimo."
            )

        if intervalo_publicacao_minutos < 0:
            raise ValueError(
                "O intervalo entre ciclos de publicação não pode ser negativo."
            )

        if (
            identificador_rastreamento is not None
            and len(identificador_rastreamento.strip()) > 150
        ):
            raise ValueError(
                "O identificador de rastreamento deve ter até 150 caracteres."
            )

    def criar(
        self,
        session: Session,
        *,
        destino_id: int,
        desconto_minimo_percentual: Decimal = Decimal("0"),
        preco_minimo: Decimal | None = None,
        preco_maximo: Decimal | None = None,
        intervalo_publicacao_minutos: int = 0,
        identificador_rastreamento: str | None = None,
        status_configuracao: bool = True,
    ) -> ConfiguracaoDivulgacao:
        destino = self.destino_repository.buscar_por_id(
            session,
            destino_id,
        )

        if destino is None:
            raise LookupError(
                f"Destino de divulgação com ID {destino_id} não encontrado."
            )

        existente = self.repository.buscar_por_destino(
            session,
            destino_id,
        )

        if existente is not None:
            raise ValueError(
                "Já existe uma configuração para esse destino de divulgação."
            )

        if identificador_rastreamento is not None:
            identificador_rastreamento = (
                identificador_rastreamento.strip() or None
            )

        self._validar_dados(
            desconto_minimo_percentual=desconto_minimo_percentual,
            preco_minimo=preco_minimo,
            preco_maximo=preco_maximo,
            intervalo_publicacao_minutos=intervalo_publicacao_minutos,
            identificador_rastreamento=identificador_rastreamento,
        )

        return self.repository.criar(
            session,
            destino_id=destino_id,
            desconto_minimo_percentual=desconto_minimo_percentual,
            preco_minimo=preco_minimo,
            preco_maximo=preco_maximo,
            intervalo_publicacao_minutos=intervalo_publicacao_minutos,
            identificador_rastreamento=identificador_rastreamento,
            status_configuracao=status_configuracao,
        )

    def atualizar(
        self,
        session: Session,
        destino_id: int,
        dados: dict,
    ) -> ConfiguracaoDivulgacao:
        configuracao = self.repository.buscar_por_destino(
            session,
            destino_id,
        )

        if configuracao is None:
            raise LookupError(
                f"Configuração do destino {destino_id} não encontrada."
            )

        dados_normalizados = dict(dados)

        campos_obrigatorios = {
            "desconto_minimo_percentual",
            "intervalo_publicacao_minutos",
            "status_configuracao",
        }

        for campo in campos_obrigatorios:
            if campo in dados_normalizados and dados_normalizados[campo] is None:
                raise ValueError(f"{campo} não pode ser nulo.")

        dados_atuais = {
            "desconto_minimo_percentual": (
                configuracao.desconto_minimo_percentual
            ),
            "preco_minimo": configuracao.preco_minimo,
            "preco_maximo": configuracao.preco_maximo,
            "intervalo_publicacao_minutos": (
                configuracao.intervalo_publicacao_minutos
            ),
            "identificador_rastreamento": (
                configuracao.identificador_rastreamento
            ),
        }

        for campo in dados_atuais:
            if campo in dados_normalizados:
                dados_atuais[campo] = dados_normalizados[campo]

        identificador = dados_atuais["identificador_rastreamento"]

        if identificador is not None:
            identificador = identificador.strip() or None
            dados_atuais["identificador_rastreamento"] = identificador

            if "identificador_rastreamento" in dados_normalizados:
                dados_normalizados["identificador_rastreamento"] = (
                    identificador
                )

        self._validar_dados(**dados_atuais)

        return self.repository.atualizar(
            session,
            configuracao,
            dados_normalizados,
        )
