---
type: decision
title: SDD decisions log
description: Append-only log of significant project decisions (constitution principle 17).
tags: [sdd, decisions]
timestamp: 2026-10-06T17:35:00Z
topic: sdd
status: stable
---

# SDD decisions log

## 2026-10-06 — Constitution v1.0.0 ratified

- Options considered: lint/types (Ruff + mypy strict · Ruff only · none); tests (TDD no floor · TDD + 80% · tests pass no TDD); branching (branch + PR · branch + local merge · main open); authorship (no AI trailer · keep AI trailer).
- Choice: Ruff + mypy --strict; TDD without coverage floor; branch + PR; no AI trailer.
- Why: production-quality bar for an agent-built app with a fixed spec (`planning/PLAN.md`); PR flow matches the repo's history; git authorship stays with the human.
- Ratified by the user: "Approved."
