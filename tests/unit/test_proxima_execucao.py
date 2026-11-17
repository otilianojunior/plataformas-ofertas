from datetime import datetime, time
from zoneinfo import ZoneInfo

from ofertas.models.janela_execucao import JanelaExecucao
from ofertas.services.automacao_status_service import AutomacaoStatusService


SP = ZoneInfo("America/Sao_Paulo")
proxima = AutomacaoStatusService._proxima_data_permitida


def _janela(inicio: int, fim: int) -> JanelaExecucao:
    return JanelaExecucao(hora_inicio=time(inicio), hora_fim=time(fim), ativa=True)


def test_sem_janelas_execucao_atrasada_vira_agora():
    agora = datetime(2026, 11, 17, 16, 30, tzinfo=SP)
    prevista = datetime(2026, 11, 13, 2, 0, tzinfo=SP)

    assert proxima(prevista, [], agora) == agora


def test_sem_janelas_execucao_futura_mantem_data():
    agora = datetime(2026, 11, 17, 16, 30, tzinfo=SP)
    prevista = datetime(2026, 11, 17, 17, 0, tzinfo=SP)

    assert proxima(prevista, [], agora) == prevista


def test_atrasada_fora_da_janela_vai_para_proxima_janela_de_hoje():
    agora = datetime(2026, 11, 17, 16, 30, tzinfo=SP)
    prevista = datetime(2026, 11, 13, 2, 0, tzinfo=SP)

    assert proxima(prevista, [_janela(17, 18)], agora) == datetime(
        2026, 11, 17, 17, 0, tzinfo=SP
    )


def test_atrasada_dentro_da_janela_vira_agora():
    agora = datetime(2026, 11, 17, 17, 15, tzinfo=SP)
    prevista = datetime(2026, 11, 13, 2, 0, tzinfo=SP)

    assert proxima(prevista, [_janela(17, 18)], agora) == agora


def test_janela_de_hoje_ja_passou_vai_para_amanha():
    agora = datetime(2026, 11, 17, 19, 0, tzinfo=SP)

    assert proxima(agora, [_janela(8, 12), _janela(17, 18)], agora) == datetime(
        2026, 11, 18, 8, 0, tzinfo=SP
    )
