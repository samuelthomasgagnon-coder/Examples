import os
import sqlite3
import tempfile
from Server.DB_manager import DBmanager


def test_db_setup_and_insert(tmp_path, monkeypatch):
    # Point DB paths to a temp directory
    tmp_dir = tmp_path / 'server' / 'data'
    (tmp_dir / 'images').mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)

    mgr = DBmanager()
    # Verify table exists
    cur = mgr.state['DB_cusor']
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='smiles'")
    assert cur.fetchone() is not None

    # Insert a row
    mgr.log_smilemeta_to_db(face_id=1)
    cur.execute("SELECT COUNT(*) FROM smiles")
    count = cur.fetchone()[0]
    assert count >= 1

    mgr.cleanup_resources()


