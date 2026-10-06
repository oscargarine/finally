---
type: article
title: Workspace agent instructions
description: How CLAUDE.md and AGENTS.md split instructions for agents in this repo.
resource: ../../../CLAUDE.md
tags: [agents]
timestamp: 2026-10-06T17:20:00Z
topic: meta
status: draft
sources: [../../raw/meta/claude.md, ../../raw/meta/agents.md]
score: 0.0
---

# Workspace agent instructions

> Sources: CLAUDE.md, AGENTS.md, 2026-10-06
> Raw: [claude](../../raw/meta/claude.md); [agents](../../raw/meta/agents.md)

## Overview

`CLAUDE.md` is read by Claude Code every turn. It pulls in `planning/PLAN.md` in full
and points to this wiki. `AGENTS.md` carries the same rules for other assistants.

## Key rules

- Read the user profile and the SDD constitution first.
- Never touch `.env` files or generated outputs.
- Keep the `frontend/` and `backend/` boundaries clean.
- Do not commit without asking. The rsc branch guard may also close `main` to agents.
- Reusable knowledge goes to `02-DOCS/`.

## Related

- [FinAlly overview](../project/finally-overview.md)
- [User profile](../harness/user-profile.md)
