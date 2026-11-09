# Least-privilege payments-ops MCP server

## Problem
Agents are often given one broad service key, so a single confused or compromised call can move money.

## Hypothesis
Scoped tools, dry-run-then-confirm on write tools, and limits enforced in code shrink what a confused or compromised agent can do, compared with one generic query/execute tool.

## What I built
_To fill in as we build._

## Results
_Blast-radius table: the same 10 attacks and mistakes run against a naive wide-access server and against the scoped server._

## What broke
_To fill in._

## When not to use this
_To fill in._

## Cost
_To fill in._

## Honesty note
Demonstrated on realistic synthetic cases, not proven in production. Ten cases give directional results, not statistical proof.