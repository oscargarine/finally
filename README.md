# FinAlly — AI Trading Workstation

FinAlly (Finance Ally) es una estación de trabajo de trading impulsada por IA que transmite datos de mercado en tiempo real, permite operar con una cartera simulada, y ofrece un asistente de chat con LLM capaz de analizar posiciones y ejecutar operaciones en nombre del usuario. Busca la sensación de una terminal Bloomberg moderna con un copiloto de IA.

Este proyecto es el trabajo final de un curso de programación con IA agéntica: está construido íntegramente por agentes de programación orquestados a través de los documentos de `planning/`.

## Estado actual

- ✅ **Datos de mercado** (`backend/app/market_data/`) — completado. Incluye simulador GBM, cliente de la API de Massive (Polygon.io), caché de precios compartida y la interfaz común entre ambas fuentes.
- 🚧 **Resto de la plataforma** (base de datos, cartera, chat LLM, frontend, Docker) — pendiente de construir, según lo especificado en `planning/PLAN.md`.

## Documentación

Toda la documentación vive en [`planning/`](planning/). El documento principal es [`planning/PLAN.md`](planning/PLAN.md), que cubre visión, arquitectura, esquema de base de datos, endpoints de la API, integración con el LLM, diseño del frontend, despliegue y estrategia de pruebas.

## Arquitectura (resumen)

Un único contenedor Docker, un único puerto (`8000`):

- **Frontend**: Next.js (TypeScript), exportado como sitio estático y servido por FastAPI.
- **Backend**: FastAPI (Python), gestionado con `uv`.
- **Base de datos**: SQLite, montada como volumen para persistencia.
- **Datos en tiempo real**: Server-Sent Events (`/api/stream/prices`).
- **IA**: LiteLLM → OpenRouter (Cerebras como proveedor de inferencia), con salidas estructuradas para ejecutar operaciones.
- **Datos de mercado**: simulador integrado por defecto, o datos reales vía la API de Massive si se configura `MASSIVE_API_KEY`.

Ver `planning/PLAN.md` §3 y §4 para el detalle completo de la arquitectura y la estructura de directorios.

## Estructura del repositorio

```
finally/
├── backend/       # Proyecto FastAPI (uv) — API, base de datos, datos de mercado, LLM
├── frontend/       # Proyecto Next.js (por construir)
├── planning/       # Documentación del proyecto (fuente de verdad)
├── test/           # Tests E2E (Playwright)
├── db/             # Punto de montaje del volumen SQLite en runtime
└── scripts/        # Scripts de inicio/parada (por construir)
```

## Variables de entorno

Copia `.env.example` a `.env` (si no existe, créalo según `planning/PLAN.md` §5) y configura:

```bash
OPENROUTER_API_KEY=   # obligatoria salvo que LLM_MOCK=true
MASSIVE_API_KEY=      # opcional — si no se define, se usa el simulador integrado
LLM_MOCK=false        # true para respuestas de LLM simuladas y deterministas (tests)
```

## Desarrollo

El backend es un proyecto [`uv`](https://docs.astral.sh/uv/) autocontenido en `backend/`:

```bash
cd backend
uv sync
uv run pytest
```

Cuando el frontend y el resto del backend estén implementados, este README se ampliará con instrucciones completas de arranque (Docker y desarrollo local).

## Licencia

Ver [`LICENSE`](LICENSE).
