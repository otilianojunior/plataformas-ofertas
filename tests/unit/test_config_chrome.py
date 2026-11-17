from unittest.mock import patch

import pytest

from ofertas.affiliates.mercado_livre_browser import MercadoLivreBrowser
from ofertas.core.config import RAIZ_PROJETO, Settings


def _settings(**kwargs) -> Settings:
    base = {"database_url": "postgresql+psycopg://x", "credential_encryption_key": "x"}
    return Settings(_env_file=None, **base, **kwargs)


def test_perfil_padrao_fica_em_data_na_raiz_do_projeto():
    assert _settings().mercado_livre_chrome_profile_dir == RAIZ_PROJETO / "data/chrome_profile"


def test_perfil_relativo_e_resolvido_pela_raiz_e_nao_pelo_diretorio_atual():
    perfil = _settings(mercado_livre_chrome_profile_dir="outro/perfil").mercado_livre_chrome_profile_dir
    assert perfil == RAIZ_PROJETO / "outro/perfil"


def test_perfil_absoluto_e_mantido(tmp_path):
    assert _settings(mercado_livre_chrome_profile_dir=str(tmp_path)).mercado_livre_chrome_profile_dir == tmp_path


def test_raiz_do_projeto_aponta_para_o_repositorio():
    assert (RAIZ_PROJETO / "pyproject.toml").exists()


def test_detecta_o_primeiro_chrome_instalado():
    navegador = MercadoLivreBrowser(_settings(mercado_livre_chrome_path=""))
    instalados = {"chromium": "/usr/bin/chromium"}

    with patch("shutil.which", side_effect=instalados.get):
        assert navegador._localizar_chrome() == "/usr/bin/chromium"


def test_caminho_configurado_tem_prioridade():
    navegador = MercadoLivreBrowser(_settings(mercado_livre_chrome_path="/opt/chrome"))

    with patch("shutil.which", side_effect=lambda c: c if c == "/opt/chrome" else None):
        assert navegador._localizar_chrome() == "/opt/chrome"


def test_sem_chrome_instalado_explica_o_que_fazer():
    navegador = MercadoLivreBrowser(_settings())

    with patch("shutil.which", return_value=None):
        with pytest.raises(FileNotFoundError, match="MERCADO_LIVRE_CHROME_PATH"):
            navegador._localizar_chrome()
