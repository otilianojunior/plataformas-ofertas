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
    ):
        resultado = servico._executar_ciclo_destino_com_lock(7)

    assert time.monotonic() - inicio < 5
    assert resultado["status"] == "interrompido"
    assert resultado["publicadas"] == 1
    assert _status_finais(ciclo_repository)[0]["status"] == "interrompido"
    # O intervalo conta do início: após o reinício, o próximo ciclo espera
    # o intervalo em vez de recomeçar na hora com a lista inteira.
    servico.configuracao_repository.registrar_execucao.assert_called_once()


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


def test_coleta_para_entre_categorias_no_encerramento():
    """Salva o que já foi coletado e não começa a próxima categoria."""
    import threading

    from ofertas.models.plataforma import Plataforma

    encerrando = threading.Event()
    categorias = [Mock(id=i, nome_categoria=f"Cat {i}") for i in (1, 2, 3)]

    def coletar(_session, categoria, encerrando=None):
        encerrando.set()  # a API começa a parar durante a 1ª categoria
        return {"encontradas": 5, "processadas": 4, "ignoradas": 1, "erros": []}

    collector = Mock()
    collector.coletar_categoria.side_effect = coletar
    categoria_repository = Mock()
    categoria_repository.listar.return_value = categorias

    servico = ExecucaoColetaService.__new__(ExecucaoColetaService)
    servico.categoria_repository = categoria_repository
    servico._lock_da_loja = MagicMock()  # sem banco: lock sempre livre

    session = MagicMock()
    session.scalar.return_value = True  # lock adquirido
    session.get.return_value = Plataforma(id=1, codigo="shopee", status_plataforma=True)
    # simula os valores padrão que o banco atribui no flush
    session.add.side_effect = lambda obj: [
        setattr(obj, campo, 0)
        for campo in ("quantidade_encontrada", "quantidade_processada", "quantidade_ignorada")
    ]

    execucao = servico._executar(session, 1, "shopee", collector, encerrando)

    assert collector.coletar_categoria.call_count == 1
    assert execucao.status == "parcial"
    assert execucao.quantidade_processada == 4
    assert "encerramento da API" in execucao.erro
