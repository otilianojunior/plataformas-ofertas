from sqlalchemy.orm import Session

from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.repositories.plataforma_divulgacao_repository import (
    PlataformaDivulgacaoRepository,
)
from ofertas.schemas.plataforma_divulgacao import PlataformaDivulgacaoCreate


class PlataformaDivulgacaoService:
    """Implementa as regras de negócio das plataformas de divulgação."""

    def __init__(
        self,
        repository: PlataformaDivulgacaoRepository | None = None,
    ) -> None:
        self.repository = repository or PlataformaDivulgacaoRepository()

    def listar(self, session: Session) -> list[PlataformaDivulgacao]:
        return self.repository.listar(session)

    def buscar_por_codigo(
        self,
        session: Session,
        codigo: str,
    ) -> PlataformaDivulgacao | None:
        return self.repository.buscar_por_codigo(session, codigo)

    def criar(
        self,
        session: Session,
        dados: PlataformaDivulgacaoCreate,
    ) -> PlataformaDivulgacao:
        codigo = dados.codigo.strip()
        nome = dados.nome.strip()

        if not codigo or not nome:
            raise ValueError("Código e nome não podem ficar vazios.")

        existente = self.repository.buscar_por_codigo(session, codigo)

        if existente is not None:
            raise ValueError(
                f"Já existe uma plataforma de divulgação com o código '{codigo}'."
            )

        return self.repository.criar(
            session,
            codigo=codigo,
            nome=nome,
            status_plataforma=dados.status_plataforma,
        )

    def atualizar_status(
        self,
        session: Session,
        codigo: str,
        ativo: bool,
    ) -> PlataformaDivulgacao:
        plataforma = self.repository.buscar_por_codigo(session, codigo)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de divulgação '{codigo}' não encontrada."
            )

        return self.repository.atualizar_status(
            session,
            plataforma,
            ativo,
        )
