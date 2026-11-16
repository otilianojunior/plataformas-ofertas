import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ofertas.db.session import SessionLocal

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
    ) -> ExecucaoColeta:
        """Executa a coleta do Mercado Livre."""

        return self._executar(
            session,
            plataforma_id,
            self.CODIGO_MERCADO_LIVRE,
            self.collector,
        )

    def executar_shopee(
        self,
        session: Session,
        plataforma_id: int,
    ) -> ExecucaoColeta:
        """Executa a coleta da Shopee."""

        return self._executar(
            session,
            plataforma_id,
            self.CODIGO_SHOPEE,
            self.shopee_collector,
        )

    def _executar(
        self,
        session: Session,
        plataforma_id: int,
        codigo_plataforma: str,
        collector,
    ) -> ExecucaoColeta:
        lock_adquirido = session.scalar(
            select(
                func.pg_try_advisory_xact_lock(
                    self.LOCK_NAMESPACE,
                    plataforma_id,
                )
            )
        )

        if not lock_adquirido:
            raise ValueError(
                "Já existe uma coleta em andamento para esta plataforma."
            )

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

        falhas = []
        avisos = []

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
                try:
                    with session.begin_nested():
                        resultado = collector.coletar_categoria(
                            session,
                            categoria,
                        )

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
        execucao.status = "falhou" if falhas else "concluida"

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
    ) -> dict | None:
        """Gera links afiliados conforme a plataforma cadastrada."""

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

        logger.info(
            "Geração de links afiliados concluída. "
            "Plataforma: %s | Encontrados: %s | Gerados: %s | "
            "Erros: %s | Lotes: %s | Tentativas: %s",
            plataforma_id,
            resultado.get("total_encontrados", 0),
            resultado.get("total_gerados", 0),
            resultado.get("total_erros", 0),
            resultado.get("total_lotes", 0),
            resultado.get("total_tentativas", 0),
        )

        for erro_afiliado in resultado.get("erros", []):
            logger.warning(
                "Falha ao gerar link afiliado. Produto %s: %s",
                erro_afiliado["produto_id"],
                erro_afiliado["mensagem"],
            )

        return resultado
