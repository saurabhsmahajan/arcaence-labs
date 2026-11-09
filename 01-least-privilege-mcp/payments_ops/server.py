"""Least-privilege payments-ops MCP server (scoped version)."""
import sqlite3
from pathlib import Path
from typing import Annotated

from pydantic import Field

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from payments_ops.policy import ROLE_LIMITS, current_role, refund_limit

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "payments.db"

mcp = MCPServer("payments-ops")
TxnId = Annotated[
    str,
    Field(pattern=r"^txn_\d{6}$", description="Transaction ID, for example 'txn_000123'"),
]

def _connect():
    """Open the database read-only: even a bug in a tool cannot write."""
    return sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)


@mcp.tool()
def get_transaction(txn_id: TxnId) -> dict:
    """Look up one transaction by its ID, for example 'txn_000123'.

    Returns the merchant, amount in minor units (for example paise or cents),
    currency, status and creation time. Read-only. Does not return PSP events
    or ledger entries.
    """
    con = _connect()
    try:
        row = con.execute(
            "SELECT txn_id, merchant_id, amount_minor, currency, status, created_at "
            "FROM transactions WHERE txn_id = ?",
            (txn_id,),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise ToolError(f"No transaction found with id {txn_id!r}")
    keys = ("txn_id", "merchant_id", "amount_minor", "currency", "status", "created_at")
    return dict(zip(keys, row))

@mcp.tool()
def get_payment_events(txn_id: TxnId) -> list[dict]:
    """List the payment provider (PSP) events for one transaction, oldest first.

    Each event has an event ID, type (for example authorization, capture,
    refund_requested), amount in minor units, timestamp and PSP reference.
    Read-only. Use get_transaction first to confirm the transaction exists.
    """
    con = _connect()
    try:
        rows = con.execute(
            "SELECT event_id, event_type, amount_minor, occurred_at, psp_reference "
            "FROM psp_events WHERE txn_id = ? ORDER BY occurred_at, event_id",
            (txn_id,),
        ).fetchall()
    finally:
        con.close()
    if not rows:
        raise ToolError(f"No PSP events found for transaction {txn_id!r}")
    keys = ("event_id", "event_type", "amount_minor", "occurred_at", "psp_reference")
    return [dict(zip(keys, r)) for r in rows]

@mcp.resource("payments://policy/refund-limits")
def refund_limits() -> dict:
    """Refund limits per role (minor units), plus the role this server is running as."""
    return {
        "limits_minor_units": ROLE_LIMITS,
        "your_role": current_role(),
        "your_limit_minor_units": refund_limit(),
    }

if __name__ == "__main__":
    mcp.run()