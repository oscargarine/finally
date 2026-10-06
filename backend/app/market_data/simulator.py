import asyncio
import contextlib
import math
import random

from .base import MarketDataProvider, TickCallback
from .correlation import correlated_shocks
from .simulator_config import (
    DEFAULT_TICKERS,
    EFFECTIVE_DT_PER_TICK,
    EVENT_MAGNITUDE_RANGE,
    EVENT_PROBABILITY,
    GENERIC_SEED_PRICE_RANGE,
    GENERIC_TICKER_DRIFT,
    GENERIC_TICKER_SECTOR,
    GENERIC_TICKER_VOLATILITY,
    TICK_INTERVAL_SECONDS,
)
from .types import PriceTick


class MarketSimulator(MarketDataProvider):
    """Simulador de mercado por movimiento browniano geométrico (GBM).

    Implementa la interfaz MarketDataProvider; ver planning/market_simulator.md
    para el modelo matemático y la justificación de las decisiones de diseño.
    """

    def __init__(self, on_tick: TickCallback, seed: int | None = None) -> None:
        super().__init__(on_tick)
        self._rng = random.Random(seed)
        self._prices: dict[str, float] = {t: cfg.seed_price for t, cfg in DEFAULT_TICKERS.items()}
        self._drift: dict[str, float] = {t: cfg.drift for t, cfg in DEFAULT_TICKERS.items()}
        self._volatility: dict[str, float] = {
            t: cfg.volatility for t, cfg in DEFAULT_TICKERS.items()
        }
        self._sector: dict[str, str] = {t: cfg.sector for t, cfg in DEFAULT_TICKERS.items()}
        # capturado una vez por ticker y fijo durante toda la vida del proceso (§6 "session_open")
        self._session_open: dict[str, float] = dict(self._prices)
        self._tickers = set(DEFAULT_TICKERS.keys())
        self._task: asyncio.Task[None] | None = None
        # referencias fuertes a los ticks inmediatos: el event loop solo guarda
        # referencias débiles, y una tarea sin referencia puede ser recolectada a medias
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._running = False

    def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper()
        if ticker not in self._prices:
            cfg = DEFAULT_TICKERS.get(ticker)
            if cfg is not None:
                self._prices[ticker] = cfg.seed_price
                self._drift[ticker] = cfg.drift
                self._volatility[ticker] = cfg.volatility
                self._sector[ticker] = cfg.sector
            else:
                self._prices[ticker] = self._lognormal_seed_price()
                self._drift[ticker] = GENERIC_TICKER_DRIFT
                self._volatility[ticker] = GENERIC_TICKER_VOLATILITY
                self._sector[ticker] = GENERIC_TICKER_SECTOR
        self._session_open.setdefault(ticker, self._prices[ticker])
        was_tracked = ticker in self._tickers
        self._tickers.add(ticker)
        if not was_tracked:
            self._emit_immediate_tick(ticker)

    def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker.upper())

    def get_last_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker.upper())

    def current_price(self, ticker: str) -> float | None:
        return self.get_last_price(ticker)

    def _emit_immediate_tick(self, ticker: str) -> None:
        """Emite un tick con el precio recién asignado sin esperar al próximo ciclo (§6).

        `add_ticker` es síncrono por contrato de interfaz, así que la emisión (que
        necesita `await`) se programa como tarea de fondo. Si todavía no hay un
        event loop corriendo (p.ej. se llama antes de `start()`), se omite en
        silencio: el primer `tick_once()` del bucle normal ya cubrirá ese ticker.
        """
        price = self._prices[ticker]
        session_open = self._session_open[ticker]
        tick = PriceTick.create(ticker, price, price, session_open=session_open)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        task = asyncio.create_task(self._emit(tick))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _lognormal_seed_price(self) -> float:
        low, high = GENERIC_SEED_PRICE_RANGE
        # log-uniforme: igual de probable un precio de $20 que de $200.
        return math.exp(self._rng.uniform(math.log(low), math.log(high)))

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="market-simulator")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while self._running:
            await self.tick_once()
            await asyncio.sleep(TICK_INTERVAL_SECONDS)

    async def tick_once(self) -> list[PriceTick]:
        """Calcula y emite un único paso de simulación para todos los tickers vigilados.

        Expuesto como método público (en lugar de solo el bucle privado) para que
        los tests puedan avanzar la simulación de forma determinista sin depender
        de temporizadores reales.
        """
        tickers = list(self._tickers)
        sectors = {t: self._sector[t] for t in tickers}
        shocks = correlated_shocks(self._rng, sectors)

        ticks: list[PriceTick] = []
        dt = EFFECTIVE_DT_PER_TICK
        for ticker in tickers:
            mu = self._drift[ticker]
            sigma = self._volatility[ticker]
            z = shocks[ticker]

            prev = self._prices[ticker]
            new_price = prev * math.exp((mu - sigma**2 / 2) * dt + sigma * math.sqrt(dt) * z)

            # Evento aleatorio idiosincrático: salto súbito del 2-5%.
            if self._rng.random() < EVENT_PROBABILITY:
                magnitude = self._rng.uniform(*EVENT_MAGNITUDE_RANGE)
                sign = self._rng.choice([-1, 1])
                new_price *= 1 + sign * magnitude

            new_price = max(new_price, 0.01)
            self._prices[ticker] = new_price

            tick = PriceTick.create(
                ticker, new_price, prev, session_open=self._session_open[ticker]
            )
            ticks.append(tick)
            await self._emit(tick)

        return ticks
