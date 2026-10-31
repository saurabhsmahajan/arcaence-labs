# Agent identity lab

Companion to the Arcaence blog post *Agent identity is not a service account* (planned).

> **Read this first.** Synthetic data, simulated identity, one machine, one person playing every role. This is a teaching lab, not production code and not employer work. Numbers are lab numbers.

## What it shows

A shopper agent, an order agent and a payment agent handle one purchase for a customer. The lab proves two rules:

1. Authority narrows at every hop: fewer scopes, one order, a shorter life.
2. The payment agent can never refund, whoever asks.

Around that, it shows the governance side: an agent register the issuer enforces, an audit log with one trace per purchase, a kill switch, an access review, metrics, a "who did this?" report and an incident playbook.

## Run it

Needs Node 20 or later. Run these three commands, one at a time:

    npm ci
    npm test
    npm run demo

Keys are generated on first run and are git-ignored. `npm test` should report 45 passing tests. `npm run demo` runs purchases, three attacks and a revocation drill, prints the metrics and the report for order 1042, and writes `evidence/audit-demo.jsonl`.

## Where things are

| Path | What it holds |
| --- | --- |
| `DESIGN.md` | The rules, planned tests and the identity decision |
| `AGENT-REGISTER.md`, `register-approved.json` | Who owns each agent and what it may do |
| `src/` | Issuer, token exchange, the three agents, audit log, checks, metrics, report |
| `test/` | Attacks, leaks, creep and revocation tests |
| `scripts/` | Key generation, demo, approval and access review |
| `INCIDENT-PLAYBOOK.md` | Who revokes, who informs, who reviews |
| `evidence/` | Demo output and what each number does and does not show |
| `BLOG-OUTLINE.md` | Working outline for the post |

## Limits

- Each agent signs with its own key pair. This simulates workload identity and is not SPIRE.
- Private keys sit on disk. Fine for synthetic data, not for production.
- In production the roles in the playbook are separate people.
