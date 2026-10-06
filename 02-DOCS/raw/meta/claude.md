# CLAUDE

> Source: `CLAUDE.md` (workspace root)
> Collected: 2026-10-06
> Published: Unknown

# Proyecto FinAlly - El Aliado Financiero

Toda la documentación del proyecto se encuentra en el directorio `planning`.

El documento clave es `planning/plan.md`, incluido en su totalidad a continuación. El componente de datos de mercado ya está completado. Está resumido en este archivo, con más detalles en esa carpeta. Consulta estos documentos solo cuando sea necesario. El resto de la plataforma aún está por desarrollarse.

@planning/PLAN.md

<!-- added by harness 2026-10-06 -->
## Knowledge map

The **full** index lives in **`02-DOCS/wiki/index.md`**. Read the relevant article before working in
its area. New index entries go there, not into this file. `planning/` remains the source of truth
for the product spec.

Read first, always:

| Area | Article |
|------|---------|
| User profile (register: technical) | `02-DOCS/wiki/harness/user-profile.md` |
| SDD constitution (project non-negotiables) | `02-DOCS/wiki/sdd/constitution.md` |
| **Everything else — full index** | `02-DOCS/wiki/index.md` |

<!-- added by harness 2026-10-06 -->
## Workspace map

| Path | Role |
|------|------|
| `backend/` | FastAPI + uv project (Python). Market data done; DB layer started. |
| `frontend/` | Next.js static export (not created yet). |
| `planning/` | Product spec and design docs (source of truth). |
| `01-TOOLS/` | Operational tooling per external provider (only `_TEMPLATE/` for now). |
| `02-DOCS/` | LLM wiki: `inbox/`, `raw/`, `wiki/` (+ `index.md`, `log.md`, `gaps.md`). |

<!-- added by harness 2026-10-06 -->
## Working rules

- Ignore generated outputs: `node_modules/`, `.next/`, `.venv/`, `.pytest_cache/`, `__pycache__/`, `build/`.
- Keep `frontend/` and `backend/` boundaries clean (PLAN.md §4).
- Never publish secrets: `.env`, `01-TOOLS/**/.env`, `CREDENTIALS.md`.
- Reusable knowledge goes to `02-DOCS/` per the `harness` wiki protocol.

<!-- added by harness 2026-10-06 -->
## Main commands

```bash
cd backend && uv sync && uv run pytest
```
