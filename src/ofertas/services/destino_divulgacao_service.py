from sqlalchemy.orm import Session

from ofertas.models.credencial_divulgacao import CredencialDivulgacao
from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.repositories.destino_divulgacao_repository import (
    DestinoDivulgacaoRepository,
)
from ofertas.repositories.plataforma_divulgacao_repository import (
    PlataformaDivulgacaoRepository,
)
from ofertas.schemas.destino_divulgacao import DestinoDivulgacaoCreate


class DestinoDivulgacaoService:
    """Implementa as regras de negócio dos destinos de divulgação."""

    def __init__(
        self,
        repository: DestinoDivulgacaoRepository | None = None,
        plataforma_repository: PlataformaDivulgacaoRepository | None = None,
    ) -> None:
        self.repository = repository or DestinoDivulgacaoRepository()
        self.plataforma_repository = (
            plataforma_repository or PlataformaDivulgacaoRepository()
        )

    def listar(self, session: Session) -> list[DestinoDivulgacao]:
        return self.repository.listar(session)

    def buscar_por_id(
        self,
        session: Session,
        destino_id: int,
    ) -> DestinoDivulgacao | None:
        return self.repository.buscar_por_id(session, destino_id)

    def criar(
        self,
        session: Session,
        dados: DestinoDivulgacaoCreate,
    ) -> DestinoDivulgacao:
        identificador = dados.identificador_destino.strip()
        nome = dados.nome_destino.strip()

        if not identificador or not nome:
            raise ValueError(
                "O identificador e o nome do destino não podem ficar vazios."
            )

        plataforma = self.plataforma_repository.buscar_por_id(
            session,
            dados.plataforma_divulgacao_id,
        )

        if plataforma is None:
            raise LookupError(
                f"Plataforma de divulgação com ID "
                f"{dados.plataforma_divulgacao_id} não encontrada."
            )

        if not plataforma.status_plataforma:
            raise ValueError(
                "Não é possível cadastrar destinos em uma plataforma "
                "de divulgação inativa."
            )

        credencial = session.get(
            CredencialDivulgacao,
            dados.credencial_divulgacao_id,
        )

        if credencial is None:
            raise LookupError(
                f"Credencial de divulgação com ID "
                f"{dados.credencial_divulgacao_id} não encontrada."
            )

        if (
            credencial.plataforma_divulgacao_id
            != dados.plataforma_divulgacao_id
        ):
            raise ValueError(
                "A credencial informada não pertence à plataforma selecionada."
            )

        if credencial.status_credencial != "ativa":
            raise ValueError(
                "Não é possível cadastrar destinos com uma credencial inativa."
            )

        existente = self.repository.buscar_por_identificador(
            session,
            dados.plataforma_divulgacao_id,
            identificador,
        )

        if existente is not None:
            raise ValueError(
                "Já existe um destino com esse identificador "
                "nessa plataforma de divulgação."
            )

        return self.repository.criar(
            session,
            plataforma_id=dados.plataforma_divulgacao_id,
            credencial_id=dados.credencial_divulgacao_id,
            identificador_destino=identificador,
            nome_destino=nome,
            status_destino=dados.status_destino,
        )

    def atualizar_status(
        self,
        session: Session,
        destino_id: int,
        status_destino: bool,
    ) -> DestinoDivulgacao:
        destino = self.repository.buscar_por_id(session, destino_id)

        if destino is None:
            raise LookupError(
                f"Destino de divulgação com ID {destino_id} não encontrado."
            )

        return self.repository.atualizar_status(
            session,
            destino,
            status_destino,
        )