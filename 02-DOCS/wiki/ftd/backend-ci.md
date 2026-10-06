# Backend CI gate

## Intent

Run the constitution's merge bar (principles 5–7) automatically on every PR and push to `main`, so the
gate added in [ruff-mypy](./ruff-mypy.md) is enforced, not just available.

## Scope

In: `.github/workflows/backend-ci.yml` — uv setup, `uv sync --locked`, ruff format check, ruff check,
mypy, pytest; triggered on changes under `backend/`.
Out: frontend CI, branch-protection settings on GitHub (a repo setting, done by the owner), pre-commit hooks.

## Checklist

- [x] Workflow file written — proof: `npx yaml valid` exit 0
- [x] Every step's command passes locally exactly as CI runs it — proof: see Evidence
- [ ] Workflow runs green on GitHub — proof: Actions run on the PR (needs push; observed by the owner)

## Evidence

- 2026-10-06 local run from `backend/`: `uv sync --locked` ok · "30 files already formatted" · ruff "All checks passed!" · mypy "Success: no issues found in 30 source files" · pytest "72 passed".
- GitHub run: not observed yet — pending the push/PR.

## Next

Open the PR and confirm the Backend CI run is green; then (owner) require the `gate` check in branch protection for `main`.
