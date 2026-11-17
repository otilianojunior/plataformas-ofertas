"""Códigos HTTP da publicação manual (serviço simulado: nada é enviado)."""

import pytest

from ofertas.api import publicacoes


def _resumo(publicadas=0, falhas=0, ignoradas=0):
    resultados = (
        [{"destino_id": 1, "nome_destino": "G", "codigo_canal": "telegram",
          "status": "publicada", "motivo": None, "publicacao": None}] * publicadas
        + [{"destino_id": 2, "nome_destino": "G", "codigo_canal": "telegram",
            "status": "falhou", "motivo": "erro", "publicacao": None}] * falhas
        + [{"destino_id": 3, "nome_destino": "G", "codigo_canal": "whatsapp",
            "status": "ignorada", "motivo": "motivo", "publicacao": None}] * ignoradas
    )
    return {
        "produto_id": 1, "categoria_id": 7, "nome_categoria": "Teclados",
        "total_destinos": len(resultados), "publicadas": publicadas,
        "falhas": falhas, "ignoradas": ignoradas, "resultados": resultados,
    }


@pytest.mark.parametrize(
    ("resumo", "esperado"),
    [
        (_resumo(publicadas=1, ignoradas=1), 200),
        (_resumo(publicadas=1, falhas=1), 200),
        (_resumo(falhas=1, ignoradas=1), 502),
        (_resumo(ignoradas=2), 409),
    ],
)
def test_codigos_de_resposta(client, monkeypatch, resumo, esperado):
    monkeypatch.setattr(
        publicacoes.service, "publicar_em_todos_destinos", lambda db, pid: resumo
    )

    resposta = client.post("/publicacoes/produtos/1")

    assert resposta.status_code == esperado
    corpo = resposta.json()
    resultados = corpo["resultados"] if esperado == 200 else corpo["detail"]["resultados"]
    assert len(resultados) == resumo["total_destinos"]


def test_produto_inexistente_retorna_404(client):
    assert client.post("/publicacoes/produtos/999999").status_code == 404
