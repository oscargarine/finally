from app.db.connection import get_connection
from app.db.init import ensure_db_initialized
from app.db.schema import DEFAULT_CASH_BALANCE, DEFAULT_WATCHLIST_TICKERS

TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


def _table_names(conn) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def test_creates_all_tables(tmp_path):
    db_path = tmp_path / "finally.db"
    ensure_db_initialized(db_path)

    conn = get_connection(db_path)
    try:
        assert TABLES <= _table_names(conn)
    finally:
        conn.close()


def test_seeds_default_user_profile(tmp_path):
    db_path = tmp_path / "finally.db"
    ensure_db_initialized(db_path)

    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT id, cash_balance FROM users_profile WHERE id = 'default'").fetchone()
        assert row is not None
        assert row["cash_balance"] == DEFAULT_CASH_BALANCE
    finally:
        conn.close()


def test_seeds_default_watchlist(tmp_path):
    db_path = tmp_path / "finally.db"
    ensure_db_initialized(db_path)

    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT ticker FROM watchlist WHERE user_id = 'default'").fetchall()
        tickers = {row["ticker"] for row in rows}
        assert tickers == set(DEFAULT_WATCHLIST_TICKERS)
        assert len(rows) == len(DEFAULT_WATCHLIST_TICKERS)
    finally:
        conn.close()


def test_is_idempotent_and_does_not_reset_existing_state(tmp_path):
    db_path = tmp_path / "finally.db"
    ensure_db_initialized(db_path)

    conn = get_connection(db_path)
    try:
        conn.execute("UPDATE users_profile SET cash_balance = 42.0 WHERE id = 'default'")
        conn.commit()
    finally:
        conn.close()

    ensure_db_initialized(db_path)

    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT cash_balance FROM users_profile WHERE id = 'default'").fetchone()
        assert row["cash_balance"] == 42.0

        watchlist_rows = conn.execute("SELECT ticker FROM watchlist").fetchall()
        assert len(watchlist_rows) == len(DEFAULT_WATCHLIST_TICKERS)
    finally:
        conn.close()


def test_trades_side_check_constraint(tmp_path):
    db_path = tmp_path / "finally.db"
    ensure_db_initialized(db_path)

    conn = get_connection(db_path)
    try:
        try:
            conn.execute(
                "INSERT INTO trades (id, ticker, side, quantity, price, executed_at) "
                "VALUES ('1', 'AAPL', 'hold', 1.0, 1.0, 'now')"
            )
            conn.commit()
            assert False, "expected CHECK constraint violation"
        except Exception:
            pass
    finally:
        conn.close()
