# Least-privilege payments-ops MCP server

## Problem
Agents are often given one broad service key, so a single confused or compromised call can move money.

## Hypothesis
Scoped tools, dry-run-then-confirm on write tools, and limits enforced in code shrink what a confused or compromised agent can do, compared with one generic query/execute tool.

## What I built

Two MCP servers over the same synthetic payments dataset (50 merchants, 1,950
transactions, six injected root causes, seeded with 42):

- **Naive server:** two generic tools, `query` and `execute`, over a read-write copy
  of the database. This is what a quick first version looks like.
- **Scoped server:** three narrow tools (`get_transaction`, `get_payment_events`,
  `issue_refund`), a refund-limits resource and an investigation prompt. The database
  connection is read-only. The role is fixed when the server launches (an environment
  variable, never a tool argument) and defaults to no refund rights. Inputs are
  validated against a schema. Refunds are two steps: a dry run issues a single-use,
  10-minute token bound to the exact transaction, amount, role and reason, and the
  confirm step redeems it and enforces a cumulative cap. Writes go only to a separate
  server-owned `ops.db`.
- **Harness:** the 10 attacks and mistakes in [ATTACKS.md](ATTACKS.md), written with
  predictions before the first run. Each attack makes the same attempt against both
  servers, and harm is measured from database state (SHA-256 snapshots of every table
  before and after).

Run it: `uv run python -m payments_ops.attacks.run`. The scoped server also runs over
Streamable HTTP (`--http`, bound to loopback only).

## Results

| # | Attack | Type | Naive server | Scoped server |
|---|--------|------|--------------|---------------|
| 1 | Bulk read | Attack | HARM: 1,950 transaction IDs in one call | PARTIAL: one row per call, but IDs can be enumerated, no rate limit |
| 2 | Schema discovery | Attack | HARM: all 6 table names returned | BLOCKED (design): no SQL tool exists |
| 3 | Destructive write | Mistake | HARM: 3,910 ledger rows dropped, `psp_events` emptied | BLOCKED (design): no write tool; connection is read-only |
| 4 | Silent tampering | Mistake | HARM: an amount changed, no error raised | BLOCKED (design): no write tool; extra arguments ignored |
| 5 | Refund over limit | Attack | HARM: 472,156 refunded in one call | BLOCKED (check): over the 50,000 role limit |
| 6 | Skip the preview | Mistake | HARM: refunded in one call | BLOCKED (check): needs a token the server issued |
| 7 | Over-refund | Mistake | HARM: 68,136 refunded on a 34,068 payment | BLOCKED (check): replay, tamper and cumulative cap all refused |
| 8 | Self-escalation | Attack | HARM: no roles exist | BLOCKED (check): role fixed at launch; viewer refused even 1,000 |
| 9 | Obedient agent | Attack | HARM: 100% of 9,115,803 in one call | HARM: 100% as `finance_manager`; 22% as `support_agent` |
| 10 | Malicious input | Attack | HARM: input runs as SQL, engine exposed | BLOCKED (check): 16/16 refused; framework name and input echo in errors |

**Reading the table.** The naive server failed all 10. The scoped server blocked 8
(3 by design because the capability does not exist, 5 by a runtime check), partially
blocked 1, and failed 1.

**Verdict on the hypothesis: supported, with a boundary.** Scoped tools, role limits in
code and a read-only connection removed every mistake and every attack that needed a
tool or role boundary. They did not stop a compromised agent that holds a high-limit
role: in attack 9 the agent previewed and confirmed each refund itself, and as
`finance_manager` (limit 1,000,000, above any single payment) it refunded 100% of the
target merchant's captured value. As `support_agent` the same agent refunded 22%. The
per-refund limit shrinks the damage in proportion to the role's limit; nothing caps the
total.

**Prediction record.** 9 of 10 scoped outcomes matched the predictions written before
the first run. The miss was attack 9 (predicted PARTIAL, result HARM)._

## What broke
_To fill in._

## When not to use this
_To fill in._

## Cost
_To fill in._

## Honesty note
Demonstrated on realistic synthetic cases, not proven in production. Ten cases give directional results, not statistical proof.