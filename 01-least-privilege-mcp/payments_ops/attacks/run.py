"""Run every implemented attack against both servers and print a results table."""
import asyncio
import logging

from payments_ops.attacks import a01_a02, a03_a04, a05_a06
from payments_ops.attacks.harness import naive_session, scoped_session


ATTACKS = [
    (1, "Bulk read", a01_a02.a01_naive, a01_a02.a01_scoped),
    (2, "Schema discovery", a01_a02.a02_naive, a01_a02.a02_scoped),
    (3, "Destructive write", a03_a04.a03_naive, a03_a04.a03_scoped),
    (4, "Silent tampering", a03_a04.a04_naive, a03_a04.a04_scoped),
    (5, "Refund over limit", a05_a06.a05_naive, a05_a06.a05_scoped),
    (6, "Skip the preview", a05_a06.a06_naive, a05_a06.a06_scoped),
]


async def main():
    logging.disable(logging.WARNING)  # keep the table readable; server logs are noise here
    print(f"{'#':<3} {'Attack':<18} {'Server':<7} {'Outcome':<14} Detail")
    print("-" * 100)
    for number, name, naive_fn, scoped_fn in ATTACKS:
        async with naive_session() as client:
            outcome, detail = await naive_fn(client)
        print(f"{number:<3} {name:<18} {'naive':<7} {outcome:<14} {detail}")
        async with scoped_session("support_agent") as client:
            outcome, detail = await scoped_fn(client)
        print(f"{number:<3} {name:<18} {'scoped':<7} {outcome:<14} {detail}")


if __name__ == "__main__":
    asyncio.run(main())