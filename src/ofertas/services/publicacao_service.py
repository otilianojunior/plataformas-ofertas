
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.produto import Produto
from ofertas.models.publicacao import Publicacao
from ofertas.publishers.telegram import TelegramPublisher
from ofertas.repositories.categoria_repository import CategoriaRepository
from ofertas.repositories.produto_repository import ProdutoRepository
from ofertas.repositories.publicacao_repository import (
    PublicacaoRepository,
)


class PublicacaoService:
    """Coordena a publicação e aplica as regras de negócio."""

    INTERVALO_REPUBLICACAO_HORAS = 24
    INTERVALO_ENTRE_PUBLICACOES_MINUTOS = 30
    LIMITE_PUBLICACOES_24_HORAS = 12
    INTERVALO_NOVA_TENTATIVA_MINUTOS = 15
    MAX_TENTATIVAS = 3

    def __init__(
        self,
        produto_repository: ProdutoRepository | None = None,
        categoria_repository: CategoriaRepository | None = None,
        publicacao_repository: PublicacaoRepository | None = None,
        telegram_publisher: TelegramPublisher | None = None,
    ) -> None:
        self.produto_repository = (
            produto_repository or ProdutoRepository()
        )
        self.categoria_repository = (
            categoria_repository or CategoriaRepository()
        )
        self.publicacao_repository = (
            publicacao_repository or PublicacaoRepository()
        )
        self.telegram_publisher = (
            telegram_publisher or TelegramPublisher()
        )

    def _buscar_categoria(
        self,
        session: Session,
        produto: Produto,
    ) -> PlataformaCategoria:
        if produto.categoria_id is None:
            raise ValueError(
                "O produto não possui uma categoria associada."
            )

        categoria = self.categoria_repository.buscar_por_id(
            session,
            produto.categoria_id,
        )

        if categoria is None:
            raise LookupError(
                "A categoria associada ao produto não foi encontrada."
            )

        if categoria.plataforma_id != produto.plataforma_id:
            raise ValueError(
                "A categoria não pertence à plataforma do produto."
            )

        if not categoria.status_categoria:
            raise ValueError(
                "A categoria está inativa e não pode ser divulgada."
            )

        if categoria.destino_divulgacao_id is None:
            raise ValueError(
                "A categoria não possui um destino de divulgação associado."
            )

        return categoria

    def _validar_elegibilidade(
        self,
        produto: Produto,
        categoria: PlataformaCategoria,
    ) -> None:
        if not produto.disponivel:
            raise ValueError(
                "O produto está indisponível."
            )

        if produto.status_monitoramento != "ativo":
            raise ValueError(
                "O monitoramento do produto não está ativo."
            )

        if (
            produto.status_link_afiliado != "gerado"
            or not produto.url_afiliada
        ):
            raise ValueError(
                "O produto não possui um link afiliado válido."
            )

        if produto.percentual_desconto is None:
            raise ValueError(
                "O produto não possui percentual de desconto calculado."
            )

        if (
            produto.percentual_desconto
            < categoria.desconto_minimo_percentual
        ):
            raise ValueError(
                "O desconto do produto está abaixo do mínimo da categoria."
            )

    def _desconto_aumentou(
        self,
        produto: Produto,
        ultima_publicacao: Publicacao,
    ) -> bool:
        desconto_anterior = (
            ultima_publicacao.percentual_desconto_divulgado
        )

        return (
            desconto_anterior is not None
            and produto.percentual_desconto is not None
            and produto.percentual_desconto > desconto_anterior
        )

    def _validar_republicacao(
        self,
        produto: Produto,
        ultima_publicacao: Publicacao | None,
        agora: datetime,
    ) -> None:
        if ultima_publicacao is None:
            return

        horario = (
            ultima_publicacao.publicada_em
            or ultima_publicacao.created_at
        )

        intervalo = timedelta(
            hours=self.INTERVALO_REPUBLICACAO_HORAS
        )

        if agora - horario >= intervalo:
            return

        if self._desconto_aumentou(produto, ultima_publicacao):
            return

        raise ValueError(
            "O produto já foi publicado neste grupo há menos de "
            "24 horas e não apresentou aumento no desconto."
        )

    def _validar_limites_destino(
        self,
        session: Session,
        destino_id: int,
        agora: datetime,
    ) -> None:
        ultima_publicacao = (
            self.publicacao_repository.buscar_ultima_publicada_destino(
                session,
                destino_id,
            )
        )

        if ultima_publicacao is not None:
            horario = (
                ultima_publicacao.publicada_em
                or ultima_publicacao.created_at
            )

            intervalo_minimo = timedelta(
                minutes=self.INTERVALO_ENTRE_PUBLICACOES_MINUTOS
            )

            if agora - horario < intervalo_minimo:
                raise ValueError(
                    "O grupo ainda está dentro do intervalo mínimo "
                    "entre publicações de 30 minutos."
                )

        inicio_periodo = agora - timedelta(hours=24)

        quantidade = (
            self.publicacao_repository.contar_publicadas_desde(
                session,
                destino_id,
                inicio_periodo,
            )
        )

        if quantidade >= self.LIMITE_PUBLICACOES_24_HORAS:
            raise ValueError(
                "O grupo atingiu o limite de 12 publicações "
                "nas últimas 24 horas."
            )

    def _preparar_publicacao(
        self,
        session: Session,
        produto: Produto,
        destino_id: int,
    ) -> Publicacao | None:
        ultima_tentativa = self.publicacao_repository.buscar_ultima(
            session,
            produto.id,
            destino_id,
        )

        if ultima_tentativa is None:
            return None

        if ultima_tentativa.status_publicacao == "pendente":
            raise ValueError(
                "Já existe uma publicação pendente para este produto "
                "neste grupo."
            )

        if ultima_tentativa.status_publicacao != "falhou":
            return None

        if ultima_tentativa.tentativas >= self.MAX_TENTATIVAS:
            # Uma nova queda no desconto inicia uma nova oportunidade.
            if not self._desconto_aumentou(
                produto,
                ultima_tentativa,
            ):
                raise ValueError(
                    "O produto atingiu o limite de três tentativas "
                    "para esta oportunidade."
                )

            return None

        referencia = (
            ultima_tentativa.updated_at
            or ultima_tentativa.created_at
        )

        intervalo = timedelta(
            minutes=self.INTERVALO_NOVA_TENTATIVA_MINUTOS
        )

        if datetime.now(timezone.utc) - referencia < intervalo:
            raise ValueError(
                "A próxima tentativa de publicação estará disponível "
                "após 15 minutos."
            )

        return self.publicacao_repository.preparar_nova_tentativa(
            session,
            ultima_tentativa,
            preco_divulgado=produto.preco_atual,
            percentual_desconto_divulgado=(
                produto.percentual_desconto
            ),
        )

    def publicar_produto(
        self,
        session: Session,
        produto_id: int,
    ) -> Publicacao:
        """Publica um produto no grupo associado à sua categoria."""

        produto = self.produto_repository.buscar_por_id(
            session,
            produto_id,
        )

        if produto is None:
            raise LookupError(
                f"Produto de ID '{produto_id}' não encontrado."
            )

        categoria = self._buscar_categoria(
            session,
            produto,
        )

        self._validar_elegibilidade(
            produto,
            categoria,
        )

        destino_id = categoria.destino_divulgacao_id

        agora = datetime.now(timezone.utc)

        ultima_publicacao = (
            self.publicacao_repository.buscar_ultima_publicada_produto_destino(
                session,
                produto.id,
                destino_id,
            )
        )

        self._validar_republicacao(
            produto,
            ultima_publicacao,
            agora,
        )

        self._validar_limites_destino(
            session,
            destino_id,
            agora,
        )

        publicacao = self._preparar_publicacao(
            session,
            produto,
            destino_id,
        )

        return self.telegram_publisher.publicar(
            session,
            produto,
            destino_id,
            publicacao=publicacao,
        )
