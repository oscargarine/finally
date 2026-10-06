# Ruff + mypy --strict in backend/

## Intent

Constitution v1.0.0 principles 5–6 require `ruff format`, `ruff check` and `mypy --strict` to pass
before merge. None of them was installed. Add them and bring the existing code to green, so the next
feature starts from a passing gate.

## Scope

In: dev dependencies + config in `backend/pyproject.toml`, `uv.lock`, formatting/lint/type fixes in
`backend/app`, `backend/tests` and `backend/demo_simulator.py`.
Out: CI wiring, pre-commit hooks, frontend tooling, functional changes.

## Checklist

- [x] Ruff + mypy added as dev deps with config — proof: ruff 0.16.10, mypy 2.4.0 installed via `uv add --dev`
- [x] Baseline measured — proof: 5 files unformatted, 23 ruff findings, 94 mypy errors in 14 files; pytest 72 passed
- [x] `ruff format --check` clean — proof: "30 files already formatted"
- [x] `ruff check` clean — proof: "All checks passed!"
- [x] `mypy --strict` clean — proof: "Success: no issues found in 30 source files"
- [x] No behaviour regression — proof: `uv run pytest` 72 passed (same as baseline)

Decisions:
- Ignored UP017 (constitution P10 names `timezone.utc`) and UP042 (`StrEnum` changes `str()` output).
- RUF006 was a real defect: un-referenced `asyncio.create_task` in `MarketSimulator._emit_immediate_tick`
  and `MassiveMarketDataProvider.add_ticker` could be garbage-collected mid-run. Both now keep a strong
  reference in `_background_tasks` until done.
- B011 exposed a vacuous test: `test_trades_side_check_constraint` swallowed its own `assert False`
  inside `except Exception`. Rewritten with `pytest.raises(sqlite3.IntegrityError)`.

## Evidence

- Final gate (2026-10-06): format clean · lint clean · mypy strict clean · 72 passed.
- Mutation check on the rewritten test: inserting a valid side (`'buy'`) makes it fail
  ("1 failed") — the test can now fail, which it could not before.

## Next

Commit on `chore/ruff-mypy`, push, open PR (stacked on `chore/rsc-harness`).
