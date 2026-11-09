"""SQLite schema for the synthetic merchant-payments system.

Money is stored as integer minor units to avoid float rounding errors.
Timestamps are ISO-8601 UTC strings.
Ground-truth exception labels are deliberately NOT in this database;
they live in a separate file the MCP server can never read.
"""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE merchants (
    merchant_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    country     TEXT NOT NULL,
    currency    TEXT NOT NULL
);

CREATE TABLE transactions (
    txn_id       TEXT PRIMARY KEY,
    merchant_id  TEXT NOT NULL REFERENCES merchants(merchant_id),
    amount_minor INTEGER NOT NULL,
    currency     TEXT NOT NULL,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE psp_events (
    event_id      TEXT PRIMARY KEY,
    txn_id        TEXT NOT NULL REFERENCES transactions(txn_id),
    event_type    TEXT NOT NULL,
    amount_minor  INTEGER NOT NULL,
    occurred_at   TEXT NOT NULL,
    psp_reference TEXT NOT NULL
);

CREATE TABLE ledger_entries (
    entry_id     TEXT PRIMARY KEY,
    txn_id       TEXT NOT NULL REFERENCES transactions(txn_id),
    account      TEXT NOT NULL,
    direction    TEXT NOT NULL CHECK (direction IN ('debit', 'credit')),
    amount_minor INTEGER NOT NULL,
    posted_at    TEXT NOT NULL
);

CREATE TABLE settlement_batches (
    batch_id    TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL REFERENCES merchants(merchant_id),
    cutoff_at   TEXT NOT NULL,
    total_minor INTEGER NOT NULL
);

CREATE TABLE settlement_items (
    batch_id     TEXT NOT NULL REFERENCES settlement_batches(batch_id),
    txn_id       TEXT NOT NULL REFERENCES transactions(txn_id),
    amount_minor INTEGER NOT NULL,
    PRIMARY KEY (batch_id, txn_id)
);
"""


def create_db(path="data/payments.db"):
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    con.commit()
    con.close()
    return db_path


if __name__ == "__main__":
    p = create_db()
    con = sqlite3.connect(p)
    names = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    print(f"Created {p} with tables: {names}")
    con.close()