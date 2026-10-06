import asyncio
import contextlib
import logging
from typing import Any

import httpx

from .base import MarketDataProvider, TickCallback
from .massive_config import (
    MASSIVE_API_KEY,
    MASSIVE_BASE_URL,
    MASSIVE_POLL_INTERVAL_SECONDS,
)
from .types import PriceTick

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"


class MassiveMarketDataProvider(MarketDataProvider):
    """Cliente de la API de Massive (antes Polygon.io) — sondeo REST por lotes.

    Implementa la misma interfaz MarketDataProvider que el simulador (ver
    planning/massive_api.md y planning/market_data_design.md §6). El estado
    interno de "último precio conocido" se usa para calcular `prev_price` en
    tickers ya vistos; para un ticker visto por primera vez se usa el cierre
    del día anterior (`prevDay.c`) como referencia, si está disponible.
    """

    def __init__(
        self,
        on_tick: TickCallback,
        *,
        api_key: str = MASSIVE_API_KEY,
        base_url: str = MASSIVE_BASE_URL,
        poll_interval_seconds: float = MASSIVE_POLL_INTERVAL_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(on_tick)
        self._poll_interval_seconds = poll_interval_seconds
        self._prev_prices: dict[str, float] = {}
        # capturado una vez por ticker (prevDay.c) y fijo mientras dure el proceso
        # (§6 "session_open")
        self._session_open: dict[str, float] = {}
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        self._task: asyncio.Task[None] | None = None
        # referencias fuertes a los sondeos dedicados: el event loop solo guarda
        # referencias débiles, y una tarea sin referencia puede ser recolectada a medias
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._running = False

    def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper()
        is_new = ticker not in self._tickers
        self._tickers.add(ticker)
        if is_new and self._running:
            # sondeo dedicado inmediato: evita que ensure_ticker() tenga que esperar
            # hasta el siguiente ciclo periódico completo (hasta MASSIVE_POLL_INTERVAL_SECONDS)
            # para obtener el primer precio (ver planning/PLAN.md §6)
            task = asyncio.create_task(self._poll_new_ticker_immediately(ticker))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker.upper())

    def get_last_price(self, ticker: str) -> float | None:
        return self._prev_prices.get(ticker.upper())

    async def _poll_new_ticker_immediately(self, ticker: str) -> None:
        try:
            await self._poll_tickers({ticker})
        except httpx.HTTPError as exc:
            logger.warning("Massive dedicated poll for new ticker %s failed: %s", ticker, exc)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="massive-poller")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._client.aclose()

    async def _run_loop(self) -> None:
        while self._running:
            if self._tickers:
                try:
                    await self.poll_once()
                except httpx.HTTPError as exc:
                    logger.warning("Massive API poll failed: %s", exc)
            await asyncio.sleep(self._poll_interval_seconds)

    async def poll_once(self) -> list[PriceTick]:
        """Realiza una única llamada de snapshot por lotes y emite los ticks resultantes.

        Público (no solo invocado desde el bucle privado) para que los tests
        puedan ejercitar el parseo y la emisión sin depender de temporizadores.
        """
        return await self._poll_tickers(self._tickers)

    async def _poll_tickers(self, tickers: set[str]) -> list[PriceTick]:
        tickers_param = ",".join(sorted(tickers))
        resp = await self._client.get(SNAPSHOT_PATH, params={"tickers": tickers_param})
        resp.raise_for_status()
        payload = resp.json()

        ticks: list[PriceTick] = []
        for ticker, price, session_open in self._parse_response(payload):
            prev = self._prev_prices.get(ticker, price)
            # se fija la primera vez que se ve el ticker y queda fijo después
            resolved_session_open = self._session_open.setdefault(
                ticker, session_open if session_open is not None else price
            )
            tick = PriceTick.create(ticker, price, prev, session_open=resolved_session_open)
            self._prev_prices[ticker] = price
            ticks.append(tick)
            await self._emit(tick)
        return ticks

    @staticmethod
    def _parse_response(payload: dict[str, Any]) -> list[tuple[str, float, float | None]]:
        """Adapta la respuesta de snapshot de Massive a (ticker, price, session_open).

        El precio prioriza el último trade, y recurre al cierre del día / cierre
        anterior si el último trade no está disponible (mercado cerrado, plan con
        retraso). `session_open` es siempre `prevDay.c` (cierre del día anterior),
        independientemente de qué campo se haya usado como precio (§6).
        """
        results: list[tuple[str, float, float | None]] = []
        for item in payload.get("tickers", []):
            ticker = item.get("ticker")
            if not ticker:
                continue
            price = (
                item.get("lastTrade", {}).get("p")
                or item.get("day", {}).get("c")
                or item.get("prevDay", {}).get("c")
            )
            if price is None:
                continue
            prev_close = item.get("prevDay", {}).get("c")
            session_open = float(prev_close) if prev_close is not None else None
            results.append((ticker, float(price), session_open))
        return results
