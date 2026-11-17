from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# src/ofertas/core/config.py -> raiz do repositório
RAIZ_PROJETO = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str
    credential_encryption_key: str

    # Chrome usado na geração de links afiliados do Mercado Livre.
    # Vazio: procura google-chrome, google-chrome-stable, chromium...
    mercado_livre_chrome_path: str | None = None

    # Perfil dedicado do projeto (não é o seu Chrome pessoal). Caminho
    # relativo é resolvido a partir da raiz do repositório.
    mercado_livre_chrome_profile_dir: Path = Path("data/chrome_profile")

    mercado_livre_chrome_cdp_url: str = "http://127.0.0.1:9222"

    model_config = SettingsConfigDict(
        env_file=RAIZ_PROJETO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("mercado_livre_chrome_path", mode="before")
    @classmethod
    def _vazio_vira_none(cls, valor):
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor

    @field_validator("mercado_livre_chrome_profile_dir", mode="after")
    @classmethod
    def _resolver_perfil(cls, valor: Path) -> Path:
        valor = valor.expanduser()

        if not valor.is_absolute():
            valor = RAIZ_PROJETO / valor

        return valor


@lru_cache
def get_settings() -> Settings:
    return Settings()
