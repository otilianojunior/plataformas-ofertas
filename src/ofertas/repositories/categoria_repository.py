
from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.plataforma_categoria import PlataformaCategoria


class CategoriaRepository:
    """Centraliza o acesso aos dados das categorias."""

    def listar(
        self,
        session: Session,
        plataforma_id: int | None = None,
    ) -> list[PlataformaCategoria]:
        """Lista categorias, opcionalmente filtradas por plataforma."""
        consulta = select(PlataformaCategoria)

        if plataforma_id is not None:
            consulta = consulta.where(
                PlataformaCategoria.plataforma_id == plataforma_id
            )

        consulta = consulta.order_by(PlataformaCategoria.nome_categoria)

        return list(session.scalars(consulta).all())

    def buscar_por_id(
        self,
        session: Session,
        categoria_id: int,
    ) -> PlataformaCategoria | None:
        """Busca uma categoria pelo identificador interno."""
        return session.get(PlataformaCategoria, categoria_id)

    def buscar_por_id_externo(
        self,
        session: Session,
        plataforma_id: int,
        id_categoria_plataforma: str,
    ) -> PlataformaCategoria | None:
        """Busca uma categoria pelo ID externo dentro da plataforma."""
        consulta = select(PlataformaCategoria).where(
            PlataformaCategoria.plataforma_id == plataforma_id,
            PlataformaCategoria.id_categoria_plataforma
            == id_categoria_plataforma,
        )
        return session.scalars(consulta).one_or_none()

    def criar(
        self,
        session: Session,
        *,
        plataforma_id: int,
        id_categoria_plataforma: str,
        nome_categoria: str,
        status_categoria: bool = True,
    ) -> PlataformaCategoria:
        """Adiciona uma categoria à sessão atual."""
        categoria = PlataformaCategoria(
            plataforma_id=plataforma_id,
            id_categoria_plataforma=id_categoria_plataforma,
            nome_categoria=nome_categoria,
            status_categoria=status_categoria,
        )
        session.add(categoria)
        session.flush()
        return categoria

    def atualizar_status(
        self,
        session: Session,
        categoria: PlataformaCategoria,
        ativo: bool,
    ) -> PlataformaCategoria:
        """Atualiza o status de uma categoria."""
        categoria.status_categoria = ativo
        session.flush()
        return categoria
