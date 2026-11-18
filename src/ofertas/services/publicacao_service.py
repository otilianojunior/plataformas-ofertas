import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.models.configuracao_divulgacao import ConfiguracaoDivulgacao
from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.models.plataforma_categoria import PlataformaCategoria
from ofertas.models.produto import Produto
from ofertas.models.publicacao import Publicacao
from ofertas.publishers.mensagem import formatar_preco
from ofertas.publishers.base import PublisherBase
from ofertas.publishers.telegram import TelegramPublisher
from ofertas.publishers.whatsapp import WhatsAppPublisher
from ofertas.repositories.categoria_repository import CategoriaRepository
from ofertas.repositories.configuracao_divulgacao_repository import (
    ConfiguracaoDivulgacaoRepository,
)
from ofertas.repositories.produto_repository import ProdutoRepository
from ofertas.schemas.publicacao import PublicacaoResponse
from ofertas.core.elegibilidade import desconto_plausivel
from ofertas.core.similaridade_produto import bloqueio_republicacao
from ofertas.repositories.publicacao_repository import (
    PublicacaoRepository,
)


logger = logging.getLogger(__name__)


class PublicacaoService:
    """Coordena a publicação e aplica as regras de negócio."""

    INTERVALO_REPUBLICACAO_HORAS = 24
    INTERVALO_NOVA_TENTATIVA_MINUTOS = 15
    MAX_TENTATIVAS = 3

    def __init__(
        self,
        produto_repository: ProdutoRepository | None = None,
        categoria_repository: CategoriaRepository | None = None,
        publicacao_repository: PublicacaoRepository | None = None,
        configuracao_repository: ConfiguracaoDivulgacaoRepository | None = None,
        telegram_publisher: TelegramPublisher | None = None,
        whatsapp_publisher: WhatsAppPublisher | None = None,
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
        self.configuracao_repository = (
            configuracao_repository or ConfiguracaoDivulgacaoRepository()
        )
        self.telegram_publisher = (
            telegram_publisher or TelegramPublisher()
        )
        self.whatsapp_publisher = (
            whatsapp_publisher or WhatsAppPublisher()
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

        return categoria

    def _validar_destino(
        self,
        session: Session,
        categoria: PlataformaCategoria,
        destino_id: int,
    ) -> int:
        """Valida que o grupo existe, está ativo e pertence à categoria."""

        destinos_ids = self.categoria_repository.listar_destinos_ids(
            session,
            categoria.id,
        )

        if (
            destino_id not in destinos_ids
            and session.get(DestinoDivulgacao, destino_id) is None
        ):
            raise LookupError("Destino de divulgação não encontrado.")

        if destino_id not in destinos_ids:
            raise ValueError(
                "O destino informado não está associado à categoria do produto."
            )

        destino = session.get(DestinoDivulgacao, destino_id)

        if destino is None:
            raise LookupError("Destino de divulgação não encontrado.")

        if not destino.status_destino:
            raise ValueError("O destino de divulgação está inativo.")

        plataforma = session.get(
            PlataformaDivulgacao,
            destino.plataforma_divulgacao_id,
        )

        if plataforma is None:
            raise LookupError("Canal de divulgação não encontrado.")

        if not plataforma.status_plataforma:
            raise ValueError("O canal de divulgação está inativo.")

        self._publisher_do_canal(plataforma.codigo)

        return destino_id

    def _publisher_do_canal(self, codigo_canal: str) -> PublisherBase:
        publishers = {
            TelegramPublisher.CODIGO_CANAL: self.telegram_publisher,
            WhatsAppPublisher.CODIGO_CANAL: self.whatsapp_publisher,
        }

        publisher = publishers.get(codigo_canal.lower())

        if publisher is None:
            raise ValueError(
                f"Não há publicador para o canal '{codigo_canal}'."
            )

        return publisher

    def _validar_elegibilidade(
        self,
        produto: Produto,
        categoria: PlataformaCategoria,
        configuracao: ConfiguracaoDivulgacao,
    ) -> None:
        if not produto.elegivel_divulgacao:
            raise ValueError(
                "O produto não está marcado como elegível para divulgação."
            )

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

        desconto_minimo = max(
            categoria.desconto_minimo_percentual,
            configuracao.desconto_minimo_percentual,
        )

        if produto.percentual_desconto < desconto_minimo:
            raise ValueError(
                "O desconto do produto está abaixo do mínimo exigido "
                "pela categoria ou pelo destino."
            )

        if not desconto_plausivel(produto.percentual_desconto):
            raise ValueError(
                f"Desconto de {produto.percentual_desconto}% acima do teto "
                f"(DESCONTO_MAXIMO_PERCENTUAL): provável preço original "
                f"inflado pela loja."
            )

        if (
            configuracao.preco_minimo is not None
            and produto.preco_atual < configuracao.preco_minimo
        ):
            raise ValueError(
                "O preço do produto está abaixo do mínimo configurado "
                "para este destino."
            )

        if (
            configuracao.preco_maximo is not None
            and produto.preco_atual > configuracao.preco_maximo
        ):
            raise ValueError(
                "O preço do produto está acima do máximo configurado "
                "para este destino."
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
        session: Session,
        produto: Produto,
        destino_id: int,
        agora: datetime,
    ) -> None:
        """Mesmo produto (de qualquer loja) só volta em 24h com preço menor."""

        recentes = self.publicacao_repository.listar_publicadas_recentes(
            session,
            destino_id,
            agora - timedelta(hours=self.INTERVALO_REPUBLICACAO_HORAS),
        )

        bloqueio = bloqueio_republicacao(
            produto.id,
            produto.titulo,
            produto.preco_atual,
            recentes,
        )

        if bloqueio is not None:
            raise ValueError(
                "Um produto igual já foi publicado neste grupo há menos de "
                f"24 horas por {formatar_preco(bloqueio.preco)} "
                f"({bloqueio.loja}: {bloqueio.titulo[:80]}). "
                "Só pode ser publicado de novo com preço menor."
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
        destino_id: int,
    ) -> Publicacao:
        """Publica um produto em um destino associado à sua categoria."""

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

        self._validar_destino(
            session,
            categoria,
            destino_id,
        )

        configuracao = self.configuracao_repository.buscar_por_destino(
            session,
            destino_id,
        )

        if configuracao is None:
            raise ValueError(
                "O destino não possui configuração de divulgação."
            )

        if not configuracao.status_configuracao:
            raise ValueError(
                "A configuração de divulgação deste destino está inativa."
            )

        self._validar_elegibilidade(
            produto,
            categoria,
            configuracao,
        )

        agora = datetime.now(timezone.utc)

        self._validar_republicacao(
            session,
            produto,
            destino_id,
            agora,
        )

        publicacao = self._preparar_publicacao(
            session,
            produto,
            destino_id,
        )

        destino = session.get(DestinoDivulgacao, destino_id)
        canal = session.get(
            PlataformaDivulgacao,
            destino.plataforma_divulgacao_id,
        )

        return self._publisher_do_canal(canal.codigo).publicar(
            session,
            produto,
            destino_id,
            publicacao=publicacao,
        )

    def publicar_em_todos_destinos(
        self,
        session: Session,
        produto_id: int,
    ) -> dict:
        """Publica o produto em todos os grupos ativos da sua categoria.

        Cada grupo passa por todas as validações de publicar_produto
        (elegibilidade, link afiliado, desconto, faixa de preço,
        republicação e tentativas). O resultado de cada grupo é
        confirmado (commit) logo após o envio, para que uma falha em um
        grupo não desfaça o registro de uma mensagem já enviada a outro.
        """

        produto = self.produto_repository.buscar_por_id(
            session,
            produto_id,
        )

        if produto is None:
            raise LookupError(
                f"Produto de ID '{produto_id}' não encontrado."
            )

        categoria = self._buscar_categoria(session, produto)
        categoria_id = categoria.id
        nome_categoria = categoria.nome_categoria

        destinos_ids = self.categoria_repository.listar_destinos_ids(
            session,
            categoria_id,
        )

        if not destinos_ids:
            raise ValueError(
                "A categoria do produto não possui grupos associados."
            )

        resultados = []

        for destino_id in destinos_ids:
            destino = session.get(DestinoDivulgacao, destino_id)
            canal = (
                session.get(
                    PlataformaDivulgacao,
                    destino.plataforma_divulgacao_id,
                )
                if destino is not None
                else None
            )

            resultado = {
                "destino_id": destino_id,
                "nome_destino": (
                    destino.nome_destino if destino is not None else "?"
                ),
                "codigo_canal": canal.codigo if canal is not None else "?",
                "status": "ignorada",
                "motivo": None,
                "publicacao": None,
            }
            resultados.append(resultado)

            if destino is None or canal is None:
                resultado["motivo"] = "Grupo ou canal não encontrado."
                continue

            if not canal.status_plataforma:
                resultado["motivo"] = "O canal de divulgação está inativo."
                continue

            if not destino.status_destino:
                resultado["motivo"] = "O grupo está inativo."
                continue

            try:
                publicacao = self.publicar_produto(
                    session,
                    produto_id,
                    destino_id=destino_id,
                )
                session.commit()
                session.refresh(publicacao)

            except (ValueError, LookupError) as erro:
                session.rollback()
                resultado["motivo"] = str(erro)
                continue

            except IntegrityError:
                session.rollback()
                resultado["motivo"] = (
                    "Publicação simultânea em andamento para este grupo."
                )
                continue

            except Exception as erro:
                session.rollback()
                logger.exception(
                    "Erro inesperado na publicação manual do produto %s "
                    "no destino %s.",
                    produto_id,
                    destino_id,
                )
                resultado["status"] = "falhou"
                resultado["motivo"] = f"{type(erro).__name__}: {erro}"
                continue

            # Copia os dados já confirmados: um rollback de outro grupo
            # expiraria o objeto ORM antes da serialização da resposta.
            resultado["publicacao"] = PublicacaoResponse.model_validate(
                publicacao
            )

            if publicacao.status_publicacao == "publicada":
                resultado["status"] = "publicada"
            else:
                resultado["status"] = "falhou"
                resultado["motivo"] = publicacao.erro

        def contar(status: str) -> int:
            return sum(1 for r in resultados if r["status"] == status)

        return {
            "produto_id": produto_id,
            "categoria_id": categoria_id,
            "nome_categoria": nome_categoria,
            "total_destinos": len(resultados),
            "publicadas": contar("publicada"),
            "falhas": contar("falhou"),
            "ignoradas": contar("ignorada"),
            "resultados": resultados,
        }
