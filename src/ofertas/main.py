from fastapi import FastAPI

from ofertas.api.plataformas import router as plataformas_router


app = FastAPI(
    title="Plataformas de Ofertas",
    description="API para coleta, armazenamento e distribuição de ofertas.",
    version="0.1.0",
)

app.include_router(plataformas_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
