
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from ofertas.db.session import SessionLocal
from ofertas.models.execucao_coleta import ExecucaoColeta
from ofertas.models.plataforma import Plataforma
from ofertas.services.configuracao_sistema_service import (
    ConfiguracaoSistemaService,
)
from ofertas.services.execucao_coleta_service import ExecucaoColetaService


logger = logging.getLogger(__name__)


def verificar_coletas_agendadas() -> None:
    """Atualiza o heartbeat e verifica coletas automáticas."""

    servico_configuracao = ConfiguracaoSistemaService()

    # Atualiza o heartbeat mesmo quando a coleta está pausada.
    with SessionLocal() as session:
        try:
            configuracao = servico_configuracao.registrar_sinal(session)

            coleta_ativa = configuracao.coleta_mercado_livre_ativa
            intervalo_segundos = (
                configuracao.intervalo_coleta_minutos * 60
            )

            session.commit()

        except Exception:
            session.rollback()
            logger.exception(
                "Erro ao atualizar o sinal de vida do agendador."
            )
            return

    if not coleta_ativa:
        logger.debug("Coleta automática está pausada.")
        return

    with SessionLocal() as session:
        try:
            plataforma_ids = session.scalars(
                select(Plataforma.id).where(
                    Plataforma.codigo == "mercado_livre",
                    Plataforma.status_plataforma.is_(True),
                )
            ).all()

        except Exception:
            session.rollback()
            logger.exception(
                "Erro ao consultar plataformas para coleta."
            )
            return

    if not plataforma_ids:
        logger.warning(
            "Nenhuma plataforma Mercado Livre ativa encontrada."
        )
        return

    for plataforma_id in plataforma_ids:
        with SessionLocal() as session:
            try:
                # Reconsulta o estado para respeitar uma pausa
                # solicitada durante o ciclo do agendador.
                configuracao_atual = servico_configuracao.buscar(session)

                if not configuracao_atual.coleta_mercado_livre_ativa:
                    logger.info(
                        "Coleta automática pausada durante a execução."
                    )
                    break

                ultima_execucao = session.scalar(
                    select(ExecucaoColeta)
                    .where(
                        ExecucaoColeta.plataforma_id == plataforma_id
                    )
                    .order_by(
                        ExecucaoColeta.iniciada_em.desc(),
                        ExecucaoColeta.id.desc(),
                    )
                    .limit(1)
                )

                agora = datetime.now(timezone.utc)

                if ultima_execucao is not None:
                    if ultima_execucao.status == "em_andamento":
                        continue

                    referencia = (
                        ultima_execucao.finalizada_em
                        or ultima_execucao.iniciada_em
                    )

                    tempo_decorrido = (
                        agora - referencia
                    ).total_seconds()

                    if tempo_decorrido < intervalo_segundos:
                        continue

                execucao = ExecucaoColetaService().executar(
                    session,
                    plataforma_id,
                )

                execucao_id = execucao.id
                execucao_status = execucao.status
                quantidade_processada = (
                    execucao.quantidade_processada
                )

                session.commit()

                logger.info(
                    "Coleta automática finalizada. "
                    "Execução: %s | Plataforma: %s | "
                    "Status: %s | Produtos processados: %s",
                    execucao_id,
                    plataforma_id,
                    execucao_status,
                    quantidade_processada,
                )

            except ValueError as erro:
                session.rollback()
                logger.info(
                    "Coleta da plataforma %s não iniciada: %s",
                    plataforma_id,
                    erro,
                )

            except Exception:
                session.rollback()
                logger.exception(
                    "Erro na coleta automática da plataforma %s.",
                    plataforma_id,
                )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        verificar_coletas_agendadas,
        trigger="interval",
        minutes=1,
        id="coleta_automatica_mercado_livre",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )

    logger.info("Agendador de coletas iniciado.")
    scheduler.start()


if __name__ == "__main__":
    main()
