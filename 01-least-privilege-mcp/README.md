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

Problems found while building and testing, with their status.

**In the test bench itself**

- **Fixed: the benchmark had a tell.** The injected fault rows used IDs starting with
  `inj`, so an agent could have found the faults by pattern instead of by reasoning.
  Caught before any evaluation; IDs now continue the normal numbering.
- **Fixed: a measurement bug in attack 10.** My first leak detector flagged an error as
  an engine leak because it contained the word `sqlite`, which was the attacker's own
  input echoed back. A match that was part of the input reveals nothing; the detector
  now ignores it. I found this by reading the actual error text, and it is why I report
  the fix here instead of only the final table.
- **Prediction miss: attack 9.** Predicted PARTIAL, result HARM. The prediction did not
  separate roles; the real result is 22% for `support_agent` and 100% for `finance_manager`.

**In the scoped server (open, not fixed in this version)**

- **No aggregate cap.** Limits apply per refund, not in total. A compromised agent can
  refund every payment of a merchant, each one within its limit (attack 9).
- **The confirm step is not a human gate.** The server checks that a preview happened
  and the token matches; it cannot know whether a person approved. The agent in attack 9
  confirmed its own previews.
- **No rate limit.** One transaction per call, but IDs can be enumerated one by one
  (attack 1).
- **A preview is issued for a refund that will fail.** The preview does not look at
  earlier refunds, so a second refund that would exceed the payment gets a preview and a
  token and is refused only at confirm (attack 7). The money is safe; the review is
  misleading.
- **Errors reveal the framework and echo input.** Validation errors name the validation
  library and repeat the first ~50 characters of the bad input. No database or path
  details leak, but echoed input is a route for injected text to reach a model (this is
  what Project 4 tests).
- **Prompt-argument errors are generic.** A bad argument to a prompt comes back as an
  opaque protocol error with the reason only in the server log, unlike tool errors,
  which carry a readable message.

**Something that went wrong in the tooling:** the first version of a tool raised
`ValueError`. In this SDK version only `ToolError` carries its message to the model; any
other exception becomes a generic "Error executing tool". Anticipated failures must be
`ToolError`.

## When not to use this

- **Not for more than one user on one server.** The role comes from the environment of
  the server process, so over HTTP every client gets the same role. A multi-user
  deployment needs an authenticated identity (a token) that maps to a role.
- **Not as a substitute for human approval.** Dry-run then confirm stops accidental
  execution. It does not stop an agent that confirms for itself. Real approval has to be
  enforced by the host or out of band.
- **Not for real money as it stands.** There is no aggregate cap, no rate limit, no
  authentication and no audit trail of refused attempts.
- **Not proof about models.** The caller in the harness is a script that makes every
  call the server accepts. It measures what the server permits, not whether a model
  would fall for an injection.
- **Weak evidence by construction.** Synthetic data, ten attacks, and the same author
  for the defences and the attacks. The predictions were written in advance to limit
  that bias, but it does not remove it.

## Cost
_To fill in._

## Honesty note
Demonstrated on realistic synthetic cases, not proven in production. Ten cases give directional results, not statistical proof.