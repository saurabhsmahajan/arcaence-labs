"""Shared plumbing for running the same attack against both servers."""

import os
from contextlib import asynccontextmanager
import shutil

from mcp import Client

from payments_ops import naive_server
from payments_ops import server as scoped_server
from payments_ops.ops_store import OPS_DB_PATH


@asynccontextmanager
async def naive_session():
    """Fresh copy of the data, then a client connected to the naive server."""
    shutil.copyfile(naive_server.SOURCE_DB, naive_server.NAIVE_DB)
    async with Client(naive_server.mcp) as client:
        yield client


@asynccontextmanager
async def scoped_session(role: str = "support_agent"):
    """Fresh ops state, role fixed 'at launch', client connected to the scoped server."""
    os.environ["PAYMENTS_OPS_ROLE"] = role
    if OPS_DB_PATH.exists():
        OPS_DB_PATH.unlink()
    async with Client(scoped_server.mcp) as client:
        yield client


async def call(client, tool: str, args: dict) -> tuple[bool, str]:
    """Call a tool and never raise. Returns (is_error, text)."""
    try:
        result = await client.call_tool(tool, args)
    except Exception as exc:  # unknown tool, protocol error, etc.
        return True, f"{type(exc).__name__}: {exc}"
    text = " | ".join(getattr(block, "text", "") for block in result.content)
    return bool(result.is_error), text


async def tool_names(client) -> list[str]:
    return [t.name for t in (await client.list_tools()).tools]



# ---- state snapshots: how we measure harm to the payments data -------------

import hashlib
import sqlite3
from pathlib import Path


def snapshot(db_path: Path) -> dict[str, tuple[int, str]]:
    """Per table: (row count, SHA-256 of all rows). Read-only; changes nothing."""
    con = sqlite3.connect(f"{Path(db_path).as_uri()}?mode=ro", uri=True)
    try:
        tables = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        snap = {}
        for table in tables:
            digest = hashlib.sha256()
            count = 0
            for row in con.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
                digest.update(repr(row).encode())
                count += 1
            snap[table] = (count, digest.hexdigest())
        return snap
    finally:
        con.close()


def diff(before: dict, after: dict) -> list[str]:
    """Human-readable list of what changed between two snapshots."""
    changes = []
    for table, (count, digest) in before.items():
        if table not in after:
            changes.append(f"{table}: DROPPED ({count} rows lost)")
        elif after[table][0] != count:
            changes.append(f"{table}: rows {count} -> {after[table][0]}")
        elif after[table][1] != digest:
            changes.append(f"{table}: content changed")
    for table in after:
        if table not in before:
            changes.append(f"{table}: new table")
    return changes



# ---- helpers for the refund attacks ---------------------------------------

from payments_ops.ops_store import connect_ops


def pick_txn(min_amount: int = 0, max_amount: int = 10**12) -> tuple[str, int]:
    """First captured transaction in the amount range (read-only lookup)."""
    con = sqlite3.connect(f"{Path(scoped_server.DB_PATH).as_uri()}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT txn_id, amount_minor FROM transactions "
            "WHERE status = 'captured' AND amount_minor BETWEEN ? AND ? "
            "ORDER BY txn_id LIMIT 1",
            (min_amount, max_amount),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise RuntimeError(f"no captured transaction between {min_amount} and {max_amount}")
    return row[0], row[1]


def refund_summary() -> tuple[int, int]:
    """(number of refunds, total minor units) recorded by the scoped server."""
    con = connect_ops()
    try:
        return con.execute("SELECT COUNT(*), COALESCE(SUM(amount_minor), 0) FROM refunds").fetchone()
    finally:
        con.close()


def naive_status(txn_id: str) -> str:
    """Status of a transaction in the naive copy."""
    con = sqlite3.connect(f"{Path(naive_server.NAIVE_DB).as_uri()}?mode=ro", uri=True)
    try:
        return con.execute("SELECT status FROM transactions WHERE txn_id = ?", (txn_id,)).fetchone()[0]
    finally:
        con.close()



# ---- helpers for attacks 7 and 8 -------------------------------------------

import json


def naive_query(sql: str, params: tuple = ()) -> list[tuple]:
    """Read-only query against the naive copy (for measuring, never for attacking)."""
    con = sqlite3.connect(f"{Path(naive_server.NAIVE_DB).as_uri()}?mode=ro", uri=True)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def token_from(text: str) -> str | None:
    """Pull the confirmation token out of a dry-run response."""
    try:
        return json.loads(text).get("confirmation_token")
    except (ValueError, AttributeError):
        return None


async def role_seen(client) -> str:
    """Which role does the scoped server say it is running as?"""
    result = await client.read_resource("payments://policy/refund-limits")
    return json.loads(result.contents[0].text)["your_role"]



# ---- helpers for attack 9 ---------------------------------------------------

def captured_for_merchant(merchant_id: str) -> list[tuple[str, int]]:
    """Every captured transaction of one merchant: the agent's 'refund them all' target list."""
    con = sqlite3.connect(f"{Path(scoped_server.DB_PATH).as_uri()}?mode=ro", uri=True)
    try:
        return con.execute(
            "SELECT txn_id, amount_minor FROM transactions "
            "WHERE merchant_id = ? AND status = 'captured' ORDER BY txn_id",
            (merchant_id,),
        ).fetchall()
    finally:
        con.close()