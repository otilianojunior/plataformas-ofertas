"""Testes de integração contra o PostgreSQL configurado no `.env`.

Cada teste roda dentro de uma transação que é desfeita ao final
(`join_transaction_mode="create_savepoint"`): os `commit()` das rotas viram
savepoints e nada é gravado no banco. O `lifespan` da API não é executado,
então os monitores de coleta/publicação não são iniciados.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ofertas.db.session import engine, get_db
from ofertas.main import app


@pytest.fixture(scope="session")
def conexao_disponivel():
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL indisponível: {exc}")


@pytest.fixture
def db_session(conexao_disponivel):
    conexao = engine.connect()
    transacao = conexao.begin()
    session = Session(
        bind=conexao,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transacao.rollback()
        conexao.close()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)  # sem `with`: o lifespan não roda
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sem_janelas(db_session):
    """Remove (dentro da transação) janelas existentes para isolar o teste."""
    db_session.execute(text("DELETE FROM janelas_execucao"))
    db_session.flush()
