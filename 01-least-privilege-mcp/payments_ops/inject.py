"""Inject known exceptions into the healthy baseline and write ground truth.

Five cases of each of six root causes = 30 cases. The answers go to
data/ground_truth.json, a separate file that the MCP server never reads.
"""
import itertools
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from payments_ops.generate import SEED, generate, iso

FMT = "%Y-%m-%dT%H:%M:%SZ"
PER_CAUSE = 5

EXPLANATIONS = {
    "duplicate_capture": "Capture was retried after a timeout; the PSP processed both "
                         "(two captures, different references) but the ledger booked only one.",
    "webhook_replay": "The PSP capture webhook was delivered twice with the same "
                      "reference and the ledger posted it twice.",
    "missing_ledger_entry": "The PSP captured and settlement paid out, but no ledger "
                            "entries were ever posted.",
    "stuck_refund": "A refund was requested but never completed; no ledger reversal "
                    "and the status is still refund_pending.",
    "settlement_cutoff_mismatch": "Captured before the 18:00 UTC cut-off but included "
                                  "in the next day's settlement batch.",
    "legitimate_refund": "Not an error: a refund was requested and completed, and "
                         "the ledger reversal was booked.",
}


def parse(s):
    return datetime.strptime(s, FMT).replace(tzinfo=timezone.utc)


def move_to_next_day_batch(con, txn_id):
    old_batch, amount = con.execute(
        "SELECT batch_id, amount_minor FROM settlement_items WHERE txn_id=?", (txn_id,)
    ).fetchone()
    merchant_id, cutoff = con.execute(
        "SELECT merchant_id, cutoff_at FROM settlement_batches WHERE batch_id=?",
        (old_batch,),
    ).fetchone()
    new_cutoff = parse(cutoff) + timedelta(days=1)
    new_batch = f"batch_{merchant_id}_{new_cutoff.date().isoformat()}"
    exists = con.execute(
        "SELECT 1 FROM settlement_batches WHERE batch_id=?", (new_batch,)
    ).fetchone()
    if not exists:
        con.execute(
            "INSERT INTO settlement_batches VALUES (?,?,?,?)",
            (new_batch, merchant_id, iso(new_cutoff), 0),
        )
    con.execute("UPDATE settlement_items SET batch_id=? WHERE txn_id=?", (new_batch, txn_id))
    con.execute("UPDATE settlement_batches SET total_minor = total_minor + ? WHERE batch_id=?",
                (amount, new_batch))
    con.execute("UPDATE settlement_batches SET total_minor = total_minor - ? WHERE batch_id=?",
                (amount, old_batch))
    left = con.execute(
        "SELECT COUNT(*) FROM settlement_items WHERE batch_id=?", (old_batch,)
    ).fetchone()[0]
    if left == 0:
        con.execute("DELETE FROM settlement_batches WHERE batch_id=?", (old_batch,))


def inject(con, rng):
    evt = itertools.count(1)
    led = itertools.count(1)

    def add_event(txn_id, etype, amount, when, ref):
        con.execute(
            "INSERT INTO psp_events VALUES (?,?,?,?,?,?)",
            (f"evt_inj_{next(evt):04d}", txn_id, etype, amount, iso(when), ref),
        )

    def add_ledger(txn_id, account, direction, amount, when):
        con.execute(
            "INSERT INTO ledger_entries VALUES (?,?,?,?,?,?)",
            (f"led_inj_{next(led):04d}", txn_id, account, direction, amount, iso(when)),
        )

    def capture_of(txn_id):
        amount, occurred, ref = con.execute(
            "SELECT amount_minor, occurred_at, psp_reference FROM psp_events "
            "WHERE txn_id=? AND event_type='capture'", (txn_id,)
        ).fetchone()
        return amount, parse(occurred), ref

    # Cut-off cases need a capture shortly before 18:00 UTC.
    near_cutoff = [r[0] for r in con.execute(
        "SELECT txn_id FROM psp_events WHERE event_type='capture' "
        "AND substr(occurred_at, 12, 8) BETWEEN '17:30:00' AND '17:59:59'"
    )]
    if len(near_cutoff) < PER_CAUSE:
        raise RuntimeError("not enough captures near the cut-off")
    cutoff_txns = rng.sample(near_cutoff, PER_CAUSE)

    pool = [r[0] for r in con.execute("SELECT txn_id FROM transactions")
            if r[0] not in cutoff_txns]
    other = rng.sample(pool, PER_CAUSE * 5)
    chosen = {
        "duplicate_capture": other[0:5],
        "webhook_replay": other[5:10],
        "missing_ledger_entry": other[10:15],
        "stuck_refund": other[15:20],
        "legitimate_refund": other[20:25],
        "settlement_cutoff_mismatch": cutoff_txns,
    }

    for t in chosen["duplicate_capture"]:
        amount, when, ref = capture_of(t)
        add_event(t, "capture", amount, when + timedelta(seconds=90), ref + "_r")

    for t in chosen["webhook_replay"]:
        amount, when, ref = capture_of(t)
        replay = when + timedelta(hours=1)
        add_event(t, "capture", amount, replay, ref)  # same reference
        add_ledger(t, "psp_clearing", "debit", amount, replay)
        add_ledger(t, "merchant_payable", "credit", amount, replay)

    for t in chosen["missing_ledger_entry"]:
        con.execute("DELETE FROM ledger_entries WHERE txn_id=?", (t,))

    for t in chosen["stuck_refund"]:
        amount, when, ref = capture_of(t)
        add_event(t, "refund_requested", amount, when + timedelta(days=2), ref + "_refund")
        con.execute("UPDATE transactions SET status='refund_pending' WHERE txn_id=?", (t,))

    for t in chosen["legitimate_refund"]:
        amount, when, ref = capture_of(t)
        requested = when + timedelta(days=1)
        done = requested + timedelta(hours=1)
        add_event(t, "refund_requested", amount, requested, ref + "_refund")
        add_event(t, "refund_completed", amount, done, ref + "_refund")
        add_ledger(t, "merchant_payable", "debit", amount, done)
        add_ledger(t, "psp_clearing", "credit", amount, done)
        con.execute("UPDATE transactions SET status='refunded' WHERE txn_id=?", (t,))

    for t in chosen["settlement_cutoff_mismatch"]:
        move_to_next_day_batch(con, t)

    cases = [{"txn_id": t, "root_cause": cause, "explanation": EXPLANATIONS[cause]}
             for cause, txns in chosen.items() for t in txns]
    rng.shuffle(cases)  # so case order does not reveal the type
    for i, c in enumerate(cases, start=1):
        c["case_id"] = f"case_{i:03d}"
    return cases


if __name__ == "__main__":
    con = generate()
    cases = inject(con, random.Random(SEED + 1))
    con.commit()

    out = Path("data/ground_truth.json")
    out.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(f"wrote {len(cases)} labelled cases to {out}")

    print("ledger entries per transaction (entries: txns):")
    for n, c in con.execute("""
        SELECT n, COUNT(*) FROM (
          SELECT t.txn_id, COUNT(l.entry_id) AS n FROM transactions t
          LEFT JOIN ledger_entries l ON l.txn_id = t.txn_id GROUP BY t.txn_id
        ) GROUP BY n ORDER BY n"""):
        print(f"  {n}: {c}")

    print("capture events per transaction (captures: txns):")
    for n, c in con.execute("""
        SELECT n, COUNT(*) FROM (
          SELECT txn_id, COUNT(*) AS n FROM psp_events
          WHERE event_type='capture' GROUP BY txn_id
        ) GROUP BY n ORDER BY n"""):
        print(f"  {n}: {c}")

    print("transaction status:")
    for s, c in con.execute("SELECT status, COUNT(*) FROM transactions GROUP BY status"):
        print(f"  {s}: {c}")
    con.close()