import pytest

from app.market_data.factory import build_market_data_provider
from app.market_data.massive_client import MassiveMarketDataProvider
from app.market_data.simulator import MarketSimulator
from app.market_data.types import PriceTick


async def noop_on_tick(tick: PriceTick) -> None:
    pass


def test_uses_simulator_when_massive_key_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    provider = build_market_data_provider(noop_on_tick)
    assert isinstance(provider, MarketSimulator)


def test_uses_simulator_when_massive_key_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", "   ")
    provider = build_market_data_provider(noop_on_tick)
    assert isinstance(provider, MarketSimulator)


async def test_uses_massive_when_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    provider = build_market_data_provider(noop_on_tick)
    assert isinstance(provider, MassiveMarketDataProvider)
    await provider._client.aclose()
