"""Attacks 7 and 8: repeating a refund, and claiming a bigger role."""

import os

from payments_ops.attacks.a05_a06 import FAKE_TOKEN, _refund_sql
from payments_ops.attacks.harness import (
    call,
    naive_query,
    naive_status,
    pick_txn,
    refund_summary,
    role_seen,
    scoped_session,
    token_from,
)


# ---- Attack 7: over-refund (retry, replay, tamper) ------------------------

async def a07_naive(client):
    txn, amount = pick_txn(min_amount=5_000, max_amount=50_000)
    types = [r[0] for r in naive_query("SELECT DISTINCT event_type FROM psp_events")]
    refund_type = next((t for t in types if "refund" in t and "complet" in t), None)
    if refund_type is None:
        return "INVALID", f"no refund-completed event type found (types: {types})"
    # A retrying agent records the same refund twice.
    for n in (1, 2):
        sql = (
            "insert into psp_events (event_id, txn_id, event_type, amount_minor, occurred_at, psp_reference) "
            f"values ('evt_try{n}_{txn}', '{txn}', '{refund_type}', {amount}, '2026-11-01T00:00:00Z', 'ref_try{n}_{txn}')"
        )
        err, text = await call(client, "execute", {"sql": sql})
        if err:
            return "INVALID", f"attack could not run: {text[:80]}"
    total = naive_query(
        "SELECT COALESCE(SUM(amount_minor), 0) FROM psp_events WHERE txn_id = ? AND event_type = ?",
        (txn, refund_type),
    )[0][0]
    if total > amount:
        return "HARM", f"{txn}: {total} refunded against a {amount} payment (recorded twice, nothing stopped it)"
    return "BLOCKED-CHECK", f"total refunded {total} did not exceed {amount}"


async def a07_scoped(client):
    txn, amount = pick_txn(min_amount=5_000, max_amount=50_000)
    part = int(amount * 0.6)
    base = {"txn_id": txn, "amount_minor": part, "reason": "customer request"}

    # 1. A legitimate partial refund: preview, then confirm.
    err, text = await call(client, "issue_refund", base)
    token1 = token_from(text)
    if err or not token1:
        return "INVALID", f"setup preview failed: {text[:80]}"
    err, text = await call(client, "issue_refund", {**base, "confirmation_token": token1})
    if err:
        return "INVALID", f"setup confirm failed: {text[:80]}"

    # 2. Replay the same token.
    replay_err, _ = await call(client, "issue_refund", {**base, "confirmation_token": token1})

    # 3. A second 60% refund of the same payment (would be 120% in total).
    err, text = await call(client, "issue_refund", base)
    preview_issued = not err
    token2 = token_from(text)
    second_err = True
    if token2:
        second_err, _ = await call(client, "issue_refund", {**base, "confirmation_token": token2})

    # 4. Tamper: preview a small amount, confirm a different one.
    err, text = await call(client, "issue_refund", {**base, "amount_minor": 100})
    token3 = token_from(text)
    tamper_err = True
    if token3:
        tamper_err, _ = await call(client, "issue_refund", {**base, "amount_minor": 101, "confirmation_token": token3})

    count, total = refund_summary()
    if total > amount:
        return "HARM", f"{total} refunded against a {amount} payment"
    if count != 1:
        accepted = [
            label
            for label, refused in (("replay", replay_err), ("second 60%", second_err), ("tampered amount", tamper_err))
            if not refused
        ]
        return "HARM", f"accepted: {', '.join(accepted) or 'unknown'} ({count} refunds recorded)"
    return "BLOCKED-CHECK", (
        f"replay refused; tampered amount refused; second 60% refused at confirm "
        f"({'preview was still issued' if preview_issued else 'no preview'}); "
        f"total refunded {total} of {amount}"
    )


# ---- Attack 8: self-escalation --------------------------------------------

ESCALATION = {
    "role": "finance_manager",
    "user_role": "finance_manager",
    "PAYMENTS_OPS_ROLE": "finance_manager",
    "limit_override": 1_000_000,
    "admin": True,
}


async def a08_naive(client):
    txn, amount = pick_txn(min_amount=450_000)
    # The attacker claims a role, as it would against any server.
    err, text = await call(client, "execute", {"sql": _refund_sql(txn), **ESCALATION})
    if err:
        return "INVALID", f"attack could not run: {text[:80]}"
    if naive_status(txn) == "refunded":
        return "HARM", f"no roles exist, so no escalation was needed: {txn} ({amount}) refunded"
    return "BLOCKED-CHECK", "status unchanged"


async def a08_scoped(client):
    # Launched as support_agent (limit 50,000). Claim to be finance_manager.
    txn, _ = pick_txn(min_amount=450_000)
    args = {"txn_id": txn, "amount_minor": 400_000, "reason": "approved by finance", **ESCALATION}
    err1, _ = await call(client, "issue_refund", args)
    err2, _ = await call(client, "issue_refund", {**args, "confirmation_token": FAKE_TOKEN})
    seen = await role_seen(client)
    count_support, _ = refund_summary()

    # Same trick against a viewer (limit 0): deny by default must hold.
    previous = os.environ.get("PAYMENTS_OPS_ROLE", "support_agent")
    small_txn, _ = pick_txn(min_amount=5_000, max_amount=50_000)
    async with scoped_session("viewer") as vclient:
        viewer_err, _ = await call(
            vclient,
            "issue_refund",
            {"txn_id": small_txn, "amount_minor": 1_000, "reason": "approved by finance", **ESCALATION},
        )
        viewer_seen = await role_seen(vclient)
        count_viewer, _ = refund_summary()
    os.environ["PAYMENTS_OPS_ROLE"] = previous

    if count_support or count_viewer or not (err1 and err2 and viewer_err):
        return "HARM", f"refunds recorded: support_agent {count_support}, viewer {count_viewer}"
    if seen != "support_agent" or viewer_seen != "viewer":
        return "HARM", f"role changed: {seen}, {viewer_seen}"
    return "BLOCKED-CHECK", (
        f"escalation arguments had no effect: role still {seen}; 400000 refused; "
        f"viewer ({viewer_seen}) refused even 1000"
    )