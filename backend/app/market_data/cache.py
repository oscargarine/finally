import asyncio
from dataclasses import dataclass

from .types import PriceTick


@dataclass(slots=True)
class CachedPrice:
    price: float
    prev_price: float
    timestamp: str
    session_open: float


class PriceCache:
    """Caché en memoria + fan-out pub/sub para los streams SSE.

    Una única instancia es escrita por el proveedor de datos de mercado activo
    (simulador o Massive) y leída por cualquier número de suscriptores SSE.
    """

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
                session_open=tick.session_open,
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
        return {
            k: CachedPrice(v.price, v.prev_price, v.timestamp, v.session_open)
            for k, v in self._latest.items()
        }

    def get(self, ticker: str) -> CachedPrice | None:
        return self._latest.get(ticker)

    def subscribe(self) -> "asyncio.Queue[PriceTick]":
        q: asyncio.Queue[PriceTick] = asyncio.Queue(maxsize=256)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: "asyncio.Queue[PriceTick]") -> None:
        self._subscribers.discard(q)


# Instancia única a nivel de aplicación
price_cache = PriceCache()
