---
type: article
title: Planning docs map
description: Index of the planning/ documents, which remain the source of truth for the spec.
resource: ../../../planning/
tags: [spec]
timestamp: 2026-10-06T17:20:00Z
topic: project
status: draft
sources: []
score: 0.0
---

# Planning docs map

> Sources: planning/*.md (read in place, not copied — planning/ is user-maintained)

## Overview

`planning/` is the shared contract between agents. The wiki points to it and does not
duplicate it.

| Document | What it holds |
|---|---|
| [PLAN.md](../../../planning/PLAN.md) | Full product spec: UX, architecture, DB schema, API, LLM, frontend, Docker, tests; review rounds §13–§14. |
| [market_data_design.md](../../../planning/market_data_design.md) | Technical design of the market data backend, with code snippets. |
| [market_data_interface.md](../../../planning/market_data_interface.md) | Protocol + ABC pattern for the provider interface. |
| [market_simulator.md](../../../planning/market_simulator.md) | GBM simulator model. |
| [massive_api.md](../../../planning/massive_api.md) | Research on the Massive (ex-Polygon.io) REST API. |
| [market_data_review.md](../../../planning/market_data_review.md) | Review of the implemented market data code. |
| [codex-review.md](../../../planning/codex-review.md) | Codex review of PLAN.md (10 findings). |
| [claude_reviewer_agent.md](../../../planning/claude_reviewer_agent.md) | Claude review of PLAN.md (19 new findings). |

## Related

- [FinAlly overview](./finally-overview.md)
