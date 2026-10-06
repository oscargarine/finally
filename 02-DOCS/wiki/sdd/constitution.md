---
type: constitution
title: FinAlly — Constitution
description: The non-negotiable principles every rsc-sdd phase obeys.
tags: [sdd, constitution]
timestamp: 2026-10-06T17:30:00Z
topic: sdd
version: v1.0.0
---

# FinAlly — Constitution

> Version: v1.0.0 · Ratified: 2026-10-06 · Last amended: 2026-10-06
> The non-negotiable principles every rsc-sdd phase obeys. The product spec is
> `planning/PLAN.md` (cited as §N); this file ratifies the principles and links the detail.

## 1. Stack canon

1. Backend is Python ≥ 3.12 + FastAPI, managed with `uv` in `backend/` (one `uv.lock`, committed).
   Frontend is Next.js + TypeScript as a static export (`output: 'export'`) with Tailwind, in `frontend/`.
   Changing a framework is a MAJOR amendment. (§3, §4)
2. Persistence is a single SQLite file `db/finally.db`, WAL mode, initialised once in FastAPI
   `lifespan` before serving traffic; all writes go through one writer connection or lock. (§7)
3. Ship as one Docker image, one port (8000): API routers registered before the `StaticFiles` mount at `/`. (§11)
4. LLM calls use LiteLLM → OpenRouter → `openrouter/openai/gpt-oss-120b` with
   `provider: {order: ["cerebras"], allow_fallbacks: false}`, structured outputs via a Pydantic
   `response_format`, 30 s timeout, no retries — via the `cerebras` skill. (§9)

## 2. Quality bar

5. Backend code is `ruff format`-ed and `ruff check`-clean (zero findings) before merge.
6. Backend passes `mypy --strict` with zero errors before merge. Ruff and mypy are dev dependencies in `backend/pyproject.toml`.
7. TDD: every behaviour change starts with a failing test (red → green → refactor, per `implement`).
   `uv run pytest` passes before merge. No numeric coverage floor; every §12 scenario a change touches has a test.

## 3. Conventions

8. `frontend/` and `backend/` never import from each other; they meet only over `/api/*` and `/api/stream/*`. (§4)
9. Write endpoints use 400/404/409/503 as in §8; error bodies are always `{"error": str, "code": "SNAKE_CASE"}`.
10. Timestamps are `datetime.now(timezone.utc).isoformat()` (`+00:00`, microseconds). Money is
    rounded to 2 decimals on write, quantity to 4; zero-comparisons use `1e-6` tolerance. (§6, §7)
11. Commit subjects open with a gitmoji followed by a Conventional Commits header, e.g.
    `✨ feat(portfolio): add trade endpoint`. Enforced by `.rsc/gitmoji-guard.mjs`.

## 4. Branching & shipping

12. Work happens on a branch off `main` and lands via pull request. No direct commits to `main`.
13. **Git authorship is the human's.** No `Co-Authored-By` an AI and no "generated with" footer
    on commits or PRs. Enforced at the `ship` phase.

## 5. Security & privacy floor

14. No secret is ever committed. `.env` (root) and `01-TOOLS/**/.env` stay gitignored; only `.env.example` is versioned. (§5)
15. Every LLM-proposed action passes the same backend validation as a manual action, against
    live DB state at execution time; at most 10 trades and 10 watchlist changes per response. (§8, §9)

## 6. UX floor

16. The UI follows the §2 palette and dark theme, and shows a connection-status dot in the header.
    Desktop-first; tablet/mobile is out of scope for v1. (§2, §10)

## 7. Knowledge & decisions

17. Every significant decision is appended to `02-DOCS/wiki/sdd/decisions.md` (date, options, why).
    A change to `planning/PLAN.md` that conflicts with this constitution requires an amendment here.

## Definition of Done (the merge bar `verify` runs against)

A change ships only when ALL hold:

- [ ] `ruff format --check` and `ruff check` clean (principle 5).
- [ ] `mypy --strict` passes (principle 6).
- [ ] Written test-first; `uv run pytest` green; frontend tests green when `frontend/` is touched (principle 7).
- [ ] Conventions followed (principles 8–11).
- [ ] On a branch, merged via PR, authored by the human, no AI trailer (principles 12–13).
- [ ] No secret committed; LLM actions validated (principles 14–15).
- [ ] UX floor met where UI changed (principle 16).
- [ ] Significant decisions logged (principle 17).

## Amendment log (append-only)

| Date | Version | Change | Why |
|------|---------|--------|-----|
| 2026-10-06 | v1.0.0 | Ratified initial constitution. | rsc onboarding; derived from PLAN.md + user answers (Ruff + mypy strict, TDD without floor, branch + PR, no AI trailer). |
