
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ofertas.collectors.mercado_livre_collector import MercadoLivreCollector
from ofertas.models.execucao_coleta import ExecucaoColeta
from ofertas.models.plataforma import Plataforma
from ofertas.repositories.categoria_repository import CategoriaRepository


logger = logging.getLogger(__name__)


class ExecucaoColetaService:
    """Coordena e registra as execuções de coleta."""

    CODIGO_PLATAFORMA = "mercado_livre"
    LOCK_NAMESPACE = 20261104

    def __init__(
        self,
        collector: MercadoLivreCollector | None = None,
        categoria_repository: CategoriaRepository | None = None,
    ) -> None:
        self.collector = collector or MercadoLivreCollector()
        self.categoria_repository = (
            categoria_repository or CategoriaRepository()
        )

    def executar(
        self,
        session: Session,
        plataforma_id: int,
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

        if plataforma.codigo != self.CODIGO_PLATAFORMA:
            raise ValueError(
                "Este serviço aceita somente a plataforma Mercado Livre."
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
                        resultado = self.collector.coletar_categoria(
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
