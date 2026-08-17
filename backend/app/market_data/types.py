from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


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
    session_open: float  # ver planning/PLAN.md §6 — base para el "% de cambio diario"

    @classmethod
    def create(
        cls,
        ticker: str,
        price: float,
        prev_price: float,
        *,
        session_open: float | None = None,
    ) -> "PriceTick":
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
            # sin referencia de sesión explícita (p.ej. ticks ad-hoc en tests),
            # el propio precio actual es la mejor aproximación disponible
            session_open=round(session_open if session_open is not None else price, 4),
        )

    def to_sse_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "prev_price": self.prev_price,
            "timestamp": self.timestamp,
            "direction": self.direction.value,
            "session_open": self.session_open,
        }
