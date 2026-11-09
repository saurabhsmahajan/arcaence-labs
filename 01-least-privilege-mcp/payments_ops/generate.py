"""Generate the healthy baseline: merchants and clean transactions.

Every payment here is consistent across PSP events, ledger and settlement.
Exceptions are injected in a later step so they stand out against this baseline.
"""
import random
import sqlite3
from datetime import datetime, timedelta, timezone

from payments_ops.schema import create_db

SEED = 42
N_MERCHANTS = 50
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
DAYS = 14
CUTOFF_HOUR = 18  # settlement cut-off: 18:00 UTC

COUNTRIES = [("IN", "INR"), ("AE", "AED"), ("GB", "GBP"), ("DE", "EUR"), ("US", "USD")]
WORDS_A = ["Blue", "Maple", "Urban", "Saffron", "Coastal", "Nimbus",
           "Orchid", "Summit", "Lotus", "Harbor", "Crimson", "Willow"]
WORDS_B = ["Bakery", "Pharmacy", "Electronics", "Travel", "Books", "Cafe",
           "Garments", "Hardware", "Florist", "Grocers", "Fitness", "Stationers"]


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate(db_path="data/payments.db"):
    rng = random.Random(SEED)
    path = create_db(db_path)
    con = sqlite3.connect(path)

    pairs = [(a, b) for a in WORDS_A for b in WORDS_B]
    rng.shuffle(pairs)
    merchants = []
    for i in range(1, N_MERCHANTS + 1):
        country, currency = rng.choice(COUNTRIES)
        a, b = pairs[i - 1]
        merchants.append((f"m_{i:03d}", f"{a} {b}", country, currency))
    con.executemany("INSERT INTO merchants VALUES (?,?,?,?)", merchants)

    txn_n = evt_n = led_n = 0
    batches = {}  # (merchant_id, date) -> list of (txn_id, amount)

    for merchant_id, _, _, currency in merchants:
        for _ in range(rng.randint(30, 50)):
            txn_n += 1
            txn_id = f"txn_{txn_n:06d}"
            amount = rng.randint(500, 500_000)  # minor units
            created = START + timedelta(seconds=rng.randint(0, DAYS * 86400 - 1))
            captured = created + timedelta(seconds=rng.randint(60, 600))

            con.execute(
                "INSERT INTO transactions VALUES (?,?,?,?,?,?)",
                (txn_id, merchant_id, amount, currency, "captured", iso(created)),
            )

            psp_ref = f"psp_{txn_n:06d}"
            for etype, when in (("authorization", created), ("capture", captured)):
                evt_n += 1
                con.execute(
                    "INSERT INTO psp_events VALUES (?,?,?,?,?,?)",
                    (f"evt_{evt_n:07d}", txn_id, etype, amount, iso(when), psp_ref),
                )

            posted = captured + timedelta(seconds=30)
            for account, direction in (("psp_clearing", "debit"),
                                       ("merchant_payable", "credit")):
                led_n += 1
                con.execute(
                    "INSERT INTO ledger_entries VALUES (?,?,?,?,?,?)",
                    (f"led_{led_n:07d}", txn_id, account, direction, amount, iso(posted)),
                )

            # Before cut-off -> same-day batch; at or after cut-off -> next day.
            day = captured.date()
            if captured.hour >= CUTOFF_HOUR:
                day = day + timedelta(days=1)
            batches.setdefault((merchant_id, day), []).append((txn_id, amount))

    for (merchant_id, day), items in sorted(batches.items()):
        batch_id = f"batch_{merchant_id}_{day.isoformat()}"
        cutoff = datetime(day.year, day.month, day.day, CUTOFF_HOUR, tzinfo=timezone.utc)
        con.execute(
            "INSERT INTO settlement_batches VALUES (?,?,?,?)",
            (batch_id, merchant_id, iso(cutoff), sum(a for _, a in items)),
        )
        con.executemany(
            "INSERT INTO settlement_items VALUES (?,?,?)",
            [(batch_id, t, a) for t, a in items],
        )

    con.commit()
    return con


if __name__ == "__main__":
    con = generate()
    for table in ("merchants", "transactions", "psp_events",
                  "ledger_entries", "settlement_batches", "settlement_items"):
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n}")

    unbalanced = con.execute("""
        SELECT COUNT(*) FROM transactions t WHERE
          (SELECT SUM(amount_minor) FROM ledger_entries l
             WHERE l.txn_id = t.txn_id AND direction = 'debit') != t.amount_minor
          OR (SELECT SUM(amount_minor) FROM ledger_entries l
             WHERE l.txn_id = t.txn_id AND direction = 'credit') != t.amount_minor
    """).fetchone()[0]
    unsettled = con.execute("""
        SELECT COUNT(*) FROM transactions
        WHERE txn_id NOT IN (SELECT txn_id FROM settlement_items)
    """).fetchone()[0]
    print(f"unbalanced ledger entries: {unbalanced}")
    print(f"unsettled transactions: {unsettled}")
    con.close()