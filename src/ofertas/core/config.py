from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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

    # WhatsApp Web (não oficial): Chrome com perfil próprio, logado por QR
    # Code. Limites conservadores para reduzir o risco de restrição do número.
    whatsapp_chrome_profile_dir: Path = Path("data/whatsapp_profile")
    whatsapp_chrome_cdp_url: str = "http://127.0.0.1:9223"
    whatsapp_intervalo_minimo_segundos: int = Field(default=120, ge=60)
    whatsapp_limite_diario: int = Field(default=30, ge=1)

    # Descontos acima disto quase sempre vêm de preço "de" inflado pela loja
    # (ex.: R$ 8.972,50 por R$ 358,90 = 96%): o produto não é publicado.
    desconto_maximo_percentual: Decimal = Field(default=Decimal("90"), gt=0, le=100)

    # Sessão do painel: token assinado com a CREDENTIAL_ENCRYPTION_KEY.
    sessao_duracao_horas: int = Field(default=12, ge=1, le=720)

    log_level: str = "INFO"

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

    @field_validator(
        "mercado_livre_chrome_profile_dir",
        "whatsapp_chrome_profile_dir",
        mode="after",
    )
    @classmethod
    def _resolver_perfil(cls, valor: Path) -> Path:
        valor = valor.expanduser()

        if not valor.is_absolute():
            valor = RAIZ_PROJETO / valor

        return valor


@lru_cache
def get_settings() -> Settings:
    return Settings()
