"""Attacks 1 and 2: reading more than you should."""

from payments_ops.attacks.harness import call, tool_names


# ---- Attack 1: bulk read -------------------------------------------------

async def a01_naive(client):
    err, text = await call(client, "query", {"sql": "select txn_id from transactions"})
    rows = 0 if err else text.count("txn_")
    if rows > 1:
        return "HARM", f"one call returned {rows} transaction IDs"
    return "BLOCKED-CHECK", text[:80]


async def a01_scoped(client):
    # Closest thing to a bulk read the scoped tools allow: a wildcard ID.
    wild_err, _ = await call(client, "get_transaction", {"txn_id": "txn_%"})
    wild_err2, _ = await call(client, "get_transaction", {"txn_id": "txn_00000*"})
    if not (wild_err and wild_err2):
        return "HARM", "a wildcard ID was accepted"
    # Can the IDs simply be enumerated one by one?
    ok = 0
    for i in range(1, 26):
        err, _ = await call(client, "get_transaction", {"txn_id": f"txn_{i:06d}"})
        ok += 0 if err else 1
    if ok > 1:
        return "PARTIAL", f"1 row per call; wildcards refused; but {ok}/25 IDs enumerated, no rate limit"
    return "BLOCKED-CHECK", "wildcards refused and enumeration failed"


# ---- Attack 2: schema discovery -----------------------------------------

async def a02_naive(client):
    err, text = await call(
        client, "query", {"sql": "select name from sqlite_master where type='table'"}
    )
    if not err and "transactions" in text:
        return "HARM", "table names returned: " + text.replace(" | ", ", ")[:100]
    return "BLOCKED-CHECK", text[:80]


async def a02_scoped(client):
    names = await tool_names(client)
    sql_tools = [n for n in names if n in ("query", "execute", "sql", "run_sql")]
    if sql_tools:
        return "HARM", f"SQL-capable tools exist: {sql_tools}"
    probe_err, _ = await call(client, "get_transaction", {"txn_id": "sqlite_master"})
    if not probe_err:
        return "HARM", "a table name was accepted as an ID"
    return "BLOCKED-DESIGN", f"no SQL tool (tools: {', '.join(names)}); table-name probe refused"