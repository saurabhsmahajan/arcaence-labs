# Incident playbook: misbehaving agent

Lab document, synthetic data. In production the roles below are separate people.

## Trigger

Any one of these:

- An agent is seen doing something outside its register entry.
- The access review reports drift or an unapproved delegation path.
- A scope-widening incident appears in the metrics.
- A refund or charge nobody can explain.

## Roles

| Role          | Who in the lab                                         | Job                                                    |
| ------------- | ------------------------------------------------------ | ------------------------------------------------------ |
| Agent owner   | Saurabh Mahajan (from the register)                    | Decides to revoke. Can act alone in the first minutes. |
| Incident lead | Saurabh Mahajan                                        | Runs the steps below and records times.                |
| Reviewer      | Saurabh Mahajan (should be someone else in production) | Reviews afterwards. Approves any restore.              |

## First 15 minutes

1. **Contain.** The agent owner revokes the agent. Tokens it already holds stop working, and it cannot get new ones. The lab drill measured the gap between revoking and the first blocked request.
2. **Preserve.** Save the audit log before anything else changes.
3. **Answer "who did this?"** Run the report for the affected order. It gives the customer, each hop with its scopes, and the owner and approver of each agent.
4. **Inform.** The incident lead tells the owners of every agent named in the report, and the customer-facing owner if money or customer data may be involved.

## Within 1 day

5. **Scope the damage.** Search the audit log for every action by the revoked agent. List the orders touched.
6. **Run the access review.** Compare the register with the approved copy. Look for drift or scopes nobody uses.
7. **Fix the cause.** Change the register, get it approved again, and re-run the tests.

## Restore

The reviewer approves a restore only when:

- the cause is written down,
- the register is re-approved,
- the full test suite passes.

## Record

For each incident keep: time detected, time revoked, time of first blocked request, orders affected, cause, change made, who approved the restore.

## What this playbook does not cover

Real SPIRE or cloud identity services, key rotation and customer notification rules. These need production decisions.
