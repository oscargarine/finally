import pytest

from app.market_data.base import MarketDataProvider
from app.market_data.types import PriceTick


async def _noop_on_tick(tick: PriceTick) -> None:
    pass


def test_cannot_instantiate_abstract_provider() -> None:
    with pytest.raises(TypeError):
        MarketDataProvider(on_tick=_noop_on_tick)  # type: ignore[abstract]


class DummyProvider(MarketDataProvider):
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def add_ticker(self, ticker: str) -> None:
        self._tickers.add(ticker)

    def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker)

    def get_last_price(self, ticker: str) -> float | None:
        return None


async def test_emit_invokes_on_tick_callback() -> None:
    received = []

    async def on_tick(tick: PriceTick) -> None:
        received.append(tick)

    provider = DummyProvider(on_tick)
    tick = PriceTick.create("AAPL", 191.0, 190.0)
    await provider._emit(tick)

    assert received == [tick]


def test_tickers_property_reflects_subclass_state() -> None:
    provider = DummyProvider(_noop_on_tick)
    provider.add_ticker("AAPL")
    provider.add_ticker("msft")

    assert provider.tickers == frozenset({"AAPL", "msft"})
