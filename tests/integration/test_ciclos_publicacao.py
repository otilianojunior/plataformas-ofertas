import pytest
from sqlalchemy import select, text

from ofertas.models.ciclo_publicacao import CicloPublicacao
from ofertas.models.execucao_coleta import ExecucaoColeta
from ofertas.models.plataforma import Plataforma
from ofertas.repositories.ciclo_publicacao_repository import (
    CicloPublicacaoRepository,
)


@pytest.fixture
def destino_id(db_session):
    destino = db_session.execute(
        text("SELECT destino_divulgacao_id FROM configuracoes_divulgacao LIMIT 1")
    ).scalar()
    if destino is None:
        pytest.skip("Nenhum destino configurado no banco.")
    return destino


def test_marcar_interrompidos_fecha_ciclos_orfaos(db_session, destino_id):
    repo = CicloPublicacaoRepository()
    orfao = repo.iniciar(db_session, destino_id, 3)

    # >= 1: com a API rodando pode existir também um ciclo real em andamento
    # (a alteração é desfeita no fim do teste).
    assert repo.marcar_interrompidos(db_session, destino_id) >= 1

    db_session.refresh(orfao)
    assert orfao.status == "interrompido"
    assert orfao.finalizado_em is not None


def test_listagem_e_filtros(client, db_session, destino_id):
    repo = CicloPublicacaoRepository()
    concluido = repo.iniciar(db_session, destino_id, 2)
    repo.atualizar(db_session, concluido.id, status="concluido", quantidade_publicada=2)
    repo.iniciar(db_session, destino_id, 5)

    todos = client.get("/ciclos-publicacao", params={"destino_id": destino_id}).json()
    assert todos[0]["status"] == "em_andamento"  # mais recente primeiro
    assert todos[0]["quantidade_candidatos"] == 5

    filtrados = client.get(
        "/ciclos-publicacao",
        params={"destino_id": destino_id, "status": "concluido"},
    ).json()
    assert filtrados and all(c["status"] == "concluido" for c in filtrados)

    assert client.get("/ciclos-publicacao", params={"limite": 1}).json().__len__() == 1
    assert client.get("/ciclos-publicacao", params={"limite": 0}).status_code == 422
    assert client.get("/ciclos-publicacao", params={"status": "x"}).status_code == 422


def test_status_mostra_ciclo_em_andamento(client, db_session, destino_id):
    db_session.execute(
        text("UPDATE configuracoes_sistema SET agendador_ultimo_sinal_em = now() WHERE id = 1")
    )
    db_session.execute(text("DELETE FROM janelas_execucao"))
    ciclo = CicloPublicacaoRepository().iniciar(db_session, destino_id, 4)

    corpo = client.get("/automacoes/status").json()
    destino = next(
        d for d in corpo["destinos_publicacao"] if d["destino_id"] == destino_id
    )

    assert destino["ultimo_ciclo"]["id"] == ciclo.id
    if destino["status"] not in {"pausada", "destino_inativo"}:
        assert destino["ciclo_em_andamento"] is True
        assert destino["status"] == "publicando"
        assert destino["proxima_execucao_em"] is None


def test_banco_aceita_status_parcial(db_session):
    plataforma_id = db_session.scalar(select(Plataforma.id).limit(1))
    execucao = ExecucaoColeta(plataforma_id=plataforma_id, status="parcial")
    db_session.add(execucao)
    db_session.flush()

    assert execucao.id is not None


def test_coleta_no_status_expoe_erro_e_encontradas(client):
    for coleta in client.get("/automacoes/status").json()["coletas"]:
        assert "ultima_execucao_erro" in coleta
        assert "quantidade_encontrada" in coleta
