from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, case, or_, select, update
from sqlalchemy.orm import Session

from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.produto import Produto
from ofertas.models.publicacao import Publicacao


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

    def listar_pendentes_para_geracao_afiliado(
        self,
        session: Session,
        plataforma_id: int,
        produto_ids: Sequence[int] | None = None,
    ) -> list[tuple[Produto, PlataformaCategoria | None]]:
        """Lista produtos pendentes e suas categorias."""

        consulta = (
            select(Produto, PlataformaCategoria)
            .outerjoin(
                PlataformaCategoria,
                (PlataformaCategoria.id == Produto.categoria_id)
                & (
                    PlataformaCategoria.plataforma_id
                    == Produto.plataforma_id
                ),
            )
            .where(
                Produto.plataforma_id == plataforma_id,
                Produto.status_link_afiliado.in_(("pendente", "erro")),
                Produto.url_afiliada.is_(None),
            )
            .order_by(Produto.created_at.asc(), Produto.id.asc())
        )

        if produto_ids is not None:
            consulta = consulta.where(Produto.id.in_(produto_ids))

        return [
            (produto, categoria)
            for produto, categoria in session.execute(consulta).all()
        ]

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


    def limpar_posicoes_selecao_categoria(
        self,
        session: Session,
        categoria_id: int,
    ) -> None:
        """Remove as posições anteriores da seleção da categoria."""

        session.execute(
            update(Produto)
            .where(Produto.categoria_id == categoria_id)
            .values(posicao_selecao_categoria=None)
            .execution_options(synchronize_session="fetch")
        )

        session.flush()

    def atualizar_posicoes_selecao_categoria(
        self,
        session: Session,
        categoria_id: int,
        posicoes: dict[int, int],
    ) -> None:
        """Atualiza as posições dos produtos selecionados na categoria."""

        self.limpar_posicoes_selecao_categoria(
            session,
            categoria_id,
        )

        if not posicoes:
            return

        consulta = (
            update(Produto)
            .where(
                Produto.categoria_id == categoria_id,
                Produto.id.in_(posicoes.keys()),
            )
            .values(
                posicao_selecao_categoria=case(
                    posicoes,
                    value=Produto.id,
                )
            )
            .execution_options(synchronize_session="fetch")
        )

        session.execute(consulta)
        session.flush()

    def listar_selecao_categoria(
        self,
        session: Session,
        categoria_id: int,
        limite: int | None = None,
    ) -> list[Produto]:
        """Lista os produtos selecionados na ordem de prioridade."""

        consulta = (
            select(Produto)
            .where(
                Produto.categoria_id == categoria_id,
                Produto.posicao_selecao_categoria.is_not(None),
            )
            .order_by(
                Produto.posicao_selecao_categoria.asc(),
                Produto.id.asc(),
            )
        )

        if limite is not None:
            consulta = consulta.limit(limite)

        return list(session.scalars(consulta).all())

    def listar_candidatos_publicacao(
        self,
        session: Session,
        *,
        categoria_id: int,
        destino_id: int,
        desconto_minimo_percentual: Decimal,
        preco_minimo: Decimal | None = None,
        preco_maximo: Decimal | None = None,
        limite: int = 10,
    ) -> list[Produto]:
        """Lista candidatos elegíveis para publicação em uma categoria."""

        if limite <= 0:
            return []

        agora = datetime.now(timezone.utc)
        limite_republicacao = agora - timedelta(hours=24)
        limite_tentativa = agora - timedelta(minutes=15)

        ultima_publicacao_em = (
            select(Publicacao.publicada_em)
            .where(
                Publicacao.produto_id == Produto.id,
                Publicacao.destino_divulgacao_id == destino_id,
                Publicacao.status_publicacao == "publicada",
            )
            .order_by(
                Publicacao.publicada_em.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
            .scalar_subquery()
        )

        ultimo_desconto_publicado = (
            select(Publicacao.percentual_desconto_divulgado)
            .where(
                Publicacao.produto_id == Produto.id,
                Publicacao.destino_divulgacao_id == destino_id,
                Publicacao.status_publicacao == "publicada",
            )
            .order_by(
                Publicacao.publicada_em.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
            .scalar_subquery()
        )

        ultima_tentativa_status = (
            select(Publicacao.status_publicacao)
            .where(
                Publicacao.produto_id == Produto.id,
                Publicacao.destino_divulgacao_id == destino_id,
            )
            .order_by(
                Publicacao.created_at.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
            .scalar_subquery()
        )

        ultima_tentativa_em = (
            select(Publicacao.updated_at)
            .where(
                Publicacao.produto_id == Produto.id,
                Publicacao.destino_divulgacao_id == destino_id,
            )
            .order_by(
                Publicacao.created_at.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
            .scalar_subquery()
        )

        ultima_tentativa_quantidade = (
            select(Publicacao.tentativas)
            .where(
                Publicacao.produto_id == Produto.id,
                Publicacao.destino_divulgacao_id == destino_id,
            )
            .order_by(
                Publicacao.created_at.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
            .scalar_subquery()
        )

        ultimo_desconto_tentativa = (
            select(Publicacao.percentual_desconto_divulgado)
            .where(
                Publicacao.produto_id == Produto.id,
                Publicacao.destino_divulgacao_id == destino_id,
            )
            .order_by(
                Publicacao.created_at.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
            .scalar_subquery()
        )

        pode_republicar = or_(
            ultima_publicacao_em.is_(None),
            ultima_publicacao_em <= limite_republicacao,
            and_(
                ultimo_desconto_publicado.is_not(None),
                Produto.percentual_desconto
                > ultimo_desconto_publicado,
            ),
        )

        tentativa_liberada = or_(
            ultima_tentativa_status.is_(None),
            ultima_tentativa_status == "publicada",
            and_(
                ultima_tentativa_status == "falhou",
                ultima_tentativa_quantidade < 3,
                ultima_tentativa_em <= limite_tentativa,
            ),
            and_(
                ultima_tentativa_status == "falhou",
                ultima_tentativa_quantidade >= 3,
                ultimo_desconto_tentativa.is_not(None),
                Produto.percentual_desconto
                > ultimo_desconto_tentativa,
            ),
        )

        consulta = select(Produto).where(
            Produto.categoria_id == categoria_id,
            Produto.disponivel.is_(True),
            Produto.status_monitoramento == "ativo",
            Produto.elegivel_divulgacao.is_(True),
            Produto.status_link_afiliado == "gerado",
            Produto.url_afiliada.is_not(None),
            Produto.percentual_desconto.is_not(None),
            Produto.percentual_desconto >= desconto_minimo_percentual,
            pode_republicar,
            tentativa_liberada,
        )

        if preco_minimo is not None:
            consulta = consulta.where(
                Produto.preco_atual >= preco_minimo
            )

        if preco_maximo is not None:
            consulta = consulta.where(
                Produto.preco_atual <= preco_maximo
            )

        consulta = (
            consulta
            .order_by(
                Produto.posicao_selecao_categoria.asc().nulls_last(),
                Produto.created_at.asc(),
                Produto.id.asc(),
            )
            .limit(limite)
        )

        return list(session.scalars(consulta).all())
