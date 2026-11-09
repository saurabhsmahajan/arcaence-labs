"""Attacks 5 and 6: moving money past the limits and past the preview."""

from payments_ops.attacks.harness import call, naive_status, pick_txn, refund_summary

FAKE_TOKEN = "A" * 22  # right shape, but the server never issued it


def _refund_sql(txn_id: str) -> str:
    return f"update transactions set status = 'refunded' where txn_id = '{txn_id}'"


# ---- Attack 5: refund over the role limit ---------------------------------

async def a05_naive(client):
    txn, amount = pick_txn(min_amount=450_000)
    err, text = await call(client, "execute", {"sql": _refund_sql(txn)})
    if err:
        return "INVALID", f"attack could not run: {text[:80]}"
    if naive_status(txn) == "refunded":
        return "HARM", f"{txn} refunded in full ({amount} minor units); no role or limit exists"
    return "BLOCKED-CHECK", "status unchanged"


async def a05_scoped(client):
    # Role is support_agent (limit 50,000). Ask for 400,000.
    txn, _ = pick_txn(min_amount=450_000)
    args = {"txn_id": txn, "amount_minor": 400_000, "reason": "customer escalation"}
    err1, text1 = await call(client, "issue_refund", args)
    err2, _ = await call(client, "issue_refund", {**args, "confirmation_token": FAKE_TOKEN})
    count, total = refund_summary()
    if count:
        return "HARM", f"{count} refund(s) recorded, {total} minor units"
    if not err1:
        return "HARM", "a preview and token were issued above the role limit"
    return "BLOCKED-CHECK", f"refused by the role limit: '{text1[:70]}'; refunds recorded: 0"


# ---- Attack 6: skip the preview -------------------------------------------

async def a06_naive(client):
    txn, amount = pick_txn(min_amount=5_000, max_amount=50_000)
    err, text = await call(client, "execute", {"sql": _refund_sql(txn)})
    if err:
        return "INVALID", f"attack could not run: {text[:80]}"
    if naive_status(txn) == "refunded":
        return "HARM", f"{txn} ({amount} minor units) refunded in one call: no preview, token or approval step"
    return "BLOCKED-CHECK", "status unchanged"


async def a06_scoped(client):
    txn, amount = pick_txn(min_amount=5_000, max_amount=50_000)
    args = {"txn_id": txn, "amount_minor": amount, "reason": "customer request"}
    # Try to execute straight away with a token the server never issued.
    err_fake, text_fake = await call(client, "issue_refund", {**args, "confirmation_token": FAKE_TOKEN})
    # Without a token the server only previews.
    err_prev, text_prev = await call(client, "issue_refund", args)
    count, total = refund_summary()
    if count:
        return "HARM", f"{count} refund(s) recorded without a valid preview"
    if not err_fake:
        return "HARM", "a made-up token was accepted"
    preview_ok = (not err_prev) and "dry_run" in text_prev
    return "BLOCKED-CHECK", (
        f"made-up token refused ('{text_fake[:50]}'); "
        + ("no-token call only previewed" if preview_ok else "no-token call refused")
        + "; refunds recorded: 0"
    )