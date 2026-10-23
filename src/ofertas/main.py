from fastapi import FastAPI


app = FastAPI(
    title="Plataformas de Ofertas",
    description="API para coleta, armazenamento e distribuição de ofertas.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}