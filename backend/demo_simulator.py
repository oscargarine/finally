"""Demo de terminal del simulador de mercado de FinAlly.

Arranca el MarketSimulator real (la misma tarea en segundo plano que usa el
backend) y muestra una tabla en vivo con precios, variación y mini-sparklines,
demostrando que el simulador genera datos de mercado plausibles.

Uso:
    uv run python demo_simulator.py            # 30 s, tickers por defecto
    uv run python demo_simulator.py --seconds 15
    uv run python demo_simulator.py --tickers AAPL,NVDA,TSLA --seed 42
"""

import argparse
import asyncio
import sys
from collections import defaultdict, deque

from app.market_data.simulator import MarketSimulator
from app.market_data.simulator_config import DEFAULT_TICKERS, TICK_INTERVAL_SECONDS
from app.market_data.types import Direction, PriceTick

# Paleta de FinAlly (ANSI truecolor).
GREEN = "\033[38;2;22;199;132m"
RED = "\033[38;2;234;57;67m"
YELLOW = "\033[38;2;236;173;10m"
BLUE = "\033[38;2;32;157;215m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
SPARK = "▁▂▃▄▅▆▇█"


class Dashboard:
    """Acumula ticks y redibuja una tabla de terminal en el sitio."""

    def __init__(self, tickers: list[str]) -> None:
        self._tickers = tickers
        self._seed = {t: DEFAULT_TICKERS[t].seed_price for t in tickers if t in DEFAULT_TICKERS}
        self._latest: dict[str, PriceTick] = {}
        self._history: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=40))
        self._ticks = 0
        self._lines_drawn = 0

    async def on_tick(self, tick: PriceTick) -> None:
        self._latest[tick.ticker] = tick
        self._history[tick.ticker].append(tick.price)
        self._seed.setdefault(tick.ticker, tick.prev_price)
        self._ticks += 1

    def _sparkline(self, ticker: str) -> str:
        prices = list(self._history[ticker])
        if len(prices) < 2:
            return DIM + "·" * 12 + RESET
        lo, hi = min(prices), max(prices)
        span = hi - lo or 1.0
        return "".join(SPARK[min(7, int((p - lo) / span * 7))] for p in prices[-12:])

    def render(self, elapsed: float) -> None:
        rows = []
        for ticker in self._tickers:
            tick = self._latest.get(ticker)
            if tick is None:
                rows.append(f"  {ticker:<6} {DIM}esperando primer tick…{RESET}")
                continue
            seed = self._seed.get(ticker, tick.price)
            pct = (tick.price - seed) / seed * 100 if seed else 0.0
            color = GREEN if pct >= 0 else RED
            arrow = (
                "▲"
                if tick.direction is Direction.UP
                else "▼"
                if tick.direction is Direction.DOWN
                else "="
            )
            rows.append(
                f"  {BOLD}{ticker:<6}{RESET} "
                f"${tick.price:>9,.2f}  "
                f"{color}{arrow} {pct:>+6.2f}%{RESET}  "
                f"{BLUE}{self._sparkline(ticker)}{RESET}"
            )

        header = (
            f"{BOLD}{YELLOW}  FinAlly — Simulador de Mercado (GBM){RESET}\n"
            f"  {DIM}{elapsed:5.1f}s · {self._ticks} ticks emitidos · "
            f"intervalo {TICK_INTERVAL_SECONDS * 1000:.0f}ms{RESET}\n"
            f"  {DIM}{'TICKER':<6} {'PRECIO':>10}  {'CAMBIO vs. SEMILLA':<13}  SPARKLINE{RESET}"
        )
        out = header + "\n" + "\n".join(rows)

        if self._lines_drawn:
            sys.stdout.write(f"\033[{self._lines_drawn}A")  # subir el cursor
        sys.stdout.write("\033[J" + out + "\n")  # limpiar hacia abajo y escribir
        sys.stdout.flush()
        self._lines_drawn = out.count("\n") + 1


async def run(tickers: list[str], seconds: float, seed: int | None) -> None:
    dashboard = Dashboard(tickers)
    sim = MarketSimulator(on_tick=dashboard.on_tick, seed=seed)
    for ticker in tickers:
        sim.add_ticker(ticker)

    sys.stdout.write("\033[?25l")  # ocultar cursor
    await sim.start()
    try:
        loop = asyncio.get_running_loop()
        start = loop.time()
        while (elapsed := loop.time() - start) < seconds:
            dashboard.render(elapsed)
            await asyncio.sleep(TICK_INTERVAL_SECONDS)
        dashboard.render(seconds)
    finally:
        await sim.stop()
        sys.stdout.write("\033[?25h")  # mostrar cursor
        sys.stdout.flush()

    print(f"\n{GREEN}✓ Demo completada: {dashboard._ticks} ticks generados sin errores.{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo en terminal del simulador de mercado FinAlly."
    )
    parser.add_argument("--seconds", type=float, default=30.0, help="Duración de la demo (s).")
    parser.add_argument(
        "--tickers", type=str, default="", help="Lista separada por comas; vacío = por defecto."
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Semilla RNG para resultados reproducibles."
    )
    args = parser.parse_args()

    tickers = (
        [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        if args.tickers
        else list(DEFAULT_TICKERS.keys())
    )

    try:
        asyncio.run(run(tickers, args.seconds, args.seed))
    except KeyboardInterrupt:
        sys.stdout.write("\033[?25h\n")
        print(f"{DIM}Interrumpido por el usuario.{RESET}")


if __name__ == "__main__":
    main()
