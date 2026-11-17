import logging
import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ofertas.db.session import SessionLocal, engine
from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.models.plataforma import Plataforma
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.repositories.categoria_repository import CategoriaRepository
from ofertas.repositories.configuracao_divulgacao_repository import (
    ConfiguracaoDivulgacaoRepository,
)
from ofertas.repositories.destino_divulgacao_repository import (
    DestinoDivulgacaoRepository,
)
from ofertas.repositories.ciclo_publicacao_repository import (
    CicloPublicacaoRepository,
)
from ofertas.repositories.produto_repository import ProdutoRepository
from ofertas.services.publicacao_service import PublicacaoService
from ofertas.services.janela_execucao_service import (
    JanelaExecucaoService,
)


logger = logging.getLogger(__name__)


class PublicacaoLoteService:
    """Coordena os ciclos automáticos de publicação por destino."""

    LOCK_NAMESPACE = 20261110
    INTERVALO_ENTRE_MENSAGENS_SEGUNDOS = 20
    CODIGO_TELEGRAM = "telegram"

    def __init__(
        self,
        configuracao_repository: ConfiguracaoDivulgacaoRepository | None = None,
        destino_repository: DestinoDivulgacaoRepository | None = None,
        categoria_repository: CategoriaRepository | None = None,
        produto_repository: ProdutoRepository | None = None,
        publicacao_service: PublicacaoService | None = None,
        janela_execucao_service: JanelaExecucaoService | None = None,
        ciclo_repository: CicloPublicacaoRepository | None = None,
    ) -> None:
        self.configuracao_repository = (
            configuracao_repository or ConfiguracaoDivulgacaoRepository()
        )
        self.destino_repository = (
            destino_repository or DestinoDivulgacaoRepository()
        )
        self.categoria_repository = (
            categoria_repository or CategoriaRepository()
        )
        self.produto_repository = (
            produto_repository or ProdutoRepository()
        )
        self.publicacao_service = (
            publicacao_service or PublicacaoService()
        )
        self.janela_execucao_service = (
            janela_execucao_service or JanelaExecucaoService()
        )
        self.ciclo_repository = (
            ciclo_repository or CicloPublicacaoRepository()
        )

    def _buscar_configuracao_ativa(
        self,
        session: Session,
        destino_id: int,
    ):
        configuracao = self.configuracao_repository.buscar_por_destino(
            session,
            destino_id,
        )

        if configuracao is None or not configuracao.status_configuracao:
            return None

        destino = self.destino_repository.buscar_por_id(
            session,
            destino_id,
        )

        if destino is None or not destino.status_destino:
            return None

        plataforma_destino = session.get(
            PlataformaDivulgacao,
            destino.plataforma_divulgacao_id,
        )

        if (
            plataforma_destino is None
            or not plataforma_destino.status_plataforma
            or plataforma_destino.codigo != self.CODIGO_TELEGRAM
        ):
            return None

        configuracao_sistema = session.get(
            ConfiguracaoSistema,
            1,
        )

        if (
            configuracao_sistema is None
            or not configuracao_sistema.automacoes_ativas
            or not configuracao_sistema.publicacao_telegram_ativa
        ):
            return None

        if not self.janela_execucao_service.esta_em_horario_permitido(
            session
        ):
            return None

        return configuracao

    def _selecionar_candidatos(
        self,
        session: Session,
        destino_id: int,
    ) -> list[tuple[int, str, int]]:
        configuracao = self.configuracao_repository.buscar_por_destino(
            session,
            destino_id,
        )

        if configuracao is None:
            return []

        configuracao_sistema = session.get(ConfiguracaoSistema, 1)

        if configuracao_sistema is None:
            return []

        limite_produtos_por_categoria = (
            configuracao_sistema.limite_produtos_por_categoria
        )

        categorias = self.categoria_repository.listar_por_destino(
            session,
            destino_id,
        )

        candidatos = []

        for categoria in categorias:
            plataforma = session.get(
                Plataforma,
                categoria.plataforma_id,
            )

            if (
                plataforma is None
                or not plataforma.status_plataforma
            ):
                continue

            desconto_minimo = max(
                categoria.desconto_minimo_percentual,
                configuracao.desconto_minimo_percentual,
            )

            produtos = self.produto_repository.listar_candidatos_publicacao(
                session,
                categoria_id=categoria.id,
                destino_id=destino_id,
                desconto_minimo_percentual=desconto_minimo,
                preco_minimo=configuracao.preco_minimo,
                preco_maximo=configuracao.preco_maximo,
                limite=limite_produtos_por_categoria,
            )

            for produto in produtos:
                candidatos.append(
                    (
                        categoria.id,
                        categoria.nome_categoria,
                        produto.id,
                    )
                )

        return candidatos

    def _registrar_execucao(self, destino_id: int) -> None:
        with SessionLocal() as session:
            configuracao = (
                self.configuracao_repository.buscar_por_destino(
                    session,
                    destino_id,
                )
            )

            if configuracao is None:
                return

            self.configuracao_repository.registrar_execucao(
                session,
                configuracao,
                datetime.now(timezone.utc),
            )
            session.commit()

    def executar_ciclo_destino(
        self,
        destino_id: int,
    ) -> dict[str, int | str]:
        """Executa um ciclo com exclusividade por destino no PostgreSQL."""

        parametros = {
            "namespace": self.LOCK_NAMESPACE,
            "destino_id": destino_id,
        }

        with engine.connect() as conexao_lock:
            lock_adquirido = False

            try:
                lock_adquirido = bool(
                    conexao_lock.execute(
                        text(
                            "SELECT pg_try_advisory_lock("
                            ":namespace, :destino_id)"
                        ),
                        parametros,
                    ).scalar_one()
                )
                conexao_lock.commit()

                if not lock_adquirido:
                    logger.info(
                        "Ciclo do destino %s não iniciado: "
                        "já existe outro ciclo em execução.",
                        destino_id,
                    )
                    return {
                        "status": "ja_em_execucao",
                        "destino_id": destino_id,
                        "candidatos": 0,
                        "publicadas": 0,
                        "falhas": 0,
                        "ignoradas": 0,
                    }

                return self._executar_ciclo_destino_com_lock(destino_id)

            finally:
                if lock_adquirido:
                    try:
                        liberado = conexao_lock.execute(
                            text(
                                "SELECT pg_advisory_unlock("
                                ":namespace, :destino_id)"
                            ),
                            parametros,
                        ).scalar_one()
                        conexao_lock.commit()

                        if not liberado:
                            logger.error(
                                "O lock do destino %s já não estava adquirido.",
                                destino_id,
                            )

                    except Exception:
                        logger.exception(
                            "Falha ao liberar o lock do destino %s. "
                            "A conexão será descartada.",
                            destino_id,
                        )
                        conexao_lock.invalidate()

    def _executar_ciclo_destino_com_lock(
        self,
        destino_id: int,
    ) -> dict[str, int | str]:
        """Executa o lote enquanto o bloqueio exclusivo está adquirido."""

        with SessionLocal() as session:
            configuracao = self._buscar_configuracao_ativa(
                session,
                destino_id,
            )

            if configuracao is None:
                return {
                    "status": "pausado",
                    "destino_id": destino_id,
                    "candidatos": 0,
                    "publicadas": 0,
                    "falhas": 0,
                    "ignoradas": 0,
                }

            candidatos = self._selecionar_candidatos(
                session,
                destino_id,
            )

            # Com o lock do destino, ciclos ainda "em andamento" são restos
            # de uma execução encerrada no meio (ex.: API reiniciada).
            self.ciclo_repository.marcar_interrompidos(
                session,
                destino_id,
            )
            ciclo = self.ciclo_repository.iniciar(
                session,
                destino_id,
                len(candidatos),
            )
            session.commit()
            ciclo_id = ciclo.id

        try:
            resultado = self._publicar_candidatos(
                destino_id,
                candidatos,
                ciclo_id,
            )
        except Exception as erro:
            self._finalizar_ciclo(
                ciclo_id,
                "falhou",
                erro=f"{type(erro).__name__}: {erro}",
            )
            raise

        self._finalizar_ciclo(
            ciclo_id,
            resultado["status"],
            quantidade_publicada=resultado["publicadas"],
            quantidade_falha=resultado["falhas"],
            quantidade_ignorada=resultado["ignoradas"],
        )

        return resultado

    def _atualizar_ciclo(self, ciclo_id: int | None, **valores) -> None:
        """Persiste o progresso do ciclo sem interromper a publicação."""

        if ciclo_id is None:
            return

        try:
            with SessionLocal() as session:
                self.ciclo_repository.atualizar(
                    session,
                    ciclo_id,
                    **valores,
                )
                session.commit()
        except Exception:
            logger.exception(
                "Falha ao registrar o andamento do ciclo %s.",
                ciclo_id,
            )

    def _finalizar_ciclo(
        self,
        ciclo_id: int | None,
        status: str,
        **valores,
    ) -> None:
        self._atualizar_ciclo(
            ciclo_id,
            status=status,
            finalizado_em=datetime.now(timezone.utc),
            **valores,
        )

    def _publicar_candidatos(
        self,
        destino_id: int,
        candidatos: list[tuple[int, str, int]],
        ciclo_id: int | None,
    ) -> dict[str, int | str]:
        """Envia os candidatos respeitando pausas, janelas e intervalos."""

        publicadas = 0
        falhas = 0
        ignoradas = 0
        ultima_mensagem_em = None
        status_ciclo = "concluido"

        for indice, (categoria_id, nome_categoria, produto_id) in enumerate(
            candidatos
        ):
            if indice > 0:
                self._atualizar_ciclo(
                    ciclo_id,
                    quantidade_publicada=publicadas,
                    quantidade_falha=falhas,
                    quantidade_ignorada=ignoradas,
                )

            if ultima_mensagem_em is not None:
                with SessionLocal() as session:
                    configuracao = self._buscar_configuracao_ativa(
                        session,
                        destino_id,
                    )

                if configuracao is None:
                    status_ciclo = "pausado"
                    break

                tempo_decorrido = time.monotonic() - ultima_mensagem_em
                tempo_restante = (
                    self.INTERVALO_ENTRE_MENSAGENS_SEGUNDOS
                    - tempo_decorrido
                )

                if tempo_restante > 0:
                    time.sleep(tempo_restante)

            with SessionLocal() as session:
                if self._buscar_configuracao_ativa(
                    session,
                    destino_id,
                ) is None:
                    status_ciclo = "pausado"
                    break

                try:
                    publicacao = self.publicacao_service.publicar_produto(
                        session,
                        produto_id,
                        destino_id=destino_id,
                    )

                    session.commit()

                    if publicacao.status_publicacao == "publicada":
                        publicadas += 1
                        ultima_mensagem_em = time.monotonic()

                        logger.info(
                            "Produto publicado. Produto: %s | "
                            "Categoria: %s | Destino: %s",
                            produto_id,
                            nome_categoria,
                            destino_id,
                        )

                    elif publicacao.status_publicacao == "falhou":
                        falhas += 1
                        ultima_mensagem_em = time.monotonic()

                        logger.warning(
                            "Falha na publicação. Produto: %s | "
                            "Categoria: %s | Destino: %s | Erro: %s",
                            produto_id,
                            nome_categoria,
                            destino_id,
                            publicacao.erro,
                        )

                    else:
                        ignoradas += 1

                except (ValueError, LookupError) as erro:
                    session.rollback()
                    ignoradas += 1

                    logger.info(
                        "Produto ignorado. Produto: %s | "
                        "Categoria: %s | Motivo: %s",
                        produto_id,
                        nome_categoria,
                        erro,
                    )

                except IntegrityError:
                    session.rollback()
                    ignoradas += 1

                    logger.info(
                        "Publicação ignorada por conflito no banco. "
                        "Produto: %s | Destino: %s",
                        produto_id,
                        destino_id,
                    )

                except Exception:
                    session.rollback()
                    falhas += 1
                    ultima_mensagem_em = time.monotonic()

                    logger.exception(
                        "Erro inesperado ao publicar o produto %s "
                        "da categoria %s no destino %s.",
                        produto_id,
                        categoria_id,
                        destino_id,
                    )

        if status_ciclo != "pausado":
            self._registrar_execucao(destino_id)

        resultado = {
            "status": status_ciclo,
            "destino_id": destino_id,
            "candidatos": len(candidatos),
            "publicadas": publicadas,
            "falhas": falhas,
            "ignoradas": ignoradas,
        }

        logger.info(
            "Ciclo de publicação finalizado: %s",
            resultado,
        )

        return resultado
