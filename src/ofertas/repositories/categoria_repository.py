from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.plataforma_categoria_destino import PlataformaCategoriaDestino


class CategoriaRepository:
    """Centraliza o acesso aos dados das categorias."""

    def listar(
        self,
        session: Session,
        plataforma_id: int | None = None,
        somente_ativas: bool = False,
    ) -> list[PlataformaCategoria]:
        """Lista categorias, opcionalmente filtradas por plataforma."""
        consulta = select(PlataformaCategoria)

        if somente_ativas:
            consulta = consulta.where(
                PlataformaCategoria.status_categoria.is_(True)
            )

        if plataforma_id is not None:
            consulta = consulta.where(
                PlataformaCategoria.plataforma_id == plataforma_id
            )

        consulta = consulta.order_by(PlataformaCategoria.nome_categoria)

        return list(session.scalars(consulta).all())

    def listar_por_destino(
        self,
        session: Session,
        destino_id: int,
    ) -> list[PlataformaCategoria]:
        """Lista categorias ativas associadas a um destino."""

        consulta = (
            select(PlataformaCategoria)
            .join(
                PlataformaCategoriaDestino,
                PlataformaCategoriaDestino.categoria_id
                == PlataformaCategoria.id,
            )
            .where(
                PlataformaCategoriaDestino.destino_divulgacao_id
                == destino_id,
                PlataformaCategoria.status_categoria.is_(True),
            )
            .order_by(PlataformaCategoria.id)
        )

        return list(session.scalars(consulta).all())

    def listar_destinos(
        self,
        session: Session,
        categoria_id: int,
    ) -> list[DestinoDivulgacao]:
        """Lista os destinos completos associados a uma categoria."""

        consulta = (
            select(DestinoDivulgacao)
            .join(
                PlataformaCategoriaDestino,
                PlataformaCategoriaDestino.destino_divulgacao_id
                == DestinoDivulgacao.id,
            )
            .where(
                PlataformaCategoriaDestino.categoria_id == categoria_id
            )
            .order_by(DestinoDivulgacao.nome_destino)
        )

        return list(session.scalars(consulta).all())

    def listar_destinos_ids(
        self,
        session: Session,
        categoria_id: int,
    ) -> list[int]:
        """Lista os identificadores dos destinos associados à categoria."""

        consulta = (
            select(PlataformaCategoriaDestino.destino_divulgacao_id)
            .where(
                PlataformaCategoriaDestino.categoria_id == categoria_id
            )
            .order_by(PlataformaCategoriaDestino.destino_divulgacao_id)
        )

        return list(session.scalars(consulta).all())

    def associar_destino(
        self,
        session: Session,
        categoria_id: int,
        destino_id: int,
    ) -> PlataformaCategoriaDestino:
        """Cria a associação entre uma categoria e um destino."""

        associacao = session.get(
            PlataformaCategoriaDestino,
            (categoria_id, destino_id),
        )

        if associacao is not None:
            return associacao

        associacao = PlataformaCategoriaDestino(
            categoria_id=categoria_id,
            destino_divulgacao_id=destino_id,
        )
        session.add(associacao)
        session.flush()
        return associacao

    def desassociar_destino(
        self,
        session: Session,
        categoria_id: int,
        destino_id: int,
    ) -> bool:
        """Remove a associação entre uma categoria e um destino."""

        associacao = session.get(
            PlataformaCategoriaDestino,
            (categoria_id, destino_id),
        )

        if associacao is None:
            return False

        session.delete(associacao)
        session.flush()
        return True

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
        desconto_minimo_percentual: Decimal,
        etiqueta_afiliado: str | None = None,
        destino_divulgacao_id: int | None = None,
        status_categoria: bool = True,
    ) -> PlataformaCategoria:
        """Adiciona uma categoria à sessão atual."""
        categoria = PlataformaCategoria(
            plataforma_id=plataforma_id,
            id_categoria_plataforma=id_categoria_plataforma,
            nome_categoria=nome_categoria,
            desconto_minimo_percentual=desconto_minimo_percentual,
            etiqueta_afiliado=etiqueta_afiliado,
            destino_divulgacao_id=destino_divulgacao_id,
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

    def atualizar_desconto_minimo(
        self,
        session: Session,
        categoria: PlataformaCategoria,
        desconto_minimo_percentual: Decimal,
    ) -> PlataformaCategoria:
        """Atualiza o desconto mínimo de uma categoria."""
        categoria.desconto_minimo_percentual = desconto_minimo_percentual
        session.flush()
        return categoria

    def atualizar_etiqueta_afiliado(
        self,
        session: Session,
        categoria: PlataformaCategoria,
        etiqueta: str | None,
    ) -> PlataformaCategoria:
        """Atualiza a etiqueta de afiliado de uma categoria."""
        categoria.etiqueta_afiliado = etiqueta
        session.flush()
        return categoria

    def atualizar_destino_divulgacao(
        self,
        session: Session,
        categoria: PlataformaCategoria,
        destino_id: int | None,
    ) -> PlataformaCategoria:
        """Atualiza o destino de divulgação da categoria."""
        categoria.destino_divulgacao_id = destino_id
        session.flush()
        return categoria


    def atualizar_selecao(
        self,
        session: Session,
        categoria: PlataformaCategoria,
        *,
        limite_produtos_selecao: int,
        selecao_renovada_em,
    ) -> PlataformaCategoria:
        """Atualiza o limite e a data da seleção semanal."""
        categoria.limite_produtos_selecao = limite_produtos_selecao
        categoria.selecao_renovada_em = selecao_renovada_em

        session.flush()
        return categoria
