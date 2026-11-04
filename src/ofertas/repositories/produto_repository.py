
from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.produto import Produto


class ProdutoRepository:
    """Centraliza o acesso aos dados dos produtos."""

    def listar(self, session: Session) -> list[Produto]:
        consulta = select(Produto).order_by(
            Produto.created_at.desc(),
            Produto.id.desc(),
        )
        return list(session.scalars(consulta).all())

    def buscar_por_id(
        self,
        session: Session,
        produto_id: int,
    ) -> Produto | None:
        consulta = select(Produto).where(Produto.id == produto_id)
        return session.scalars(consulta).one_or_none()

    def buscar_por_item(
        self,
        session: Session,
        plataforma_id: int,
        id_item_plataforma: str,
    ) -> Produto | None:
        consulta = select(Produto).where(
            Produto.plataforma_id == plataforma_id,
            Produto.id_item_plataforma == id_item_plataforma,
        )
        return session.scalars(consulta).one_or_none()

    def criar(self, session: Session, dados: dict) -> Produto:
        produto = Produto(**dados)
        session.add(produto)
        session.flush()
        return produto

    def atualizar_coleta(
        self,
        session: Session,
        produto: Produto,
        dados: dict,
    ) -> Produto:
        campos_protegidos = {
            "id",
            "plataforma_id",
            "id_item_plataforma",
            "url_afiliada",
            "status_link_afiliado",
            "metodo_geracao_link_afiliado",
            "identificador_rastreamento",
            "erro_geracao_link_afiliado",
            "link_afiliado_gerado_em",
            "primeira_coleta_em",
            "created_at",
        }

        for campo, valor in dados.items():
            if campo not in campos_protegidos and hasattr(produto, campo):
                setattr(produto, campo, valor)

        session.flush()
        return produto
