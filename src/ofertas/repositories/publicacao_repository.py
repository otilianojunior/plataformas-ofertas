from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ofertas.models.publicacao import Publicacao


class PublicacaoRepository:
    """Centraliza o acesso aos registros de publicação."""

    def buscar_ativa(
        self,
        session: Session,
        produto_id: int,
        destino_id: int,
    ) -> Publicacao | None:
        """Busca uma publicação ainda pendente."""

        consulta = select(Publicacao).where(
            Publicacao.produto_id == produto_id,
            Publicacao.destino_divulgacao_id == destino_id,
            Publicacao.status_publicacao == "pendente",
        )

        return session.scalars(consulta).one_or_none()

    def buscar_ultima(
        self,
        session: Session,
        produto_id: int,
        destino_id: int,
    ) -> Publicacao | None:
        """Busca o registro mais recente do produto no destino."""

        consulta = (
            select(Publicacao)
            .where(
                Publicacao.produto_id == produto_id,
                Publicacao.destino_divulgacao_id == destino_id,
            )
            .order_by(
                Publicacao.created_at.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
        )

        return session.scalars(consulta).first()


    def buscar_ultima_publicada_produto_destino(
        self,
        session: Session,
        produto_id: int,
        destino_id: int,
    ) -> Publicacao | None:
        """Busca a última publicação bem-sucedida do produto no destino."""

        consulta = (
            select(Publicacao)
            .where(
                Publicacao.produto_id == produto_id,
                Publicacao.destino_divulgacao_id == destino_id,
                Publicacao.status_publicacao == "publicada",
            )
            .order_by(
                Publicacao.publicada_em.desc(),
                Publicacao.id.desc(),
            )
            .limit(1)
        )

        return session.scalars(consulta).first()


    def criar(
        self,
        session: Session,
        *,
        produto_id: int,
        destino_id: int,
        preco_divulgado: Decimal,
        percentual_desconto_divulgado: Decimal | None = None,
        tentativas: int = 1,
    ) -> Publicacao:
        """Registra uma nova publicação."""

        publicacao = Publicacao(
            produto_id=produto_id,
            destino_divulgacao_id=destino_id,
            preco_divulgado=preco_divulgado,
            percentual_desconto_divulgado=(
                percentual_desconto_divulgado
            ),
            status_publicacao="pendente",
            tentativas=tentativas,
        )

        session.add(publicacao)
        session.flush()

        return publicacao

    def preparar_nova_tentativa(
        self,
        session: Session,
        publicacao: Publicacao,
        *,
        preco_divulgado: Decimal,
        percentual_desconto_divulgado: Decimal | None,
    ) -> Publicacao:
        """Reabre uma publicação com falha para uma nova tentativa."""

        publicacao.status_publicacao = "pendente"
        publicacao.tentativas += 1
        publicacao.preco_divulgado = preco_divulgado
        publicacao.percentual_desconto_divulgado = (
            percentual_desconto_divulgado
        )
        publicacao.erro = None
        publicacao.publicada_em = None

        session.flush()
        return publicacao
