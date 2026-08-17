import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .connection import get_connection
from .schema import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST_TICKERS,
    SCHEMA_SQL,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_defaults(conn: sqlite3.Connection) -> None:
    # INSERT OR IGNORE + las restricciones PRIMARY KEY/UNIQUE del esquema hacen
    # que sembrar sea seguro de repetir (PLAN.md §7).
    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, _now()),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        [
            (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, _now())
            for ticker in DEFAULT_WATCHLIST_TICKERS
        ],
    )


def ensure_db_initialized(path: str | Path | None = None) -> None:
    """Crea el esquema y siembra los datos por defecto si hace falta (PLAN.md §7).

    Debe llamarse una única vez, dentro del `lifespan` de FastAPI, antes de aceptar
    tráfico. Es idempotente: puede llamarse repetidamente sin efectos adicionales.
    """
    conn = get_connection(path)
    try:
        with conn:
            conn.executescript(SCHEMA_SQL)
            _seed_defaults(conn)
    finally:
        conn.close()
