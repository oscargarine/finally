from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TickerConfig:
    seed_price: float
    drift: float  # mu anualizado, p.ej. 0.08 = 8%/año
    volatility: float  # sigma anualizado, p.ej. 0.35 = 35%/año
    sector: str  # para correlación entre sectores


DEFAULT_TICKERS: dict[str, TickerConfig] = {
    "AAPL": TickerConfig(190.00, 0.10, 0.28, "tech"),
    "GOOGL": TickerConfig(175.00, 0.09, 0.30, "tech"),
    "MSFT": TickerConfig(420.00, 0.10, 0.26, "tech"),
    "AMZN": TickerConfig(185.00, 0.11, 0.32, "tech"),
    "TSLA": TickerConfig(250.00, 0.05, 0.55, "auto"),
    "NVDA": TickerConfig(135.00, 0.18, 0.50, "tech"),
    "META": TickerConfig(580.00, 0.10, 0.34, "tech"),
    "JPM": TickerConfig(215.00, 0.07, 0.22, "finance"),
    "V": TickerConfig(310.00, 0.08, 0.20, "finance"),
    "NFLX": TickerConfig(700.00, 0.09, 0.33, "media"),
}

# Parámetros por defecto para tickers añadidos dinámicamente (no pre-configurados).
GENERIC_TICKER_DRIFT = 0.06
GENERIC_TICKER_VOLATILITY = 0.30
GENERIC_TICKER_SECTOR = "general"
GENERIC_SEED_PRICE_RANGE = (10.0, 500.0)

# Acoplamiento de movimiento entre sectores (0 = independiente, 1 = en bloque)
SECTOR_CORRELATION = 0.55
MARKET_CORRELATION = 0.35  # factor de mercado global compartido por todos los tickers

# Probabilidad por tick de un "evento" de salto brusco, y su magnitud
EVENT_PROBABILITY = 0.0008  # ~ uno cada ~20 min a 500ms/tick
EVENT_MAGNITUDE_RANGE = (0.02, 0.05)

TICK_INTERVAL_SECONDS = 0.5
# dt anualizado "efectivo": acelera el reloj de mercado para que se vea movimiento
# real en una sesión de demo corta (ver planning/market_simulator.md §5).
EFFECTIVE_DT_PER_TICK = 1.0 / 360
