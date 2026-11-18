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
