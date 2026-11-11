import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ofertas.api.plataformas import router as plataformas_router
from ofertas.api.produtos import router as produtos_router
from ofertas.api.categorias import router as categorias_router
from ofertas.api.configuracoes_sistema import router as configuracoes_sistema_router
from ofertas.api.configuracoes_divulgacao import router as configuracoes_divulgacao_router
from ofertas.api.plataformas_divulgacao import router as plataformas_divulgacao_router
from ofertas.api.destinos_divulgacao import router as destinos_divulgacao_router
from ofertas.api.credenciais_plataforma import router as credenciais_plataforma_router
from ofertas.api.credenciais_divulgacao import router as credenciais_divulgacao_router
from ofertas.api.publicacoes import router as publicacoes_router
from ofertas.api.oauth_mercado_livre import router as oauth_mercado_livre_router
from ofertas.api.coletas import router as coletas_router

from ofertas.services.automacao_service import AutomacaoService
from ofertas.services.publicacao_lote_service import PublicacaoLoteService


logger = logging.getLogger(__name__)

INTERVALO_VERIFICACAO_AUTOMACOES_SEGUNDOS = 15
INTERVALO_SINAL_VIDA_SEGUNDOS = 30


async def aguardar_encerramento(
    evento: asyncio.Event,
    intervalo: int,
) -> None:
    try:
        await asyncio.wait_for(evento.wait(), timeout=intervalo)
    except TimeoutError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Executa as automações dentro do processo da API."""

    automacao = AutomacaoService()
    publicacao_lote = PublicacaoLoteService()

    encerrando = asyncio.Event()
    tarefas_publicacao: dict[int, asyncio.Task[None]] = {}

    async def monitorar_sinal_vida() -> None:
        while not encerrando.is_set():
            await asyncio.to_thread(automacao.registrar_sinal)

            await aguardar_encerramento(
                encerrando,
                INTERVALO_SINAL_VIDA_SEGUNDOS,
            )

    async def monitorar_coletas() -> None:
        while not encerrando.is_set():
            try:
                await asyncio.to_thread(
                    automacao.executar_coletas_liberadas
                )
            except Exception:
                logger.exception("Erro no ciclo automático de coletas.")

            await aguardar_encerramento(
                encerrando,
                INTERVALO_VERIFICACAO_AUTOMACOES_SEGUNDOS,
            )

    async def executar_lote_destino(destino_id: int) -> None:
        try:
            resultado = await asyncio.to_thread(
                publicacao_lote.executar_ciclo_destino,
                destino_id,
            )

            logger.info(
                "Ciclo automático do destino %s: %s",
                destino_id,
                resultado,
            )

        except Exception:
            logger.exception(
                "Erro no ciclo automático de publicação do destino %s.",
                destino_id,
            )

    async def monitorar_publicacoes() -> None:
        while not encerrando.is_set():
            try:
                destinos = await asyncio.to_thread(
                    automacao.listar_destinos_publicacao_liberados
                )

                if encerrando.is_set():
                    break

                for destino_id in destinos:
                    tarefa = tarefas_publicacao.get(destino_id)

                    if tarefa is None or tarefa.done():
                        tarefas_publicacao[destino_id] = (
                            asyncio.create_task(
                                executar_lote_destino(destino_id),
                                name=f"publicacao-destino-{destino_id}",
                            )
                        )

            except Exception:
                logger.exception(
                    "Erro ao verificar ciclos de publicação."
                )

            await aguardar_encerramento(
                encerrando,
                INTERVALO_VERIFICACAO_AUTOMACOES_SEGUNDOS,
            )

    tarefas_principais = [
        asyncio.create_task(
            monitorar_sinal_vida(),
            name="automacao-sinal-vida",
        ),
        asyncio.create_task(
            monitorar_coletas(),
            name="automacao-coletas",
        ),
        asyncio.create_task(
            monitorar_publicacoes(),
            name="automacao-publicacoes",
        ),
    ]

    logger.info("Automações internas da API iniciadas.")

    try:
        yield

    finally:
        logger.info("Encerrando automações internas da API.")
        encerrando.set()

        await asyncio.gather(
            *tarefas_principais,
            return_exceptions=True,
        )

        tarefas_ativas = [
            tarefa
            for tarefa in tarefas_publicacao.values()
            if not tarefa.done()
        ]

        if tarefas_ativas:
            await asyncio.gather(
                *tarefas_ativas,
                return_exceptions=True,
            )

        logger.info("Automações internas da API encerradas.")


app = FastAPI(
    title="Plataformas de Ofertas",
    description="API para coleta, armazenamento e distribuição de produtos e ofertas.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(plataformas_router)
app.include_router(coletas_router)
app.include_router(oauth_mercado_livre_router)
app.include_router(produtos_router)
app.include_router(categorias_router)
app.include_router(configuracoes_sistema_router)
app.include_router(configuracoes_divulgacao_router)
app.include_router(plataformas_divulgacao_router)
app.include_router(destinos_divulgacao_router)
app.include_router(credenciais_plataforma_router)
app.include_router(credenciais_divulgacao_router)
app.include_router(publicacoes_router)


@app.get("/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
