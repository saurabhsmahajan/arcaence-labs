# Arcaence labs

[![CI](https://github.com/saurabhsmahajan/arcaence-labs/actions/workflows/ci.yml/badge.svg)](https://github.com/saurabhsmahajan/arcaence-labs/actions/workflows/ci.yml)

Hands-on labs behind the [Arcaence](https://arcaence.com) blog.

> **Read this first.** Every lab here uses synthetic data and simulated systems. Nothing is production code, and none of it is employer work. Numbers are lab numbers, not production figures.

## Labs

| Lab | Blog post | Notes | What it shows |
| --- | --- | --- | --- |
| [agent-identity](agent-identity/) | [Agent identity is not a service account](https://www.arcaence.com/p/agent-identity-is-not-a-service-account) | — | Delegation between AI agents must narrow at every hop, and the payment agent can never refund |
| [01-least-privilege-mcp](01-least-privilege-mcp/) | [Predict first, then test](https://www.arcaence.com/p/predict-first-then-test) | [Project 1 notes (Word)](01-least-privilege-mcp/docs/Project1-Notes.docx) | Scoped tools, dry-run then confirm, and limits enforced in code shrink what a confused or compromised agent can do (10 attacks, naive vs scoped server) |

## Conventions

- One folder per lab, each with its own README, tests and `package.json`.
- Private keys and `.env` files are git-ignored. Labs generate their own keys on first run.


