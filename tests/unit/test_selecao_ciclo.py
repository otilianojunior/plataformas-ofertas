"""Rodízio entre categorias, limite por ciclo e prioridade dos mais vendidos."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from ofertas.repositories.produto_repository import PESO_POPULARIDADE, pontuacao_publicacao
from ofertas.services.publicacao_lote_service import PublicacaoLoteService


def _vagas(categoria_id, *produtos):
    return [[categoria_id, f"Cat {categoria_id}", SimpleNamespace(id=p)] for p in produtos]


AGORA = datetime.now(timezone.utc)


def test_alterna_categorias_e_comeca_pela_publicada_ha_mais_tempo():
    selecionados = _vagas(1, 11, 12, 13) + _vagas(2, 21, 22) + _vagas(3, 31)
    ultima = {1: AGORA, 2: AGORA - timedelta(hours=5)}  # 3 nunca publicada

    ordem = PublicacaoLoteService._intercalar_categorias(selecionados, ultima, None)

    assert [p for _, _, p in ordem] == [31, 21, 11, 22, 12, 13]


def test_limite_do_ciclo_corta_depois_do_rodizio():
    selecionados = _vagas(1, 11, 12, 13) + _vagas(2, 21, 22) + _vagas(3, 31)

    ordem = PublicacaoLoteService._intercalar_categorias(selecionados, {}, 4)

    # Uma de cada categoria antes de repetir alguma.
    assert sorted(c for c, _, _ in ordem[:3]) == [1, 2, 3]
    assert len(ordem) == 4


def test_pontuacao_soma_desconto_e_bonus_de_popularidade():
    sql = str(pontuacao_publicacao().compile(dialect=postgresql.dialect()))
    assert "sqrt" in sql and "coalesce" in sql
    # 1º lugar ganha o peso inteiro; 4º, metade.
    assert PESO_POPULARIDADE / 1**0.5 == 40 and PESO_POPULARIDADE / 4**0.5 == 20


def test_mensagens_sao_espalhadas_pelo_intervalo():
    # 10 mensagens em 30 min: uma a cada 162s, terminando antes do próximo ciclo.
    assert PublicacaoLoteService._espacamento(20, 30, 10) == 162
    assert 10 * 162 < 30 * 60
    # Muitos candidatos: nunca abaixo do mínimo do canal.
    assert PublicacaoLoteService._espacamento(20, 30, 500) == 20
    # Sem intervalo configurado ou uma mensagem só: o mínimo.
    assert PublicacaoLoteService._espacamento(20, None, 10) == 20
    assert PublicacaoLoteService._espacamento(120, 30, 1) == 120


def test_preco_vencido_nao_e_publicado():
    from unittest.mock import Mock

    import pytest

    from ofertas.services.publicacao_service import PublicacaoService

    produto = Mock(ultima_coleta_em=AGORA - timedelta(hours=26))
    with pytest.raises(ValueError, match="Preço não confirmado há 26"):
        PublicacaoService._validar_elegibilidade(Mock(), produto, Mock(), Mock(), 120)


def test_selecao_so_busca_precos_dentro_da_validade():
    sql_sem = _consulta_candidatos(None)
    sql_com = _consulta_candidatos(AGORA - timedelta(minutes=120))
    assert "ultima_coleta_em" not in sql_sem.split("WHERE", 1)[1].split("ORDER BY")[0]
    assert "produtos.ultima_coleta_em >=" in sql_com


def _consulta_candidatos(coletado_desde):
    from unittest.mock import Mock

    from ofertas.repositories.produto_repository import ProdutoRepository

    session = Mock()
    session.scalars.return_value.all.return_value = []
    ProdutoRepository().listar_candidatos_publicacao(
        session, categoria_id=1, destino_id=1, desconto_minimo_percentual=0, coletado_desde=coletado_desde
    )
    consulta = session.scalars.call_args.args[0]
    return str(consulta.compile(dialect=postgresql.dialect()))


def test_favoritas_entram_primeiro_em_cada_rodada():
    selecionados = _vagas(1, 11, 12) + _vagas(2, 21, 22) + _vagas(3, 31, 32)
    ultima = {1: AGORA - timedelta(hours=9), 2: AGORA, 3: AGORA - timedelta(hours=1)}

    ordem = PublicacaoLoteService._intercalar_categorias(selecionados, ultima, None, favoritas={2})

    # A favorita (2) abre cada rodada; as demais seguem pelo rodízio.
    assert [p for _, _, p in ordem] == [21, 11, 31, 22, 12, 32]


def test_favorita_garante_vaga_mesmo_com_teto_baixo():
    selecionados = _vagas(1, 11) + _vagas(2, 21) + _vagas(3, 31)

    ordem = PublicacaoLoteService._intercalar_categorias(selecionados, {}, 1, favoritas={3})

    assert [p for _, _, p in ordem] == [31]


def test_links_afiliados_so_para_publicaveis_e_melhores_primeiro():
    from unittest.mock import Mock

    from ofertas.repositories.produto_repository import ProdutoRepository

    session = Mock()
    session.execute.return_value.all.return_value = []
    ProdutoRepository().listar_pendentes_para_geracao_afiliado(session, 2, limite=25, excluir_ids=[7])
    sql = str(session.execute.call_args.args[0].compile(dialect=postgresql.dialect()))

    assert "produtos.percentual_desconto >= plataforma_categoria.desconto_minimo_percentual" in sql
    assert "produtos.percentual_desconto <=" in sql and "produtos.disponivel IS true" in sql
    assert "NOT IN" in sql and "LIMIT" in sql and "sqrt" in sql
