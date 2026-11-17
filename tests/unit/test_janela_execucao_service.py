from datetime import datetime, time, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from ofertas.models.janela_execucao import JanelaExecucao
from ofertas.schemas.janela_execucao import (
    JanelaExecucaoCreate,
    JanelaExecucaoUpdate,
)
from ofertas.services.janela_execucao_service import JanelaExecucaoService


SP = ZoneInfo("America/Sao_Paulo")


def _janela(inicio: str, fim: str, ativa: bool = True, id: int = 1):
    return JanelaExecucao(
        id=id,
        hora_inicio=time.fromisoformat(inicio),
        hora_fim=time.fromisoformat(fim),
        ativa=ativa,
    )


@pytest.fixture
def repositorio():
    return Mock()


@pytest.fixture
def servico(repositorio):
    return JanelaExecucaoService(repository=repositorio)


# --- esta_em_horario_permitido ---------------------------------------------


def test_sem_janelas_ativas_libera_24h(servico, repositorio):
    repositorio.listar_ativas.return_value = []
    agora = datetime(2026, 11, 17, 3, 0, tzinfo=SP)

    assert servico.esta_em_horario_permitido(Mock(), agora) is True


@pytest.mark.parametrize(
    ("horario", "esperado"),
    [
        ("07:59:59", False),
        ("08:00:00", True),   # início é inclusivo
        ("11:59:59", True),
        ("12:00:00", False),  # fim é exclusivo
        ("18:30:00", True),
        ("23:00:00", False),
    ],
)
def test_limites_da_janela(servico, repositorio, horario, esperado):
    repositorio.listar_ativas.return_value = [
        _janela("08:00", "12:00"),
        _janela("18:00", "22:00", id=2),
    ]
    agora = datetime.combine(
        datetime(2026, 11, 17).date(),
        time.fromisoformat(horario),
        tzinfo=SP,
    )

    assert servico.esta_em_horario_permitido(Mock(), agora) is esperado


def test_horario_em_utc_e_convertido_para_sao_paulo(servico, repositorio):
    repositorio.listar_ativas.return_value = [_janela("08:00", "12:00")]

    # 11:00 UTC = 08:00 em São Paulo (UTC-3)
    agora_utc = datetime(2026, 11, 17, 11, 0, tzinfo=timezone.utc)
    assert servico.esta_em_horario_permitido(Mock(), agora_utc) is True

    # 08:00 UTC = 05:00 em São Paulo
    agora_utc = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)
    assert servico.esta_em_horario_permitido(Mock(), agora_utc) is False


# --- criar / atualizar -------------------------------------------------------


def test_criar_rejeita_sobreposicao(servico, repositorio):
    repositorio.existe_conflito.return_value = True

    with pytest.raises(ValueError, match="sobrepõe"):
        servico.criar(Mock(), time(8), time(12))

    repositorio.bloquear_alteracoes.assert_called_once()
    repositorio.criar.assert_not_called()


def test_criar_inativa_nao_verifica_sobreposicao(servico, repositorio):
    servico.criar(Mock(), time(8), time(12), ativa=False)

    repositorio.existe_conflito.assert_not_called()
    repositorio.criar.assert_called_once()


def test_criar_rejeita_inicio_maior_ou_igual_ao_fim(servico, repositorio):
    with pytest.raises(ValueError, match="meia-noite"):
        servico.criar(Mock(), time(22), time(2))

    repositorio.criar.assert_not_called()


def test_atualizar_combina_valores_atuais_e_ignora_a_propria_janela(
    servico,
    repositorio,
):
    repositorio.buscar.return_value = _janela("08:00", "12:00", id=7)
    repositorio.existe_conflito.return_value = False

    servico.atualizar(Mock(), 7, {"hora_fim": time(13)})

    _, inicio, fim = repositorio.existe_conflito.call_args.args
    assert (inicio, fim) == (time(8), time(13))
    assert repositorio.existe_conflito.call_args.kwargs == {"ignorar_id": 7}


def test_atualizar_rejeita_fim_antes_do_inicio_atual(servico, repositorio):
    repositorio.buscar.return_value = _janela("08:00", "12:00")

    with pytest.raises(ValueError):
        servico.atualizar(Mock(), 1, {"hora_fim": time(7)})

    repositorio.atualizar.assert_not_called()


def test_atualizar_janela_inexistente(servico, repositorio):
    repositorio.buscar.return_value = None

    with pytest.raises(LookupError):
        servico.atualizar(Mock(), 99, {"ativa": False})


# --- schemas -----------------------------------------------------------------


@pytest.mark.parametrize("campo", ["hora_inicio", "hora_fim"])
def test_schema_rejeita_horario_com_fuso(campo):
    dados = {"hora_inicio": "08:00", "hora_fim": "12:00"}
    dados[campo] = dados[campo] + "-03:00"

    with pytest.raises(ValidationError, match="sem fuso"):
        JanelaExecucaoCreate(**dados)

    with pytest.raises(ValidationError, match="sem fuso"):
        JanelaExecucaoUpdate(**{campo: dados[campo]})


def test_schema_update_exige_algum_campo_e_rejeita_nulo():
    with pytest.raises(ValidationError, match="ao menos um campo"):
        JanelaExecucaoUpdate()

    with pytest.raises(ValidationError, match="não pode ser nulo"):
        JanelaExecucaoUpdate(ativa=None)
