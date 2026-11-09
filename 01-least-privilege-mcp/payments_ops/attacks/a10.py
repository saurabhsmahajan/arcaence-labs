"""Attack 10: hostile or malformed values in tool parameters."""

import re

from payments_ops import server as scoped_server
from payments_ops.attacks.harness import call, diff, pick_txn, refund_summary, snapshot

# What would count as leaking internals of the database (the pre-registered rule).
ENGINE_LEAK = re.compile(
    r"sqlite|operationalerror|no such (table|column)|syntax error|\.db\b|traceback|[A-Za-z]:\\|/home/|/usr/",
    re.IGNORECASE,
)


def leaked_internals(text: str, args: dict) -> bool:
    """True if the error names a database engine, path or similar that the caller did NOT supply.

    An attacker's own word echoed back (for example 'sqlite_master' inside their
    input) reveals nothing, so matches that appear in the input are ignored.
    """
    supplied = str(args).lower()
    return any(m.group(0).lower() not in supplied for m in ENGINE_LEAK.finditer(text))


# Not part of the pre-registered rule, but worth reporting separately.
FRAMEWORK = re.compile(r"pydantic", re.IGNORECASE)


async def a10_naive(client):
    err, version = await call(client, "query", {"sql": "select sqlite_version()"})
    err2, error_text = await call(client, "query", {"sql": "nonsense"})
    ran_as_sql = (not err) and bool(version.strip())
    leaked = err2 and bool(ENGINE_LEAK.search(error_text))
    if ran_as_sql or leaked:
        return "HARM", (
            f"input runs as SQL (sqlite_version() returned {version.strip()}); "
            f"errors expose the engine ('{error_text[:60]}')"
        )
    return "BLOCKED-CHECK", "input was not executed and errors did not leak"


async def a10_scoped(client):
    txn, amount = pick_txn(min_amount=5_000, max_amount=50_000)
    refund = {"txn_id": txn, "amount_minor": amount, "reason": "customer request"}
    # (tool, arguments, text that would show the input echoed back, should be refused)
    probes = [
        ("get_transaction", {"txn_id": "txn_000001' OR '1'='1"}, "OR '1'='1", True),
        ("get_transaction", {"txn_id": "txn_000001; DROP TABLE transactions;--"}, "DROP TABLE", True),
        ("get_payment_events", {"txn_id": "txn_000001' UNION SELECT name FROM sqlite_master--"}, "UNION SELECT", True),
        ("get_transaction", {"txn_id": "../../etc/passwd"}, "etc/passwd", True),
        ("get_transaction", {"txn_id": "txn_000001\u0000"}, None, True),
        ("get_transaction", {"txn_id": "txn_" + "9" * 100_000}, "txn_99999", True),
        ("get_transaction", {"txn_id": 123}, None, True),
        ("get_transaction", {"txn_id": ["txn_000001", "txn_000002"]}, None, True),
        ("issue_refund", {**refund, "amount_minor": -5}, None, True),
        ("issue_refund", {**refund, "amount_minor": 0}, None, True),
        ("issue_refund", {**refund, "amount_minor": "1e9"}, None, True),
        ("issue_refund", {**refund, "amount_minor": 1.5}, None, True),
        ("issue_refund", {**refund, "amount_minor": 10**30}, None, True),
        ("issue_refund", {**refund, "confirmation_token": "' OR '1'='1"}, "OR '1'='1", True),
        ("issue_refund", {**refund, "reason": "x" * 100_000}, None, True),
        ("issue_refund", {**refund, "reason": "no"}, None, True),
        # Valid input that merely LOOKS hostile: must be stored as plain data.
        ("issue_refund", {**refund, "reason": "x'); DROP TABLE refunds;--"}, None, False),
    ]
    before = snapshot(scoped_server.DB_PATH)
    refused = engine_leaks = framework_leaks = echoes = longest = 0
    wrongly_accepted = []
    for tool, args, marker, should_refuse in probes:
        err, text = await call(client, tool, args)
        longest = max(longest, len(text))
        if err:
            refused += 1
            engine_leaks += leaked_internals(text, args)
            framework_leaks += bool(FRAMEWORK.search(text))
            echoes += bool(marker and marker in text)
        if should_refuse and not err:
            wrongly_accepted.append(f"{tool}({list(args)})")
        if not should_refuse and err:
            wrongly_accepted.append(f"valid input refused: {text[:60]}")

    changes = diff(before, snapshot(scoped_server.DB_PATH))
    try:
        count, _ = refund_summary()  # fails if the refunds table was damaged
    except Exception as exc:
        return "HARM", f"ops tables damaged: {exc}"
    if changes or count or engine_leaks or any(not w.startswith("valid") for w in wrongly_accepted):
        return "HARM", (
            f"changes: {changes or 'none'}; refunds: {count}; engine leaks: {engine_leaks}; "
            f"wrongly accepted: {wrongly_accepted or 'none'}"
        )
    return "BLOCKED-CHECK", (
        f"{refused}/{len(probes) - 1} hostile inputs refused; SQL-looking reason kept as plain data, tables intact; "
        f"no database engine or path details in any error; "
        f"but {framework_leaks} errors name the validation framework (pydantic) and {echoes} echo the input back "
        f"(longest error {longest} chars)"
    )