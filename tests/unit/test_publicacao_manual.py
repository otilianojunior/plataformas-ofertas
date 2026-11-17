"""Publicação manual em todos os grupos da categoria do produto."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from ofertas.models.destino_divulgacao import DestinoDivulgacao
from ofertas.models.plataforma_divulgacao import PlataformaDivulgacao
from ofertas.models.publicacao import Publicacao
from ofertas.services.publicacao_service import PublicacaoService


AGORA = datetime(2026, 11, 17, tzinfo=timezone.utc)


def _publicacao(destino_id, status="publicada", erro=None):
    return Publicacao(
        id=100 + destino_id, produto_id=1, destino_divulgacao_id=destino_id,
        preco_divulgado=Decimal("10"), percentual_desconto_divulgado=Decimal("30"),
        status_publicacao=status, tentativas=1, publicada_em=AGORA, erro=erro,
        created_at=AGORA, updated_at=AGORA,
    )


@pytest.fixture
def cenario():
    """Grupos 1 e 2 no Telegram ativo, 3 inativo, 4 em canal inativo, 5 WhatsApp."""
    canais = {
        10: PlataformaDivulgacao(id=10, codigo="telegram", status_plataforma=True),
        20: PlataformaDivulgacao(id=20, codigo="telegram", status_plataforma=False),
        30: PlataformaDivulgacao(id=30, codigo="whatsapp", status_plataforma=True),
    }
    destinos = {
        1: DestinoDivulgacao(id=1, nome_destino="G1", plataforma_divulgacao_id=10, status_destino=True),
        2: DestinoDivulgacao(id=2, nome_destino="G2", plataforma_divulgacao_id=10, status_destino=True),
        3: DestinoDivulgacao(id=3, nome_destino="G3", plataforma_divulgacao_id=10, status_destino=False),
        4: DestinoDivulgacao(id=4, nome_destino="G4", plataforma_divulgacao_id=20, status_destino=True),
        5: DestinoDivulgacao(id=5, nome_destino="G5", plataforma_divulgacao_id=30, status_destino=True),
    }
    session = Mock()
    session.get.side_effect = lambda modelo, i: (
        destinos.get(i) if modelo is DestinoDivulgacao else canais.get(i)
    )

    categoria_repository = Mock()
    categoria_repository.listar_destinos_ids.return_value = [1, 2, 3, 4, 5]
    produto_repository = Mock()
    produto_repository.buscar_por_id.return_value = Mock(id=1)

    servico = PublicacaoService(
        produto_repository=produto_repository,
        categoria_repository=categoria_repository,
        publicacao_repository=Mock(),
        configuracao_repository=Mock(),
        telegram_publisher=Mock(),
    )
    servico._buscar_categoria = Mock(
        return_value=Mock(id=7, nome_categoria="Teclados")
    )
    return servico, session


def test_publica_em_cada_grupo_ativo_e_explica_os_ignorados(cenario):
    servico, session = cenario

    def publicar(_session, _produto_id, destino_id):
        if destino_id == 5:
            raise ValueError("O publisher do WhatsApp ainda não foi implementado.")
        return _publicacao(destino_id)

    servico.publicar_produto = Mock(side_effect=publicar)

    resumo = servico.publicar_em_todos_destinos(session, 1)

    por_destino = {r["destino_id"]: r for r in resumo["resultados"]}
    assert por_destino[1]["status"] == por_destino[2]["status"] == "publicada"
    assert por_destino[3]["motivo"] == "O grupo está inativo."
    assert por_destino[4]["motivo"] == "O canal de divulgação está inativo."
    assert "WhatsApp" in por_destino[5]["motivo"]
    assert (resumo["publicadas"], resumo["falhas"], resumo["ignoradas"]) == (2, 0, 3)

    # só tenta publicar onde canal e grupo estão ativos
    tentados = [c.kwargs["destino_id"] for c in servico.publicar_produto.call_args_list]
    assert tentados == [1, 2, 5]
    assert session.commit.call_count == 2  # um commit por envio concluído


def test_regra_violada_em_um_grupo_nao_impede_os_outros(cenario):
    servico, session = cenario

    def publicar(_session, _produto_id, destino_id):
        if destino_id == 1:
            raise ValueError("O produto já foi publicado neste grupo há menos de 24 horas.")
        if destino_id == 2:
            return _publicacao(2, status="falhou", erro="Telegram: chat not found")
        raise ValueError("outro")

    servico.publicar_produto = Mock(side_effect=publicar)

    resumo = servico.publicar_em_todos_destinos(session, 1)
    por_destino = {r["destino_id"]: r for r in resumo["resultados"]}

    assert por_destino[1]["status"] == "ignorada"
    assert "24 horas" in por_destino[1]["motivo"]
    assert por_destino[2]["status"] == "falhou"
    assert por_destino[2]["motivo"] == "Telegram: chat not found"
    assert session.rollback.call_count >= 1


def test_erro_inesperado_vira_falha_do_grupo(cenario):
    servico, session = cenario
    servico.publicar_produto = Mock(side_effect=[RuntimeError("timeout"), _publicacao(2), ValueError("x")])

    resumo = servico.publicar_em_todos_destinos(session, 1)

    assert resumo["resultados"][0]["status"] == "falhou"
    assert resumo["publicadas"] == 1


def test_categoria_sem_grupos(cenario):
    servico, session = cenario
    servico.categoria_repository.listar_destinos_ids.return_value = []

    with pytest.raises(ValueError, match="não possui grupos"):
        servico.publicar_em_todos_destinos(session, 1)


def test_produto_inexistente(cenario):
    servico, session = cenario
    servico.produto_repository.buscar_por_id.return_value = None

    with pytest.raises(LookupError):
        servico.publicar_em_todos_destinos(session, 1)
