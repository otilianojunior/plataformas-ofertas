import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from ofertas import __version__

from ofertas.api.autenticacao import RESPOSTA_401, usuario_atual
from ofertas.api.autenticacao import router as autenticacao_router
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
from ofertas.api.automacoes import router as automacoes_router
from ofertas.api.janelas_execucao import router as janelas_execucao_router
from ofertas.api.ciclos_publicacao import router as ciclos_publicacao_router
from ofertas.api.usuarios import router as usuarios_router

from ofertas.publishers.whatsapp_web import WhatsAppWebClient
from ofertas.services.automacao_service import AutomacaoService
from ofertas.services.publicacao_lote_service import PublicacaoLoteService


from ofertas.core.config import RAIZ_PROJETO, get_settings


# Sem isto os logs INFO das automações não aparecem no uvicorn/journalctl.
logging.basicConfig(
    level=get_settings().log_level.upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

# O httpx registra a URL de cada requisição em INFO, e a URL da API do
# Telegram contém o token do bot (/bot<token>/...). Nunca baixe para INFO.
for _biblioteca in ("httpx", "httpcore"):
    logging.getLogger(_biblioteca).setLevel(logging.WARNING)

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

    await asyncio.to_thread(automacao.marcar_coletas_interrompidas)

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
        automacao.encerrando.set()
        publicacao_lote.encerrando.set()
        WhatsAppWebClient.encerrando.set()

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
    version=__version__,
    lifespan=lifespan,
)

# Rotas abertas: login, saúde e OAuth do Mercado Livre (o navegador é
# redirecionado para elas sem o token; o callback é protegido pelo `state`).
app.include_router(autenticacao_router)
app.include_router(oauth_mercado_livre_router)

# Todas as demais exigem login no painel.
for _router in (
    plataformas_router,
    coletas_router,
    automacoes_router,
    janelas_execucao_router,
    ciclos_publicacao_router,
    produtos_router,
    categorias_router,
    configuracoes_sistema_router,
    configuracoes_divulgacao_router,
    plataformas_divulgacao_router,
    destinos_divulgacao_router,
    credenciais_plataforma_router,
    credenciais_divulgacao_router,
    publicacoes_router,
    usuarios_router,
):
    app.include_router(
        _router,
        dependencies=[Depends(usuario_atual)],
        responses=RESPOSTA_401,
    )


# --- painel (frontend compilado em frontend/dist) -----------------------------
PAINEL_DIST = RAIZ_PROJETO / "frontend" / "dist"


@app.get("/painel", include_in_schema=False)
@app.get("/painel/{caminho:path}", include_in_schema=False)
def painel(caminho: str = "") -> FileResponse:
    """Serve o painel; rotas internas do React caem no index.html."""

    if not (PAINEL_DIST / "index.html").exists():
        raise HTTPException(
            status_code=404,
            detail="Painel não compilado. Rode: make painel-build",
        )

    arquivo = (PAINEL_DIST / caminho).resolve()

    # Impede sair da pasta dist (ex.: /painel/../../.env).
    if arquivo.is_file() and arquivo.is_relative_to(PAINEL_DIST.resolve()):
        return FileResponse(arquivo)

    return FileResponse(PAINEL_DIST / "index.html")


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse("/painel/")


@app.get("/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
