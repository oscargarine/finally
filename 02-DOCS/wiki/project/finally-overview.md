---
type: article
title: FinAlly overview
description: What FinAlly is, its architecture, current build status and where the spec lives.
resource: ../../../planning/PLAN.md
tags: [architecture, status]
timestamp: 2026-10-06T17:20:00Z
topic: project
status: draft
sources: [../../raw/project/readme.md]
score: 0.0
---

# FinAlly overview

> Sources: README.md, 2026-10-06; planning/PLAN.md
> Raw: [readme](../../raw/project/readme.md)

## Overview

FinAlly is an AI trading workstation: live simulated or real market prices over SSE,
a simulated $10k portfolio, and an LLM chat assistant that can analyse positions and
execute trades or watchlist changes. It is the capstone of an agentic-coding course,
built entirely by orchestrated agents that coordinate through `planning/`.

## Architecture

- One Docker container, port 8000. FastAPI serves `/api/*`, SSE at `/api/stream/*`,
  and the Next.js static export at `/`.
- SQLite at `db/finally.db`, initialised in the FastAPI `lifespan`, WAL mode.
- Market data: GBM simulator by default; Massive (Polygon) REST polling when
  `MASSIVE_API_KEY` is set.
- LLM: LiteLLM → OpenRouter → `openai/gpt-oss-120b` on Cerebras, structured outputs,
  `LLM_MOCK=true` for deterministic tests.

## Status (2026-10-06)

- Done: market data (`backend/app/market_data/`).
- Started: SQLite layer (`backend/app/db/`).
- Pending: portfolio, chat/LLM, API routes, frontend, Docker, scripts, E2E tests.

## Related

- [Planning docs map](./planning-docs-map.md) — where each design decision is recorded.
- [Workspace agent instructions](../meta/workspace-agent-instructions.md) — rules agents follow here.
