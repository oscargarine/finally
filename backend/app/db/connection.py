import os
import sqlite3
from pathlib import Path

# Raíz del proyecto = tres niveles por encima de este archivo (app/db/connection.py
# -> app/db -> app -> backend -> raíz), coherente con backend/db/ en planning/PLAN.md §4.
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "db" / "finally.db"


def resolve_db_path() -> Path:
    override = os.environ.get("DB_PATH", "").strip()
    return Path(override) if override else _DEFAULT_DB_PATH


def get_connection(path: str | Path | None = None) -> sqlite3.Connection:
    """Abre una conexión SQLite con WAL y claves foráneas activas (ver PLAN.md §7)."""
    resolved = Path(path) if path is not None else resolve_db_path()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
