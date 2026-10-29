
from sqlalchemy.orm import Session

from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.repositories.categoria_repository import CategoriaRepository
from ofertas.schemas.categoria import CategoriaCreate


class CategoriaService:
    """Implementa as regras de negócio das categorias."""

    def __init__(
        self,
        repository: CategoriaRepository | None = None,
    ) -> None:
        self.repository = repository or CategoriaRepository()

    def listar(
        self,
        session: Session,
        plataforma_id: int | None = None,
    ) -> list[PlataformaCategoria]:
        return self.repository.listar(session, plataforma_id)

    def buscar_por_id(
        self,
        session: Session,
        categoria_id: int,
    ) -> PlataformaCategoria | None:
        return self.repository.buscar_por_id(session, categoria_id)

    def criar(
        self,
        session: Session,
        dados: CategoriaCreate,
    ) -> PlataformaCategoria:
        plataforma = session.get(Plataforma, dados.plataforma_id)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de ID '{dados.plataforma_id}' não encontrada."
            )

        id_externo = dados.id_categoria_plataforma.strip()
        nome = dados.nome_categoria.strip()

        if not id_externo or not nome:
            raise ValueError(
                "O identificador externo e o nome da categoria não podem ficar vazios."
            )

        existente = self.repository.buscar_por_id_externo(
            session,
            dados.plataforma_id,
            id_externo,
        )

        if existente is not None:
            raise ValueError(
                f"A categoria '{id_externo}' já está cadastrada nesta plataforma."
            )

        return self.repository.criar(
            session,
            plataforma_id=dados.plataforma_id,
            id_categoria_plataforma=id_externo,
            nome_categoria=nome,
            status_categoria=dados.status_categoria,
        )

    def atualizar_status(
        self,
        session: Session,
        categoria_id: int,
        ativo: bool,
    ) -> PlataformaCategoria:
        categoria = self.repository.buscar_por_id(session, categoria_id)

        if categoria is None:
            raise LookupError(
                f"Categoria de ID '{categoria_id}' não encontrada."
            )

        return self.repository.atualizar_status(session, categoria, ativo)
