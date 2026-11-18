import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ofertas.db.session import SessionLocal, engine

from ofertas.affiliates.mercado_livre_affiliate_service import (
    MercadoLivreAffiliateService,
)
from ofertas.affiliates.shopee_affiliate_service import (
    ShopeeAffiliateService,
)
from ofertas.collectors.mercado_livre_collector import MercadoLivreCollector
from ofertas.collectors.shopee_collector import ShopeeCollector
from ofertas.models.execucao_coleta import ExecucaoColeta
from ofertas.models.plataforma import Plataforma
from ofertas.repositories.categoria_repository import CategoriaRepository


logger = logging.getLogger(__name__)


class ExecucaoColetaService:
    """Coordena e registra as execuções de coleta dos marketplaces."""

    CODIGO_MERCADO_LIVRE = "mercado_livre"
    CODIGO_SHOPEE = "shopee"
    LOCK_NAMESPACE = 20261104
    # Produtos por transação na geração de links afiliados.
    LOTE_AFILIADOS = 25

    def __init__(
        self,
        collector: MercadoLivreCollector | None = None,
        categoria_repository: CategoriaRepository | None = None,
        affiliate_service: MercadoLivreAffiliateService | None = None,
        shopee_collector: ShopeeCollector | None = None,
        shopee_affiliate_service: ShopeeAffiliateService | None = None,
    ) -> None:
        self.collector = collector or MercadoLivreCollector()
        self.shopee_collector = shopee_collector or ShopeeCollector()
        self.categoria_repository = (
            categoria_repository or CategoriaRepository()
        )
        self.affiliate_service = (
            affiliate_service or MercadoLivreAffiliateService()
        )
        self.shopee_affiliate_service = (
            shopee_affiliate_service or ShopeeAffiliateService()
        )

    def executar(
        self,
        session: Session,
        plataforma_id: int,
        encerrando: threading.Event | None = None,
    ) -> ExecucaoColeta:
        """Executa a coleta do Mercado Livre."""

        return self._executar(
            session,
            plataforma_id,
            self.CODIGO_MERCADO_LIVRE,
            self.collector,
            encerrando,
        )

    def executar_shopee(
        self,
        session: Session,
        plataforma_id: int,
        encerrando: threading.Event | None = None,
    ) -> ExecucaoColeta:
        """Executa a coleta da Shopee."""

        return self._executar(
            session,
            plataforma_id,
            self.CODIGO_SHOPEE,
            self.shopee_collector,
            encerrando,
        )

    @staticmethod
    def _definir_status(
        falhas: list[str],
        categorias_com_sucesso: int,
    ) -> str:
        """Diferencia falha total de falha em parte das categorias."""

        if not falhas:
            return "concluida"

        if categorias_com_sucesso > 0:
            return "parcial"

        return "falhou"

    def _executar(
        self,
        session: Session,
        plataforma_id: int,
        codigo_plataforma: str,
        collector,
        encerrando: threading.Event | None = None,
    ) -> ExecucaoColeta:
        with self._lock_da_loja(plataforma_id):
            return self._executar_com_lock(
                session,
                plataforma_id,
                codigo_plataforma,
                collector,
                encerrando,
            )

    @contextmanager
    def _lock_da_loja(self, plataforma_id: int) -> Iterator[None]:
        """Uma coleta por loja. O lock fica numa conexão própria porque a
        coleta grava (commit) a cada categoria."""

        with engine.connect() as conexao:
            adquirido = conexao.scalar(
                select(func.pg_try_advisory_lock(self.LOCK_NAMESPACE, plataforma_id))
            )
            conexao.commit()

            if not adquirido:
                raise ValueError(
                    "Já existe uma coleta em andamento para esta plataforma."
                )

            try:
                yield
            finally:
                conexao.scalar(
                    select(func.pg_advisory_unlock(self.LOCK_NAMESPACE, plataforma_id))
                )
                conexao.commit()

    @staticmethod
    def marcar_interrompidas(session: Session) -> int:
        """Ao subir a API nenhuma coleta roda: "em andamento" é resto de queda."""

        resultado = session.execute(
            update(ExecucaoColeta)
            .where(ExecucaoColeta.status == "em_andamento")
            .values(
                status="falhou",
                finalizada_em=datetime.now(timezone.utc),
                erro="Interrompida: a API foi encerrada durante a coleta.",
            )
        )
        return resultado.rowcount or 0

    def _executar_com_lock(
        self,
        session: Session,
        plataforma_id: int,
        codigo_plataforma: str,
        collector,
        encerrando: threading.Event | None = None,
    ) -> ExecucaoColeta:
        plataforma = session.get(Plataforma, plataforma_id)

        if plataforma is None:
            raise LookupError(
                f"Plataforma de ID '{plataforma_id}' não encontrada."
            )

        if plataforma.codigo != codigo_plataforma:
            raise ValueError(
                f"Este serviço aceita somente a plataforma "
                f"{codigo_plataforma}."
            )

        if not plataforma.status_plataforma:
            raise ValueError("A plataforma está inativa.")

        execucao = ExecucaoColeta(
            plataforma_id=plataforma_id,
            status="em_andamento",
        )
        session.add(execucao)
        session.flush()
        # Grava já: o painel mostra "executando" e cada categoria fica salva
        # (e com os preços visíveis para a publicação) assim que termina.
        session.commit()

        falhas = []
        avisos = []
        categorias_com_sucesso = 0

        try:
            categorias = self.categoria_repository.listar(
                session,
                plataforma_id=plataforma_id,
                somente_ativas=True,
            )

            if not categorias:
                falhas.append(
                    "Nenhuma categoria ativa disponível para coleta."
                )

            for categoria in categorias:
                # Encerramento da API: salva o que já foi coletado e para.
                if encerrando is not None and encerrando.is_set():
                    falhas.append(
                        "Coleta interrompida pelo encerramento da API antes "
                        f"da categoria '{categoria.nome_categoria}'."
                    )
                    break

                try:
                    with session.begin_nested():
                        resultado = collector.coletar_categoria(
                            session,
                            categoria,
                            encerrando=encerrando,
                        )

                    categorias_com_sucesso += 1

                    execucao.quantidade_encontrada += (
                        resultado["encontradas"]
                    )
                    execucao.quantidade_processada += (
                        resultado["processadas"]
                    )
                    execucao.quantidade_ignorada += (
                        resultado["ignoradas"]
                    )

                    for erro in resultado.get("erros", []):
                        avisos.append(
                            f"Categoria '{categoria.nome_categoria}': "
                            f"{erro}"
                        )

                except Exception as erro:
                    logger.exception(
                        "Falha na coleta da categoria %s (ID %s).",
                        categoria.nome_categoria,
                        categoria.id,
                    )

                    falhas.append(
                        f"Categoria '{categoria.nome_categoria}' "
                        f"(ID {categoria.id}): "
                        f"{type(erro).__name__}: {erro}"
                    )

                # Libera as linhas e a memória da sessão a cada categoria.
                session.commit()

                # Links afiliados já para esta categoria: a publicação não
                # espera a coleta inteira (que leva dezenas de minutos).
                if encerrando is None or not encerrando.is_set():
                    self.gerar_afiliados_pendentes(plataforma_id, encerrando)

        except Exception as erro:
            logger.exception(
                "Falha ao preparar a execução de coleta da plataforma %s.",
                plataforma_id,
            )
            falhas.append(
                f"Falha ao preparar a coleta: "
                f"{type(erro).__name__}: {erro}"
            )

        execucao.finalizada_em = datetime.now(timezone.utc)
        execucao.status = self._definir_status(
            falhas,
            categorias_com_sucesso,
        )

        registros_erro = []

        if falhas:
            registros_erro.append(
                "FALHAS DE CATEGORIA:\n" + "\n".join(falhas)
            )

        if avisos:
            registros_erro.append(
                "AVISOS DE PRODUTOS:\n" + "\n".join(avisos)
            )

        execucao.erro = (
            "\n\n".join(registros_erro)
            if registros_erro
            else None
        )

        session.flush()
        return execucao

    def gerar_afiliados_pendentes(
        self,
        plataforma_id: int,
        encerrando: threading.Event | None = None,
    ) -> dict | None:
        """Gera links afiliados em lotes, cada um gravado na hora.

        Um lote por transação: os links já gerados ficam visíveis para a
        publicação e nada segura as tabelas por muito tempo.
        """

        total = {"total_encontrados": 0, "total_gerados": 0, "total_erros": 0, "total_lotes": 0, "total_tentativas": 0, "erros": []}
        vistos: list[int] = []

        while encerrando is None or not encerrando.is_set():
            with SessionLocal() as session:
                try:
                    plataforma = session.get(Plataforma, plataforma_id)

                    if plataforma is None:
                        raise LookupError(
                            f"Plataforma de ID '{plataforma_id}' não encontrada."
                        )

                    if plataforma.codigo == self.CODIGO_MERCADO_LIVRE:
                        servico_afiliado = self.affiliate_service
                    elif plataforma.codigo == self.CODIGO_SHOPEE:
                        servico_afiliado = self.shopee_affiliate_service
                    else:
                        raise ValueError(
                            f"Não existe serviço de afiliados para a plataforma "
                            f"'{plataforma.codigo}'."
                        )

                    resultado = servico_afiliado.gerar_pendentes(
                        session,
                        plataforma_id,
                        encerrando=encerrando,
                        limite=self.LOTE_AFILIADOS,
                        excluir_ids=vistos,
                    )
                    session.commit()

                except Exception:
                    session.rollback()
                    logger.exception(
                        "Falha independente na geração de links afiliados "
                        "da plataforma %s. A coleta já confirmada foi preservada.",
                        plataforma_id,
                    )
                    return None

            for chave in ("total_encontrados", "total_gerados", "total_erros", "total_lotes", "total_tentativas"):
                total[chave] += resultado.get(chave, 0)
            total["erros"].extend(resultado.get("erros", []))

            ids = resultado.get("produto_ids", [])
            # Quem falhou neste lote não volta na mesma rodada.
            vistos.extend(ids)

            if len(ids) < self.LOTE_AFILIADOS:
                break

        if total["total_encontrados"]:
            logger.info(
                "Geração de links afiliados concluída. "
                "Plataforma: %s | Encontrados: %s | Gerados: %s | "
                "Erros: %s | Lotes: %s | Tentativas: %s",
                plataforma_id,
                total["total_encontrados"],
                total["total_gerados"],
                total["total_erros"],
                total["total_lotes"],
                total["total_tentativas"],
            )

        for erro_afiliado in total["erros"]:
            logger.warning(
                "Falha ao gerar link afiliado. Produto %s: %s",
                erro_afiliado["produto_id"],
                erro_afiliado["mensagem"],
            )

        return total
