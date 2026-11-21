from sqlalchemy import text


def _canal_whatsapp(client, db_session):
    existente = db_session.execute(
        text("SELECT id FROM plataformas_divulgacao WHERE codigo = 'whatsapp'")
    ).scalar()
    if existente:
        # O canal pode estar desligado no painel; a transação é desfeita no fim.
        db_session.execute(
            text("UPDATE plataformas_divulgacao SET status_plataforma = true WHERE id = :id"),
            {"id": existente},
        )
        return existente
    resposta = client.post("/canais-divulgacao", json={"codigo": "whatsapp", "nome": "WhatsApp"})
    assert resposta.status_code == 201
    return resposta.json()["id"]


def test_grupo_do_whatsapp_nao_precisa_de_credencial(client, db_session):
    canal_id = _canal_whatsapp(client, db_session)

    resposta = client.post("/grupos", json={
        "plataforma_divulgacao_id": canal_id,
        "identificador_destino": "Ofertas Tech (teste)",
        "nome_destino": "Ofertas Tech (teste)",
    })

    assert resposta.status_code == 201
    assert resposta.json()["credencial_divulgacao_id"] is None


def test_grupo_do_telegram_continua_exigindo_credencial(client, db_session):
    canal_id = db_session.execute(
        text("SELECT id FROM plataformas_divulgacao WHERE codigo = 'telegram'")
    ).scalar()

    resposta = client.post("/grupos", json={
        "plataforma_divulgacao_id": canal_id,
        "identificador_destino": "-100999",
        "nome_destino": "Teste",
    })

    assert resposta.status_code == 409
    assert "token do bot" in resposta.json()["detail"]
