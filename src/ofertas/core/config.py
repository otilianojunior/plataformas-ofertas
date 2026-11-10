from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    credential_encryption_key: str

    # Configuração do Chrome utilizado na geração de links afiliados.
    mercado_livre_chrome_path: str = "google-chrome"

    mercado_livre_chrome_profile_dir: Path = (
        Path.home()
        / ".local"
        / "share"
        / "plataformas-ofertas"
        / "mercado-livre-chrome"
    )

    mercado_livre_chrome_cdp_url: str = "http://127.0.0.1:9222"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
