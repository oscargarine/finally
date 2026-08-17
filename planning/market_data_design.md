# Diseño del Backend de Datos de Mercado

> Documento de diseño técnico para la implementación del componente de datos de mercado descrito en `PLAN.md` (Sección 6). Dirigido al agente de Backend/Datos de Mercado. Incluye fragmentos de código en Python (FastAPI, async) listos para adaptar.
>
> **Aviso (2026-08-14): documento histórico, no fuente de verdad.** El componente ya está implementado en `backend/app/market_data/` y ha evolucionado más allá de los fragmentos de código de este documento — por ejemplo, `PriceTick`/`CachedPrice` ahora incluyen `session_open`, `MarketDataProvider` expone `get_last_price()`, `MarketSimulator.add_ticker()` emite un tick inmediato, y `PriceCache.snapshot()` hace copia profunda de cada `CachedPrice` (no `dict(self._latest)`) — ver `PLAN.md` §6 para el contrato vigente. Ante cualquier discrepancia entre este documento y `PLAN.md` o el código real bajo `backend/app/market_data/`, esos dos priman. Este documento se conserva como contexto de diseño original, no como referencia a mantener sincronizada línea a línea.

## 1. Objetivos y Restricciones

- Dos fuentes de datos intercambiables: **Simulador GBM** (por defecto) y **API de Massive (Polygon.io)** (opcional, si `MASSIVE_API_KEY` está presente).
- Ambas implementan la misma interfaz abstracta — el resto del sistema (caché de precios, SSE, frontend) es agnóstico de la fuente.
- Una única tarea en segundo plano por proceso escribe en una **caché de precios en memoria** compartida.
- El endpoint SSE `/api/stream/prices` lee de esa caché y empuja actualizaciones a todos los clientes conectados a ~500ms.
- Todo async, sin bloquear el event loop de FastAPI.

---

## 2. Modelo de Datos Compartido

```python
# backend/app/market_data/types.py
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


@dataclass(slots=True)
class PriceTick:
    ticker: str
    price: float
    prev_price: float
    timestamp: str  # ISO 8601, UTC
    direction: Direction

    @classmethod
    def create(cls, ticker: str, price: float, prev_price: float) -> "PriceTick":
        if price > prev_price:
            direction = Direction.UP
        elif price < prev_price:
            direction = Direction.DOWN
        else:
            direction = Direction.FLAT
        return cls(
            ticker=ticker,
            price=round(price, 4),
            prev_price=round(prev_price, 4),
            timestamp=datetime.now(timezone.utc).isoformat(),
            direction=direction,
        )

    def to_sse_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "prev_price": self.prev_price,
            "timestamp": self.timestamp,
            "direction": self.direction.value,
        }
```

---

## 3. Interfaz Abstracta de Proveedor de Datos de Mercado

Ambas implementaciones (simulador y Massive) heredan de esta clase base. El contrato es deliberadamente mínimo: arrancar, detener, y notificar ticks vía callback — para que la caché de precios no necesite saber cuál se está usando.

```python
# backend/app/market_data/base.py
from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from .types import PriceTick

TickCallback = Callable[[PriceTick], Awaitable[None]]


class MarketDataProvider(ABC):
    """Interfaz que deben implementar el simulador y el cliente de Massive."""

    def __init__(self, on_tick: TickCallback) -> None:
        self._on_tick = on_tick
        self._tickers: set[str] = set()

    @abstractmethod
    async def start(self) -> None:
        """Arranca la tarea en segundo plano que produce ticks."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Detiene limpiamente la tarea en segundo plano."""
        ...

    @abstractmethod
    def add_ticker(self, ticker: str) -> None:
        """Añade un ticker al conjunto vigilado (watchlist agregada de todos los usuarios)."""
        ...

    @abstractmethod
    def remove_ticker(self, ticker: str) -> None:
        """Elimina un ticker del conjunto vigilado, si ya no lo necesita nadie."""
        ...

    async def _emit(self, tick: PriceTick) -> None:
        await self._on_tick(tick)
```

---

## 4. Caché de Precios en Memoria

Estructura central compartida entre el proveedor (que escribe) y el endpoint SSE (que lee). Usa `asyncio.Queue` por suscriptor para el fan-out, más un diccionario simple para el "último precio conocido" (necesario para que clientes que se conectan tarde reciban un snapshot inicial).

```python
# backend/app/market_data/cache.py
import asyncio
from dataclasses import dataclass

from .types import PriceTick


@dataclass(slots=True)
class CachedPrice:
    price: float
    prev_price: float
    timestamp: str


class PriceCache:
    """Caché en memoria + fan-out pub/sub para los streams SSE."""

    def __init__(self) -> None:
        self._latest: dict[str, CachedPrice] = {}
        self._subscribers: set[asyncio.Queue[PriceTick]] = set()
        self._lock = asyncio.Lock()

    async def update(self, tick: PriceTick) -> None:
        async with self._lock:
            self._latest[tick.ticker] = CachedPrice(
                price=tick.price,
                prev_price=tick.prev_price,
                timestamp=tick.timestamp,
            )
            dead: list[asyncio.Queue] = []
            for q in self._subscribers:
                try:
                    q.put_nowait(tick)
                except asyncio.QueueFull:
                    dead.append(q)  # cliente lento: lo desconectamos
            for q in dead:
                self._subscribers.discard(q)

    def snapshot(self) -> dict[str, CachedPrice]:
        return dict(self._latest)

    def subscribe(self) -> asyncio.Queue[PriceTick]:
        q: asyncio.Queue[PriceTick] = asyncio.Queue(maxsize=256)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)


# Instancia única a nivel de aplicación
price_cache = PriceCache()
```

El callback que conecta cualquier proveedor con la caché es trivial:

```python
# backend/app/market_data/wiring.py
from .cache import price_cache
from .types import PriceTick


async def on_tick(tick: PriceTick) -> None:
    await price_cache.update(tick)
```

---

## 5. Simulador de Mercado (GBM)

### 5.1 Matemática

Movimiento browniano geométrico discretizado:

```
S(t+dt) = S(t) * exp((mu - sigma^2 / 2) * dt + sigma * sqrt(dt) * Z)
```

donde `Z ~ N(0, 1)`, `mu` es la deriva anualizada, `sigma` la volatilidad anualizada, y `dt` el paso de tiempo expresado en años (ya que mu/sigma son anuales).

Con ticks cada 500ms y queriendo movimientos visualmente interesantes pero no absurdos, usamos un `dt` "efectivo" mayor al real transcurrido (acelerado), para que en una sesión de demo de minutos se vea movimiento real de mercado.

### 5.2 Parámetros por Ticker

```python
# backend/app/market_data/simulator_config.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TickerConfig:
    seed_price: float
    drift: float       # mu anualizado, p.ej. 0.08 = 8%/año
    volatility: float   # sigma anualizado, p.ej. 0.35 = 35%/año
    sector: str         # para correlación entre sectores


DEFAULT_TICKERS: dict[str, TickerConfig] = {
    "AAPL":  TickerConfig(190.00, 0.10, 0.28, "tech"),
    "GOOGL": TickerConfig(175.00, 0.09, 0.30, "tech"),
    "MSFT":  TickerConfig(420.00, 0.10, 0.26, "tech"),
    "AMZN":  TickerConfig(185.00, 0.11, 0.32, "tech"),
    "TSLA":  TickerConfig(250.00, 0.05, 0.55, "auto"),
    "NVDA":  TickerConfig(130.00, 0.18, 0.50, "tech"),
    "META":  TickerConfig(500.00, 0.10, 0.34, "tech"),
    "JPM":   TickerConfig(200.00, 0.07, 0.22, "finance"),
    "V":     TickerConfig(280.00, 0.08, 0.20, "finance"),
    "NFLX":  TickerConfig(700.00, 0.09, 0.33, "media"),
}

# Acoplamiento de movimiento entre sectores (0 = independiente, 1 = en bloque)
SECTOR_CORRELATION = 0.55
MARKET_CORRELATION = 0.35  # factor de mercado global compartido por todos los tickers

# Probabilidad por tick de un "evento" de salto brusco
EVENT_PROBABILITY = 0.0008  # ~ uno cada ~20 min a 500ms/tick
EVENT_MAGNITUDE_RANGE = (0.02, 0.05)  # 2%-5%
```

### 5.3 Generación de Shocks Correlacionados

Para que "las tecnológicas se muevan juntas", generamos un factor de mercado global `Z_market`, un factor por sector `Z_sector`, y un factor idiosincrático `Z_idio` por ticker, combinados con pesos que suman varianza 1:

```python
# backend/app/market_data/correlation.py
import random
from .simulator_config import DEFAULT_TICKERS, MARKET_CORRELATION, SECTOR_CORRELATION


def correlated_shocks(rng: random.Random) -> dict[str, float]:
    """Devuelve un Z ~ N(0,1) correlacionado para cada ticker."""
    z_market = rng.gauss(0, 1)
    sectors = {cfg.sector for cfg in DEFAULT_TICKERS.values()}
    z_sector = {s: rng.gauss(0, 1) for s in sectors}

    w_market = MARKET_CORRELATION
    w_sector = SECTOR_CORRELATION * (1 - MARKET_CORRELATION)
    w_idio = 1 - w_market - w_sector
    # normalizamos pesos al espacio de varianzas para mantener Var(Z) = 1
    norm = (w_market**2 + w_sector**2 + w_idio**2) ** 0.5

    shocks: dict[str, float] = {}
    for ticker, cfg in DEFAULT_TICKERS.items():
        z_idio = rng.gauss(0, 1)
        z = (w_market * z_market + w_sector * z_sector[cfg.sector] + w_idio * z_idio) / norm
        shocks[ticker] = z
    return shocks
```

### 5.4 Bucle Principal del Simulador

```python
# backend/app/market_data/simulator.py
import asyncio
import math
import random

from .base import MarketDataProvider, TickCallback
from .correlation import correlated_shocks
from .simulator_config import (
    DEFAULT_TICKERS,
    EVENT_PROBABILITY,
    EVENT_MAGNITUDE_RANGE,
)
from .types import PriceTick

TICK_INTERVAL_SECONDS = 0.5
# dt anualizado "efectivo": acelera el reloj de mercado para que se vea
# movimiento real en una sesión de demo corta. Aprox. un "día de trading" cada ~2 min reales.
EFFECTIVE_DT_PER_TICK = 1.0 / (390 * 60 / TICK_INTERVAL_SECONDS) * 8  # ajustable


class MarketSimulator(MarketDataProvider):
    def __init__(self, on_tick: TickCallback, seed: int | None = None) -> None:
        super().__init__(on_tick)
        self._rng = random.Random(seed)
        self._prices: dict[str, float] = {
            t: cfg.seed_price for t, cfg in DEFAULT_TICKERS.items()
        }
        self._tickers = set(DEFAULT_TICKERS.keys())
        self._task: asyncio.Task | None = None
        self._running = False

    def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper()
        if ticker not in self._prices:
            cfg = DEFAULT_TICKERS.get(ticker)
            seed_price = cfg.seed_price if cfg else 100.0
            self._prices[ticker] = seed_price
        self._tickers.add(ticker)

    def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker.upper())

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="market-simulator")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        while self._running:
            shocks = correlated_shocks(self._rng)
            for ticker in list(self._tickers):
                cfg = DEFAULT_TICKERS.get(ticker)
                mu = cfg.drift if cfg else 0.08
                sigma = cfg.volatility if cfg else 0.35
                z = shocks.get(ticker, self._rng.gauss(0, 1))

                prev = self._prices[ticker]
                dt = EFFECTIVE_DT_PER_TICK
                new_price = prev * math.exp(
                    (mu - sigma**2 / 2) * dt + sigma * math.sqrt(dt) * z
                )

                # Evento aleatorio: salto súbito
                if self._rng.random() < EVENT_PROBABILITY:
                    magnitude = self._rng.uniform(*EVENT_MAGNITUDE_RANGE)
                    sign = self._rng.choice([-1, 1])
                    new_price *= 1 + sign * magnitude

                new_price = max(new_price, 0.01)
                self._prices[ticker] = new_price

                tick = PriceTick.create(ticker, new_price, prev)
                await self._emit(tick)

            await asyncio.sleep(TICK_INTERVAL_SECONDS)
```

---

## 6. Cliente de la API de Massive (Polygon.io)

### 6.1 Estrategia de Polling

- Sin WebSocket: REST polling simple, compatible con cualquier nivel de suscripción.
- Sondea la **unión** de tickers vigilados por todos los usuarios (en este modelo de usuario único, equivale a la watchlist).
- Intervalo configurable: 15s para el nivel gratuito, 2-15s para niveles de pago (variable de entorno `MASSIVE_POLL_INTERVAL_SECONDS`).

```python
# backend/app/market_data/massive_config.py
import os

MASSIVE_API_KEY = os.environ.get("MASSIVE_API_KEY", "")
MASSIVE_BASE_URL = "https://api.massive.com"  # confirmado en planning/massive_api.md; rutas bajo /v2/...
MASSIVE_POLL_INTERVAL_SECONDS = float(os.environ.get("MASSIVE_POLL_INTERVAL_SECONDS", "15"))
```

### 6.2 Cliente HTTP Async

```python
# backend/app/market_data/massive_client.py
import asyncio
import logging

import httpx

from .base import MarketDataProvider, TickCallback
from .massive_config import MASSIVE_API_KEY, MASSIVE_BASE_URL, MASSIVE_POLL_INTERVAL_SECONDS
from .types import PriceTick

logger = logging.getLogger(__name__)


class MassiveMarketDataProvider(MarketDataProvider):
    def __init__(self, on_tick: TickCallback) -> None:
        super().__init__(on_tick)
        self._prev_prices: dict[str, float] = {}
        self._client = httpx.AsyncClient(
            base_url=MASSIVE_BASE_URL,
            headers={"Authorization": f"Bearer {MASSIVE_API_KEY}"},
            timeout=10.0,
        )
        self._task: asyncio.Task | None = None
        self._running = False

    def add_ticker(self, ticker: str) -> None:
        self._tickers.add(ticker.upper())

    def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker.upper())

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="massive-poller")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._client.aclose()

    async def _run_loop(self) -> None:
        while self._running:
            if self._tickers:
                try:
                    await self._poll_once()
                except httpx.HTTPError as exc:
                    logger.warning("Massive API poll failed: %s", exc)
            await asyncio.sleep(MASSIVE_POLL_INTERVAL_SECONDS)

    async def _poll_once(self) -> None:
        tickers_param = ",".join(sorted(self._tickers))
        resp = await self._client.get(
            "/snapshot/tickers", params={"tickers": tickers_param}
        )
        resp.raise_for_status()
        payload = resp.json()

        for entry in self._parse_response(payload):
            ticker, price = entry
            prev = self._prev_prices.get(ticker, price)
            tick = PriceTick.create(ticker, price, prev)
            self._prev_prices[ticker] = price
            await self._emit(tick)

    @staticmethod
    def _parse_response(payload: dict) -> list[tuple[str, float]]:
        """Adapta la forma específica de la respuesta de Massive/Polygon
        al formato (ticker, price) común. Ajustar a la forma real del JSON
        documentada por Massive."""
        results = []
        for item in payload.get("tickers", []):
            ticker = item["ticker"]
            price = item.get("lastTrade", {}).get("p") or item.get("day", {}).get("c")
            if price is not None:
                results.append((ticker, float(price)))
        return results
```

> Nota: la forma exacta del JSON de Massive debe confirmarse contra la documentación real de la API antes de integrar; `_parse_response` está aislado precisamente para que ese ajuste no afecte al resto del sistema.

---

## 7. Selección del Proveedor (Factory)

```python
# backend/app/market_data/factory.py
import os

from .base import MarketDataProvider, TickCallback
from .massive_client import MassiveMarketDataProvider
from .simulator import MarketSimulator


def build_market_data_provider(on_tick: TickCallback) -> MarketDataProvider:
    massive_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if massive_key:
        return MassiveMarketDataProvider(on_tick)
    return MarketSimulator(on_tick)
```

---

## 8. Integración con el Ciclo de Vida de FastAPI

```python
# backend/app/main.py (fragmento relevante)
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .market_data.factory import build_market_data_provider
from .market_data.wiring import on_tick
from .market_data.cache import price_cache
from .db.init import ensure_db_initialized


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_db_initialized()

    provider = build_market_data_provider(on_tick)
    app.state.market_data_provider = provider

    # sembrar tickers iniciales: unión de watchlist + tickers con posición abierta
    # (una posición sin ticker en watchlist debe seguir recibiendo precios tras un reinicio)
    seed_tickers = set(load_watchlist_tickers()) | set(load_position_tickers())
    for ticker in seed_tickers:
        provider.add_ticker(ticker)

    await provider.start()
    try:
        yield
    finally:
        await provider.stop()


app = FastAPI(lifespan=lifespan)
```

Cuando el usuario añade/elimina un ticker vía `/api/watchlist`, el handler debe llamar a `app.state.market_data_provider.add_ticker(...)` / `remove_ticker(...)` además de persistir en SQLite.

---

## 9. Endpoint SSE

```python
# backend/app/routes/stream.py
import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from ..market_data.cache import price_cache

router = APIRouter()

HEARTBEAT_SECONDS = 15


@router.get("/api/stream/prices")
async def stream_prices(request: Request):
    async def event_generator():
        # 1. Snapshot inicial: el cliente recibe inmediatamente el último precio conocido
        #    de cada ticker, para no esperar al siguiente tick del simulador.
        snapshot = price_cache.snapshot()
        for ticker, cached in snapshot.items():
            yield {
                "event": "price",
                "data": json.dumps(
                    {
                        "ticker": ticker,
                        "price": cached.price,
                        "prev_price": cached.prev_price,
                        "timestamp": cached.timestamp,
                        "direction": "flat",
                    }
                ),
            }

        # 2. Suscripción a ticks en vivo
        queue = price_cache.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    tick = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                    yield {"event": "price", "data": json.dumps(tick.to_sse_dict())}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}  # mantiene viva la conexión
        finally:
            price_cache.unsubscribe(queue)

    return EventSourceResponse(event_generator())
```

`EventSourceResponse` proviene de `sse-starlette` (añadir a `pyproject.toml`). El cliente usa la `EventSource` nativa del navegador, que reintenta automáticamente la conexión — no se necesita lógica de reconexión manual en el backend, solo asegurar que el snapshot inicial siempre se reenvía al reconectar.

### Formato del evento SSE recibido por el frontend

```
event: price
data: {"ticker":"AAPL","price":191.23,"prev_price":190.87,"timestamp":"2026-06-23T10:15:30.512Z","direction":"up"}
```

---

## 10. Pruebas Unitarias Sugeridas (pytest)

```python
# backend/tests/market_data/test_simulator.py
import asyncio
import pytest

from app.market_data.simulator import MarketSimulator
from app.market_data.types import PriceTick


@pytest.mark.asyncio
async def test_simulator_emits_positive_prices():
    received: list[PriceTick] = []

    async def on_tick(tick: PriceTick):
        received.append(tick)

    sim = MarketSimulator(on_tick, seed=42)
    sim.add_ticker("AAPL")
    await sim.start()
    await asyncio.sleep(1.2)  # ~2 ticks a 0.5s
    await sim.stop()

    assert received
    assert all(t.price > 0 for t in received)


def test_both_providers_implement_interface():
    from app.market_data.base import MarketDataProvider
    from app.market_data.simulator import MarketSimulator
    from app.market_data.massive_client import MassiveMarketDataProvider

    assert issubclass(MarketSimulator, MarketDataProvider)
    assert issubclass(MassiveMarketDataProvider, MarketDataProvider)
```

```python
# backend/tests/market_data/test_correlation.py
import random
from app.market_data.correlation import correlated_shocks
from app.market_data.simulator_config import DEFAULT_TICKERS


def test_correlated_shocks_covers_all_tickers():
    rng = random.Random(1)
    shocks = correlated_shocks(rng)
    assert set(shocks.keys()) == set(DEFAULT_TICKERS.keys())
```

```python
# backend/tests/market_data/test_cache.py
import asyncio
import pytest

from app.market_data.cache import PriceCache
from app.market_data.types import PriceTick


@pytest.mark.asyncio
async def test_subscribers_receive_ticks():
    cache = PriceCache()
    q = cache.subscribe()
    tick = PriceTick.create("AAPL", 191.0, 190.0)
    await cache.update(tick)

    received = await asyncio.wait_for(q.get(), timeout=1)
    assert received.ticker == "AAPL"
    assert cache.snapshot()["AAPL"].price == 191.0
```

---

## 11. Dependencias a Añadir (`backend/pyproject.toml`)

```toml
[project]
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "sse-starlette",
    "httpx",
    "pydantic",
    # ...resto de dependencias del backend (litellm, etc.)
]

[dependency-groups]
dev = [
    "pytest",
    "pytest-asyncio",
]
```

---

## 12. Resumen de Archivos a Crear

```
backend/app/market_data/
├── __init__.py
├── types.py              # PriceTick, Direction
├── base.py                # MarketDataProvider (ABC)
├── cache.py                # PriceCache (singleton price_cache)
├── wiring.py                # callback on_tick -> price_cache
├── simulator_config.py      # TickerConfig, DEFAULT_TICKERS, parámetros GBM
├── correlation.py            # correlated_shocks()
├── simulator.py                # MarketSimulator
├── massive_config.py            # env vars de Massive
├── massive_client.py              # MassiveMarketDataProvider
└── factory.py                      # build_market_data_provider()

backend/app/routes/
└── stream.py              # GET /api/stream/prices

backend/tests/market_data/
├── test_simulator.py
├── test_correlation.py
└── test_cache.py
```

Este diseño cumple con la interfaz única descrita en `PLAN.md` §6, deja la caché de precios y el SSE completamente desacoplados de la fuente de datos, y permite intercambiar simulador ↔ Massive con solo la variable de entorno `MASSIVE_API_KEY`.
