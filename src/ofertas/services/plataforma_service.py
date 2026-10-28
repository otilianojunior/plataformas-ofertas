from sqlalchemy.orm import Session

from ofertas.models.plataforma import Plataforma
from ofertas.repositories import PlataformaRepository
from ofertas.schemas.plataforma import PlataformaCreate


class PlataformaService:
    """Implementa as regras de negócio das plataformas."""

    def __init__(self, repository: PlataformaRepository | None = None) -> None:
        self.repository = repository or PlataformaRepository()

    def listar(self, session: Session) -> list[Plataforma]:
        return self.repository.listar(session)

    def buscar_por_codigo(
        self,
        session: Session,
        codigo: str,
    ) -> Plataforma | None:
        return self.repository.buscar_por_codigo(session, codigo)

    def criar(
        self,
        session: Session,
        dados: PlataformaCreate,
    ) -> Plataforma:
        codigo = dados.codigo.strip()
        nome = dados.nome.strip()

        if not codigo or not nome:
            raise ValueError("Código e nome não podem ficar vazios.")

        existente = self.repository.buscar_por_codigo(session, codigo)

        if existente is not None:
            raise ValueError(f"Já existe uma plataforma com o código '{codigo}'.")

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
    ) -> Plataforma:
        plataforma = self.repository.buscar_por_codigo(session, codigo)

        if plataforma is None:
            raise LookupError(f"Plataforma '{codigo}' não encontrada.")

        return self.repository.atualizar_status(session, plataforma, ativo)
