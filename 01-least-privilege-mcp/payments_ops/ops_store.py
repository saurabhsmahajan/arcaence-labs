"""Server-owned state: refund confirmation tokens and executed refunds.

This is a separate database from payments.db. The payments data stays
read-only; the only thing this server can ever write is its own ops.db.
"""
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

OPS_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ops.db"
TOKEN_TTL_MINUTES = 10

OPS_SCHEMA = """
CREATE TABLE IF NOT EXISTS refund_tokens (
    token        TEXT PRIMARY KEY,
    txn_id       TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    role         TEXT NOT NULL,
    reason       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    expires_at   TEXT NOT NULL,
    used         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id       TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    role         TEXT NOT NULL,
    reason       TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
"""


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def connect_ops():
    """Open the server's own read-write database (created on first use)."""
    OPS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(OPS_DB_PATH)
    con.executescript(OPS_SCHEMA)
    return con


def create_token(txn_id, amount_minor, role, reason):
    """Store a single-use confirmation token bound to exactly this refund."""
    token = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=TOKEN_TTL_MINUTES)
    con = connect_ops()
    try:
        con.execute(
            "INSERT INTO refund_tokens "
            "(token, txn_id, amount_minor, role, reason, created_at, expires_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (token, txn_id, amount_minor, role, reason, _iso(now), _iso(expires)),
        )
        con.commit()
    finally:
        con.close()
    return token, _iso(expires)