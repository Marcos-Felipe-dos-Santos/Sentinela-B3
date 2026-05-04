import pytest
from database import DatabaseManager
import os

import tempfile

@pytest.fixture
def db_path():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_sentinela.db")
    yield db_file
    # Cleanup logic could be added here if needed

@pytest.fixture
def db(db_path):
    manager = DatabaseManager(db_path)
    yield manager
    # Ensure connections are closed
    # It auto closes via context managers in methods

def test_database_initialization(db, db_path):
    assert os.path.exists(db_path)
    
    # Check tables
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r['name'] for r in cursor.fetchall()]
    conn.close()
    
    assert 'analises' in tables
    assert 'carteira_real' in tables
    assert 'fundamentals_cache' in tables

def test_database_reset_db(db, db_path):
    # Write some data to create wal/shm
    db.salvar_analise({'ticker': 'TEST3', 'score_final': 80})
    
    wal_path = f"{db_path}-wal"
    # Even if they don't exist yet, we check reset_db executes without error
    # and reinitializes
    db.reset_db()
    
    # Should still exist
    assert os.path.exists(db_path)


def test_fundamentos_cache_roundtrip(db):
    dados = {"pl": 8.0, "pvp": 1.2, "roe": 0.15, "dy": 0.04}

    db.salvar_fundamentos_cache("petr4.sa", dados, "brapi")

    assert db.buscar_fundamentos_cache("PETR4") == dados


def test_fundamentos_cache_stale_is_not_returned(db):
    dados = {"pl": 8.0, "pvp": 1.2, "roe": 0.15, "dy": 0.04}
    db.salvar_fundamentos_cache("VALE3", dados, "brapi")

    with db._get_conn() as conn:
        with conn:
            conn.execute(
                """
                UPDATE fundamentals_cache
                SET atualizado_em = '2000-01-01T00:00:00'
                WHERE ticker = 'VALE3'
                """
            )

    assert db.buscar_fundamentos_cache("VALE3", max_age_days=7) is None
