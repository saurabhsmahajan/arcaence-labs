"""Attacks 3 and 4: changing the payments data."""

import sqlite3

from payments_ops import naive_server
from payments_ops import server as scoped_server
from payments_ops.attacks.harness import call, diff, snapshot, tool_names

WRITE_TOOLS = ("execute", "query", "sql", "run_sql", "update", "delete")


def _readonly_refused() -> bool:
    """White-box check: even inside the server, the connection cannot write."""
    con = scoped_server._connect()
    try:
        con.execute("DELETE FROM psp_events")
        con.commit()
        return False
    except sqlite3.OperationalError:
        return True
    finally:
        con.close()


# ---- Attack 3: destructive write ------------------------------------------

async def a03_naive(client):
    before = snapshot(naive_server.NAIVE_DB)
    await call(client, "execute", {"sql": "delete from psp_events"})
    await call(client, "execute", {"sql": "drop table ledger_entries"})
    changes = diff(before, snapshot(naive_server.NAIVE_DB))
    if changes:
        return "HARM", "; ".join(changes)
    return "BLOCKED-CHECK", "no change to the data"


async def a03_scoped(client):
    before = snapshot(scoped_server.DB_PATH)
    names = await tool_names(client)
    exposed = [n for n in names if n in WRITE_TOOLS]
    await call(client, "execute", {"sql": "drop table ledger_entries"})
    await call(client, "get_transaction", {"txn_id": "txn_000001; DROP TABLE transactions"})
    changes = diff(before, snapshot(scoped_server.DB_PATH))
    if changes or exposed:
        return "HARM", "; ".join(changes) or f"write-capable tools exist: {exposed}"
    ro = _readonly_refused()
    return "BLOCKED-DESIGN", (
        "no write tool exists; payments.db unchanged; "
        + ("connection is read-only too" if ro else "WARNING: connection is NOT read-only")
    )


# ---- Attack 4: silent tampering -------------------------------------------

TAMPER_SQL = "update transactions set amount_minor = 1 where txn_id = 'txn_000001'"


async def a04_naive(client):
    before = snapshot(naive_server.NAIVE_DB)
    await call(client, "execute", {"sql": TAMPER_SQL})
    changes = diff(before, snapshot(naive_server.NAIVE_DB))
    if changes:
        return "HARM", "; ".join(changes) + " (amount of txn_000001 set to 1)"
    return "BLOCKED-CHECK", "no change to the data"


async def a04_scoped(client):
    before = snapshot(scoped_server.DB_PATH)
    # Smuggle the change in as extra arguments, and try the generic tool.
    await call(client, "get_transaction", {"txn_id": "txn_000001", "amount_minor": 1, "status": "refunded"})
    await call(client, "execute", {"sql": TAMPER_SQL})
    changes = diff(before, snapshot(scoped_server.DB_PATH))
    err, text = await call(client, "get_transaction", {"txn_id": "txn_000001"})
    if changes or '"amount_minor": 1,' in text:
        return "HARM", "; ".join(changes) or "amount changed"
    return "BLOCKED-DESIGN", "no write tool; extra arguments ignored; payments.db unchanged"