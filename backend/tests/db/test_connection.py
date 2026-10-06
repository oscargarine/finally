from pathlib import Path

import pytest

from app.db.connection import get_connection, resolve_db_path


def test_resolve_db_path_defaults_to_project_db_dir() -> None:
    path = resolve_db_path()
    assert path.name == "finally.db"
    assert path.parent.name == "db"


def test_resolve_db_path_respects_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    override = tmp_path / "custom" / "finally.db"
    monkeypatch.setenv("DB_PATH", str(override))

    assert resolve_db_path() == override


def test_get_connection_creates_parent_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "finally.db"

    conn = get_connection(db_path)
    try:
        assert db_path.parent.is_dir()
    finally:
        conn.close()


def test_get_connection_enables_wal_and_foreign_keys(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "finally.db")
    try:
        (journal_mode,) = conn.execute("PRAGMA journal_mode").fetchone()
        (foreign_keys,) = conn.execute("PRAGMA foreign_keys").fetchone()
        assert journal_mode.lower() == "wal"
        assert foreign_keys == 1
    finally:
        conn.close()


def test_get_connection_uses_row_factory(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "finally.db")
    try:
        conn.execute("CREATE TABLE t (a INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        row = conn.execute("SELECT a FROM t").fetchone()
        assert row["a"] == 1
    finally:
        conn.close()
