from fastapi import FastAPI

from ofertas.api.plataformas import router as plataformas_router
from ofertas.api.ofertas import router as ofertas_router
from ofertas.api.categorias import router as categorias_router
from ofertas.api.configuracoes_coleta import router as configuracoes_coleta_router
from ofertas.api.plataformas_divulgacao import router as plataformas_divulgacao_router
from ofertas.api.destinos_divulgacao import router as destinos_divulgacao_router
from ofertas.api.credenciais_plataforma import router as credenciais_plataforma_router
from ofertas.api.credenciais_divulgacao import router as credenciais_divulgacao_router

app = FastAPI(
    title="Plataformas de Ofertas",
    description="API para coleta, armazenamento e distribuição de ofertas.",
    version="0.1.0",
)

app.include_router(plataformas_router)
app.include_router(ofertas_router)
app.include_router(categorias_router)
app.include_router(configuracoes_coleta_router)
app.include_router(plataformas_divulgacao_router)
app.include_router(destinos_divulgacao_router)
app.include_router(credenciais_plataforma_router)
app.include_router(credenciais_divulgacao_router)


@app.get("/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}