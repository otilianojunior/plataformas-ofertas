from collections import Counter
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from ofertas.services.janela_execucao_service import JanelaExecucaoService
from ofertas.services.publicacao_lote_service import PublicacaoLoteService


SP = ZoneInfo("America/Sao_Paulo")

# Status que antecedem a checagem de janela na regra de prioridade.
STATUS_COLETA_ANTERIORES = {
    "plataforma_nao_cadastrada", "executando", "pausada", "plataforma_inativa",
}
# "publicando" também vem antes da janela: com a API rodando, pode haver um
# ciclo real em andamento.
STATUS_DESTINO_ANTERIORES = {"pausada", "destino_inativo", "publicando"}

pytestmark = pytest.mark.usefixtures("sem_janelas")


def _janela_fora_de_agora() -> tuple[str, str]:
    agora = datetime.now(SP)
    if agora.hour < 22:
        return f"{agora.hour + 1:02d}:00", f"{agora.hour + 2:02d}:00"
    return "01:00", "02:00"


def _janela_com_agora() -> tuple[str, str]:
    agora = datetime.now(SP)
    inicio = max(agora - timedelta(minutes=30), agora.replace(hour=0, minute=0, second=0))
    fim = min(agora + timedelta(minutes=30), agora.replace(hour=23, minute=59, second=59))
    return inicio.strftime("%H:%M:%S"), fim.strftime("%H:%M:%S")


def _monitor_online(db_session):
    db_session.execute(
        text("UPDATE configuracoes_sistema SET agendador_ultimo_sinal_em = now() WHERE id = 1")
    )
    db_session.flush()


def test_estrutura_do_status(client):
    resposta = client.get("/automacoes/status")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["fuso_horario"] == "America/Sao_Paulo"
    assert corpo["horario_permitido"] is True  # sem janelas: 24h liberado
    assert {c["codigo"] for c in corpo["coletas"]} == {"mercado_livre", "shopee"}
    assert corpo["monitor"]["limite_sinal_minutos"] == 3
    assert corpo["publicacao_whatsapp_status"] in {"ativa", "pausada"}


def test_monitor_offline_sem_sinal_recente(client, db_session):
    db_session.execute(
        text(
            "UPDATE configuracoes_sistema "
            "SET agendador_ultimo_sinal_em = now() - interval '10 minutes' WHERE id = 1"
        )
    )
    db_session.flush()

    corpo = client.get("/automacoes/status").json()

    assert corpo["monitor"]["online"] is False
    for coleta in corpo["coletas"]:
        if coleta["status"] not in STATUS_COLETA_ANTERIORES:
            assert coleta["status"] == "monitor_offline"
            assert coleta["proxima_execucao_em"] is None


def test_fora_da_janela(client, db_session):
    _monitor_online(db_session)
    inicio, fim = _janela_fora_de_agora()
    assert client.post(
        "/janelas-execucao", json={"hora_inicio": inicio, "hora_fim": fim}
    ).status_code == 201

    corpo = client.get("/automacoes/status").json()

    assert corpo["horario_permitido"] is False
    assert JanelaExecucaoService().esta_em_horario_permitido(db_session) is False

    hora_inicio = time.fromisoformat(inicio)
    for coleta in corpo["coletas"]:
        if coleta["status"] in STATUS_COLETA_ANTERIORES:
            continue
        assert coleta["status"] == "fora_da_janela"
        proxima = datetime.fromisoformat(coleta["proxima_execucao_em"])
        assert proxima.astimezone(SP).time() >= hora_inicio
        assert proxima > datetime.now(timezone.utc)

    for destino in corpo["destinos_publicacao"]:
        if destino["codigo_canal"] != "telegram":
            continue
        if destino["status"] in STATUS_DESTINO_ANTERIORES:
            continue
        assert destino["status"] == "fora_da_janela"


def test_dentro_da_janela(client, db_session):
    _monitor_online(db_session)
    inicio, fim = _janela_com_agora()
    assert client.post(
        "/janelas-execucao", json={"hora_inicio": inicio, "hora_fim": fim}
    ).status_code == 201

    corpo = client.get("/automacoes/status").json()

    assert corpo["horario_permitido"] is True
    for coleta in corpo["coletas"]:
        assert coleta["status"] != "fora_da_janela"


def test_janela_inativa_nao_bloqueia(client, db_session):
    inicio, fim = _janela_fora_de_agora()
    client.post(
        "/janelas-execucao",
        json={"hora_inicio": inicio, "hora_fim": fim, "ativa": False},
    )

    assert client.get("/automacoes/status").json()["horario_permitido"] is True


def test_limite_global_limita_cada_categoria(client, db_session):
    destino_ids = db_session.execute(
        text("SELECT destino_divulgacao_id FROM configuracoes_divulgacao")
    ).scalars().all()
    if not destino_ids:
        pytest.skip("Nenhum destino configurado no banco.")

    servico = PublicacaoLoteService()

    for limite in (5, 1):
        assert client.patch(
            "/configuracoes-sistema",
            json={"limite_produtos_por_categoria": limite},
        ).status_code == 200

        for destino_id in destino_ids:
            candidatos = servico._selecionar_candidatos(db_session, destino_id)
            por_categoria = Counter(c[0] for c in candidatos)
            assert all(qtd <= limite for qtd in por_categoria.values()), (
                destino_id, limite, por_categoria,
            )
