"""Registro dos ciclos de publicação e status das coletas."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from ofertas.services.execucao_coleta_service import ExecucaoColetaService
from ofertas.services.publicacao_lote_service import PublicacaoLoteService


def _session_local():
    fabrica = MagicMock()
    fabrica.return_value.__enter__.return_value = MagicMock()
    fabrica.return_value.__exit__.return_value = False
    return fabrica


@pytest.fixture
def ciclo_repository():
    repositorio = Mock()
    repositorio.iniciar.return_value = Mock(id=42)
    return repositorio


@pytest.fixture
def servico(ciclo_repository):
    return PublicacaoLoteService(
        configuracao_repository=Mock(),
        destino_repository=Mock(),
        categoria_repository=Mock(),
        produto_repository=Mock(),
        publicacao_service=Mock(),
        janela_execucao_service=Mock(),
        ciclo_repository=ciclo_repository,
    )


def _status_finais(ciclo_repository):
    return [
        chamada.kwargs
        for chamada in ciclo_repository.atualizar.call_args_list
        if "status" in chamada.kwargs
    ]


def test_ciclo_concluido_registra_inicio_progresso_e_fim(servico, ciclo_repository):
    servico.publicacao_service.publicar_produto.return_value = Mock(
        status_publicacao="publicada"
    )
    candidatos = [(1, "Teclados", 10), (1, "Teclados", 11)]

    with (
        patch("ofertas.services.publicacao_lote_service.SessionLocal", _session_local()),
        patch.object(servico, "INTERVALO_ENTRE_MENSAGENS_SEGUNDOS", 0),
        patch.object(servico, "_buscar_configuracao_ativa", return_value=Mock()),
        patch.object(servico, "_selecionar_candidatos", return_value=candidatos),
        patch.object(servico, "_registrar_execucao"),
    ):
        resultado = servico._executar_ciclo_destino_com_lock(7)

    assert resultado["publicadas"] == 2
    ciclo_repository.marcar_interrompidos.assert_called_once()
    assert ciclo_repository.iniciar.call_args.args[1:] == (7, 2)

    # progresso gravado antes do 2º produto
    progresso = ciclo_repository.atualizar.call_args_list[0].kwargs
    assert progresso == {
        "quantidade_publicada": 1,
        "quantidade_falha": 0,
        "quantidade_ignorada": 0,
    }

    (final,) = _status_finais(ciclo_repository)
    assert final["status"] == "concluido"
    assert final["quantidade_publicada"] == 2
    assert final["finalizado_em"] is not None


def test_ciclo_pausado_no_meio_e_registrado_como_pausado(servico, ciclo_repository):
    with (
        patch("ofertas.services.publicacao_lote_service.SessionLocal", _session_local()),
        patch.object(servico, "_buscar_configuracao_ativa", side_effect=[Mock(), None]),
        patch.object(servico, "_selecionar_candidatos", return_value=[(1, "c", 10)]),
    ):
        resultado = servico._executar_ciclo_destino_com_lock(7)

    assert resultado["status"] == "pausado"
    assert _status_finais(ciclo_repository)[0]["status"] == "pausado"


def test_erro_inesperado_registra_falha_e_propaga(servico, ciclo_repository):
    with (
        patch("ofertas.services.publicacao_lote_service.SessionLocal", _session_local()),
        patch.object(servico, "_buscar_configuracao_ativa", return_value=Mock()),
        patch.object(servico, "_selecionar_candidatos", return_value=[(1, "c", 10)]),
        patch.object(servico, "_publicar_candidatos", side_effect=RuntimeError("boom")),
    ):
        with pytest.raises(RuntimeError):
            servico._executar_ciclo_destino_com_lock(7)

    (final,) = _status_finais(ciclo_repository)
    assert final["status"] == "falhou"
    assert "boom" in final["erro"]


def test_destino_pausado_antes_de_iniciar_nao_cria_ciclo(servico, ciclo_repository):
    with (
        patch("ofertas.services.publicacao_lote_service.SessionLocal", _session_local()),
        patch.object(servico, "_buscar_configuracao_ativa", return_value=None),
    ):
        assert servico._executar_ciclo_destino_com_lock(7)["status"] == "pausado"

    ciclo_repository.iniciar.assert_not_called()


def test_falha_ao_gravar_progresso_nao_interrompe_publicacao(servico, ciclo_repository):
    ciclo_repository.atualizar.side_effect = RuntimeError("banco fora")
    servico.publicacao_service.publicar_produto.return_value = Mock(
        status_publicacao="publicada"
    )

    with (
        patch("ofertas.services.publicacao_lote_service.SessionLocal", _session_local()),
        patch.object(servico, "INTERVALO_ENTRE_MENSAGENS_SEGUNDOS", 0),
        patch.object(servico, "_buscar_configuracao_ativa", return_value=Mock()),
        patch.object(servico, "_selecionar_candidatos", return_value=[(1, "c", 10), (1, "c", 11)]),
        patch.object(servico, "_registrar_execucao"),
    ):
        resultado = servico._executar_ciclo_destino_com_lock(7)

    assert resultado["publicadas"] == 2


@pytest.mark.parametrize(
    ("falhas", "sucessos", "esperado"),
    [
        ([], 5, "concluida"),
        (["Categoria X falhou"], 4, "parcial"),
        (["Categoria X falhou"], 0, "falhou"),
        (["Nenhuma categoria ativa"], 0, "falhou"),
    ],
)
def test_status_da_execucao_de_coleta(falhas, sucessos, esperado):
    assert ExecucaoColetaService._definir_status(falhas, sucessos) == esperado


def test_encerramento_da_api_interrompe_durante_o_intervalo(servico, ciclo_repository):
    """Não espera os 20s entre mensagens quando a API está parando."""
    import threading
    import time

    servico.publicacao_service.publicar_produto.return_value = Mock(
        status_publicacao="publicada"
    )
    threading.Timer(0.2, servico.encerrando.set).start()
    inicio = time.monotonic()

    with (
        patch("ofertas.services.publicacao_lote_service.SessionLocal", _session_local()),
        patch.object(servico, "_buscar_configuracao_ativa", return_value=Mock()),
        patch.object(servico, "_selecionar_candidatos", return_value=[(1, "c", 10), (1, "c", 11)]),
        patch.object(servico, "_registrar_execucao") as registrar,
    ):
        resultado = servico._executar_ciclo_destino_com_lock(7)

    assert time.monotonic() - inicio < 5
    assert resultado["status"] == "interrompido"
    assert resultado["publicadas"] == 1
    assert _status_finais(ciclo_repository)[0]["status"] == "interrompido"
    registrar.assert_not_called()  # o ciclo volta a rodar após o reinício


def test_encerramento_antes_do_ciclo_nao_publica(servico):
    servico.encerrando.set()

    with (
        patch("ofertas.services.publicacao_lote_service.SessionLocal", _session_local()),
        patch.object(servico, "_buscar_configuracao_ativa", return_value=Mock()),
        patch.object(servico, "_selecionar_candidatos", return_value=[(1, "c", 10)]),
    ):
        resultado = servico._executar_ciclo_destino_com_lock(7)

    assert resultado["status"] == "interrompido"
    servico.publicacao_service.publicar_produto.assert_not_called()
