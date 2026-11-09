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



class RefundRejected(Exception):
    """A refund confirmation failed a safety check."""


def redeem_token(token, txn_id, amount_minor, role, reason, txn_amount):
    """Atomically consume a confirmation token and record the refund.

    Everything happens inside one database transaction, so two simultaneous
    confirmations of the same token cannot both succeed.
    Returns (refund_id, created_at).
    """
    now = datetime.now(timezone.utc)
    con = connect_ops()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT txn_id, amount_minor, role, reason, expires_at, used "
            "FROM refund_tokens WHERE token = ?",
            (token,),
        ).fetchone()
        # One generic message for unknown token and mismatched arguments,
        # so the error does not tell an attacker which part was wrong.
        if row is None or row[:4] != (txn_id, amount_minor, role, reason):
            raise RefundRejected("Confirmation token is invalid for this refund.")
        if row[5]:
            raise RefundRejected("Confirmation token has already been used.")
        if _iso(now) > row[4]:
            raise RefundRejected("Confirmation token has expired. Run a new dry run.")

        already = con.execute(
            "SELECT COALESCE(SUM(amount_minor), 0) FROM refunds WHERE txn_id = ?",
            (txn_id,),
        ).fetchone()[0]
        if already + amount_minor > txn_amount:
            raise RefundRejected(
                f"Refund would exceed the original payment of {txn_amount} "
                f"({already} already refunded)."
            )

        changed = con.execute(
            "UPDATE refund_tokens SET used = 1 WHERE token = ? AND used = 0", (token,)
        ).rowcount
        if changed != 1:
            raise RefundRejected("Confirmation token has already been used.")
        cur = con.execute(
            "INSERT INTO refunds (txn_id, amount_minor, role, reason, created_at) "
            "VALUES (?,?,?,?,?)",
            (txn_id, amount_minor, role, reason, _iso(now)),
        )
        con.commit()
        return cur.lastrowid, _iso(now)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()