# Evidence note: agent identity lab

Source: `node scripts/demo.mjs`, run 2026-10-31. Raw log: `evidence/audit-demo.jsonl` (15 events).
All data is synthetic. These are lab numbers, not production figures.

## Scenario

- Two purchases (orders 1042, 1043) and one refund request, all through shopper, order and payment agents.
- Three attacks: refund token request, skipped hop, same order bought twice.
- One revocation drill on the order agent, followed by a purchase attempt.

## Metrics

| Metric                             | Value               | What it shows                                            | What it does not show                        |
| ---------------------------------- | ------------------- | -------------------------------------------------------- | -------------------------------------------- |
| Decisions with full chain recorded | 100% (14 of 14)     | Every decision carries a trace id and customer           | That the log cannot be tampered with         |
| Longest token lifetime             | 300 s (login token) | Delegated tokens are shorter, 120 s                      | That 300 s is the right value for production |
| Scope-widening incidents           | 0                   | No hop granted more than its parent                      | Anything about hops outside the register     |
| Denied requests                    | 28.6% (4 of 14)     | The three attacks and the revoked agent were all stopped | A real attack rate                           |
| Revoke to first block              | 3 ms                | Revocation takes effect immediately in the lab           | Production latency across services           |

## Denials by reason

- scope wider than parent token: 1
- shopper may not delegate to payment: 1
- order already charged: 1
- agent revoked: 1

## Who did this? Order 1042

Customer: customer:sam. Chain: login to shopper, shopper to order, order to payment. Each hop narrower. Owner and approver of all three agents: Saurabh Mahajan. The payment token's life is the parent's remaining life, so it reads 119 or 120 s depending on timing.

## Bugs found by running it

- Denial reasons starting with an agent name were grouped under the key "spiffe". Fixed by shortening agent names before grouping.
- The "who did this?" report mixed several orders when one login drove many. Fixed by walking back from the charge through parent token ids instead of filtering by trace id.

## Limits

- Simulated identity: each agent signs with its own key pair. This is not SPIRE.
- One process, one machine, one human playing every role.
- Private keys on disk, acceptable for synthetic data only.

