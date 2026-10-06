---
type: article
title: Operational tools catalog
description: State of 01-TOOLS/ and the providers that still lack operator tooling.
resource: ../../../01-TOOLS/README.md
tags: [tooling]
timestamp: 2026-10-06T17:20:00Z
topic: operations
status: draft
sources: [../../raw/operations/01-tools-readme.md]
score: 0.0
---

# Operational tools catalog

> Sources: 01-TOOLS/README.md, 2026-10-06
> Raw: [01-tools-readme](../../raw/operations/01-tools-readme.md)

## Overview

`01-TOOLS/` holds only `_TEMPLATE/`. The project uses two external providers that are
not in the harness catalog, so no tool folder was generated:

- **OpenRouter** (`OPENROUTER_API_KEY`) — LLM chat via LiteLLM.
- **Massive / Polygon** (`MASSIVE_API_KEY`) — optional real market data.

To add either one, copy `_TEMPLATE/` and write a `test_connection` first.

## Related

- [FinAlly overview](../project/finally-overview.md)
