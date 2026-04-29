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

def test_database_reset_db(db, db_path):
    # Write some data to create wal/shm
    db.salvar_analise({'ticker': 'TEST3', 'score_final': 80})
    
    wal_path = f"{db_path}-wal"
    # Even if they don't exist yet, we check reset_db executes without error
    # and reinitializes
    db.reset_db()
    
    # Should still exist
    assert os.path.exists(db_path)
