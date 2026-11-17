"""Garante que coletas e publicações automáticas não começam fora das janelas."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from ofertas.models.configuracao_sistema import ConfiguracaoSistema
from ofertas.services.automacao_service import AutomacaoService
from ofertas.services.publicacao_lote_service import PublicacaoLoteService


def _configuracao_sistema(**kwargs) -> ConfiguracaoSistema:
    valores = dict(
        id=1,
        automacoes_ativas=True,
        coleta_mercado_livre_ativa=True,
        coleta_shopee_ativa=True,
        publicacao_telegram_ativa=True,
        publicacao_whatsapp_ativa=False,
        intervalo_coleta_minutos=30,
        limite_produtos_por_categoria=10,
    )
    valores.update(kwargs)
    return ConfiguracaoSistema(**valores)


def _session_local(session):
    """Simula `with SessionLocal() as session:` devolvendo o mock informado."""
    fabrica = MagicMock()
    fabrica.return_value.__enter__.return_value = session
    fabrica.return_value.__exit__.return_value = False
    return fabrica


@pytest.fixture
def janela_fechada():
    janela = Mock()
    janela.esta_em_horario_permitido.return_value = False
    return janela


# --- coletas -----------------------------------------------------------------


def test_coletas_nao_iniciam_fora_da_janela(janela_fechada):
    session = MagicMock()
    configuracao_service = Mock()
    configuracao_service.buscar.return_value = _configuracao_sistema()
    execucao_coleta_service = Mock()

    servico = AutomacaoService(
        configuracao_sistema_service=configuracao_service,
        execucao_coleta_service=execucao_coleta_service,
        configuracao_divulgacao_repository=Mock(),
        destino_repository=Mock(),
        janela_execucao_service=janela_fechada,
    )

    with patch(
        "ofertas.services.automacao_service.SessionLocal",
        _session_local(session),
    ):
        servico.executar_coletas_liberadas()

    # Consultou a janela para os dois marketplaces e parou antes das plataformas.
    assert janela_fechada.esta_em_horario_permitido.call_count == 2
    session.scalars.assert_not_called()
    execucao_coleta_service.executar.assert_not_called()
    execucao_coleta_service.executar_shopee.assert_not_called()


# --- publicações ---------------------------------------------------------------


def test_destinos_nao_sao_liberados_fora_da_janela(janela_fechada):
    configuracao_service = Mock()
    configuracao_service.buscar.return_value = _configuracao_sistema()
    configuracao_divulgacao_repository = Mock()

    servico = AutomacaoService(
        configuracao_sistema_service=configuracao_service,
        execucao_coleta_service=Mock(),
        configuracao_divulgacao_repository=configuracao_divulgacao_repository,
        destino_repository=Mock(),
        janela_execucao_service=janela_fechada,
    )

    with patch(
        "ofertas.services.automacao_service.SessionLocal",
        _session_local(MagicMock()),
    ):
        assert servico.listar_destinos_publicacao_liberados() == []

    configuracao_divulgacao_repository.listar.assert_not_called()


def test_ciclo_de_publicacao_retorna_pausado_fora_da_janela(janela_fechada):
    configuracao = Mock(status_configuracao=True)
    destino = Mock(status_destino=True, plataforma_divulgacao_id=1)
    canal = Mock(status_plataforma=True, codigo="telegram")

    session = Mock()
    session.get.side_effect = lambda modelo, _id: (
        _configuracao_sistema()
        if modelo is ConfiguracaoSistema
        else canal
    )

    configuracao_repository = Mock()
    configuracao_repository.buscar_por_destino.return_value = configuracao
    destino_repository = Mock()
    destino_repository.buscar_por_id.return_value = destino

    servico = PublicacaoLoteService(
        configuracao_repository=configuracao_repository,
        destino_repository=destino_repository,
        categoria_repository=Mock(),
        produto_repository=Mock(),
        publicacao_service=Mock(),
        janela_execucao_service=janela_fechada,
    )

    assert servico._buscar_configuracao_ativa(session, 1) is None

    janela_fechada.esta_em_horario_permitido.return_value = True
    assert servico._buscar_configuracao_ativa(session, 1) is configuracao


def test_ciclo_em_andamento_para_quando_a_janela_fecha():
    publicacao_service = Mock()
    servico = PublicacaoLoteService(
        configuracao_repository=Mock(),
        destino_repository=Mock(),
        categoria_repository=Mock(),
        produto_repository=Mock(),
        publicacao_service=publicacao_service,
        janela_execucao_service=Mock(),
    )

    # Ativo ao iniciar o ciclo; fora da janela na checagem antes do 1º envio.
    with (
        patch(
            "ofertas.services.publicacao_lote_service.SessionLocal",
            _session_local(MagicMock()),
        ),
        patch.object(
            servico,
            "_buscar_configuracao_ativa",
            side_effect=[Mock(), None],
        ),
        patch.object(
            servico,
            "_selecionar_candidatos",
            return_value=[(1, "Eletrônicos", 10), (1, "Eletrônicos", 11)],
        ),
        patch.object(servico, "_registrar_execucao"),
    ):
        resultado = servico._executar_ciclo_destino_com_lock(1)

    assert resultado["status"] == "pausado"
    assert resultado["publicadas"] == 0
    publicacao_service.publicar_produto.assert_not_called()


# --- limite global por categoria ---------------------------------------------


def test_limite_global_e_aplicado_a_cada_categoria():
    session = Mock()
    session.get.side_effect = lambda modelo, _id: (
        _configuracao_sistema(limite_produtos_por_categoria=5)
        if modelo is ConfiguracaoSistema
        else Mock(status_plataforma=True)
    )

    configuracao_repository = Mock()
    configuracao_repository.buscar_por_destino.return_value = Mock(
        desconto_minimo_percentual=0,
        preco_minimo=None,
        preco_maximo=None,
    )

    categorias = [
        Mock(id=i, nome_categoria=f"Cat {i}", plataforma_id=1,
             desconto_minimo_percentual=0)
        for i in (1, 2, 3)
    ]
    categoria_repository = Mock()
    categoria_repository.listar_por_destino.return_value = categorias

    produto_repository = Mock()
    produto_repository.listar_candidatos_publicacao.return_value = []

    servico = PublicacaoLoteService(
        configuracao_repository=configuracao_repository,
        destino_repository=Mock(),
        categoria_repository=categoria_repository,
        produto_repository=produto_repository,
        publicacao_service=Mock(),
        janela_execucao_service=Mock(),
    )

    servico._selecionar_candidatos(session, destino_id=1)

    chamadas = produto_repository.listar_candidatos_publicacao.call_args_list
    assert [c.kwargs["categoria_id"] for c in chamadas] == [1, 2, 3]
    assert all(c.kwargs["limite"] == 5 for c in chamadas)
