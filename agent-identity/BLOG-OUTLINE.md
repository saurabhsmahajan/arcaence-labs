# Blog 1 outline: agent identity is not a service account

Working title: Agent identity is not a service account
Audience: AI product and program leaders, security and governance leads
Note for the reader near the top: hands-on lab, synthetic data, simulated identity, not employer work.

## 1. The problem

Claim: when one agent hands work to another, the authority has to shrink at every hop, or one tricked agent can spend the whole chain's power.
Evidence: the design note rules (own identity per agent, narrower token per hop, payment agent holds no refund scope).

## 2. The setup

Claim: three agents, one customer, one purchase is enough to show the whole idea.
Evidence: shopper, order and payment agents. Sam's login token narrows from 300 s to 120 s and from three scopes to one.

## 3. Identity first

Claim: each agent proves who it is with its own key, not a shared secret.
Evidence: SPIFFE-style names, signed assertions, and the decision note with its trade-off (simulated, not SPIRE).

## 4. Governance as code

Claim: the agent register is a governance record the system enforces, not a document that sits in a folder.
Evidence: the issuer refuses any scope or delegation path not in the register. The skipped-hop attack was refused for exactly that reason.

## 5. Attacks that were stopped

Claim: defence works in layers, so one failed layer is not a breach.
Evidence: refund relay refused at three layers (shopper, order agent, payment agent); replayed token; wrong audience; same order twice.

## 6. When things go wrong

Claim: you need to stop an agent in seconds and answer "who did this?" in one minute.
Evidence: revocation drill (3 ms from revoke to first block); the order 1042 report with customer, three hops and owners; the incident playbook.

## 7. Keeping it honest over time

Claim: access creeps, so review it on a schedule.
Evidence: simulated creep and simulated leak tests; the access review against the approved register.

## 8. What the numbers say, and what they do not

Claim: report lab numbers as lab numbers.
Evidence: the metrics table from the evidence note (100% chain recorded, 28.6% denied, 0 widening incidents) with its "what it does not show" column.

## 9. Two bugs the demo caught

Claim: running the scenario found problems the tests did not.
Evidence: the "spiffe" reason key and the report that mixed orders. Fixed by grouping on shortened names and by walking back through parent token ids.

## 10. What production would need

Claim: this is a teaching lab, and the gap to production is the honest part.
Evidence: real SPIRE or cloud identity, key rotation, tamper-proof logs, separate people in each role.

## Ending

One line for the reader to take away, and a link to the repo folder.

## LinkedIn post

Short animated diagram of the delegation chain, with the title as the first frame.
