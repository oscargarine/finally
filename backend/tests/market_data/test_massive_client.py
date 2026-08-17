import asyncio
import json

import httpx
import pytest

from app.market_data.base import MarketDataProvider
from app.market_data.massive_client import SNAPSHOT_PATH, MassiveMarketDataProvider
from app.market_data.types import PriceTick


def snapshot_payload(entries: dict[str, dict]) -> dict:
    return {
        "status": "OK",
        "tickers": [{"ticker": ticker, **fields} for ticker, fields in entries.items()],
    }


def make_provider(handler) -> tuple[MassiveMarketDataProvider, list[PriceTick]]:
    received: list[PriceTick] = []

    async def on_tick(tick: PriceTick) -> None:
        received.append(tick)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://massive.test")
    provider = MassiveMarketDataProvider(on_tick, client=client)
    return provider, received


def test_implements_market_data_provider_interface():
    assert issubclass(MassiveMarketDataProvider, MarketDataProvider)


def test_add_and_remove_ticker():
    provider, _ = make_provider(lambda request: httpx.Response(200, json={"tickers": []}))
    provider.add_ticker("aapl")
    assert "AAPL" in provider.tickers

    provider.remove_ticker("AAPL")
    assert "AAPL" not in provider.tickers


async def test_poll_once_requests_the_union_of_tickers():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=snapshot_payload({}))

    provider, _ = make_provider(handler)
    provider.add_ticker("MSFT")
    provider.add_ticker("AAPL")

    await provider.poll_once()

    assert len(captured) == 1
    assert captured[0].url.path == SNAPSHOT_PATH
    assert captured[0].url.params["tickers"] == "AAPL,MSFT"


async def test_poll_once_parses_last_trade_price():
    payload = snapshot_payload(
        {"AAPL": {"lastTrade": {"p": 189.72, "t": 1735000000000}, "prevDay": {"c": 187.9}}}
    )
    provider, received = make_provider(lambda request: httpx.Response(200, json=payload))
    provider.add_ticker("AAPL")

    ticks = await provider.poll_once()

    assert len(ticks) == 1
    assert ticks[0].ticker == "AAPL"
    assert ticks[0].price == 189.72
    assert received == ticks


async def test_poll_once_falls_back_to_day_close_then_prev_day_close():
    payload = snapshot_payload(
        {
            "AAPL": {"day": {"c": 190.5}, "prevDay": {"c": 187.9}},
            "MSFT": {"prevDay": {"c": 410.0}},
        }
    )
    provider, _ = make_provider(lambda request: httpx.Response(200, json=payload))
    provider.add_ticker("AAPL")
    provider.add_ticker("MSFT")

    ticks = await provider.poll_once()
    prices = {t.ticker: t.price for t in ticks}

    assert prices["AAPL"] == 190.5
    assert prices["MSFT"] == 410.0


async def test_poll_once_uses_previous_seen_price_as_prev_price():
    prices = iter([100.0, 105.0])

    def handler(request: httpx.Request) -> httpx.Response:
        price = next(prices)
        return httpx.Response(200, json=snapshot_payload({"AAPL": {"lastTrade": {"p": price}}}))

    provider, _ = make_provider(handler)
    provider.add_ticker("AAPL")

    first = await provider.poll_once()
    second = await provider.poll_once()

    assert first[0].price == 100.0
    assert first[0].prev_price == 100.0  # primera vez: sin referencia previa
    assert second[0].price == 105.0
    assert second[0].prev_price == 100.0


async def test_poll_once_skips_entries_without_usable_price():
    payload = snapshot_payload({"AAPL": {}})
    provider, _ = make_provider(lambda request: httpx.Response(200, json=payload))
    provider.add_ticker("AAPL")

    ticks = await provider.poll_once()
    assert ticks == []


async def test_poll_once_raises_on_http_error():
    provider, _ = make_provider(lambda request: httpx.Response(500, json={"error": "boom"}))
    provider.add_ticker("AAPL")

    with pytest.raises(httpx.HTTPStatusError):
        await provider.poll_once()


async def test_run_loop_swallows_http_errors_and_keeps_polling():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(500, json={"error": "boom"})

    provider, _ = make_provider(handler)
    provider.add_ticker("AAPL")
    provider._poll_interval_seconds = 0.05

    await provider.start()
    try:
        await asyncio.sleep(0.2)
    finally:
        await provider.stop()

    assert call_count >= 2


def test_get_last_price_returns_none_before_first_poll():
    provider, _ = make_provider(lambda request: httpx.Response(200, json=snapshot_payload({})))
    provider.add_ticker("AAPL")
    assert provider.get_last_price("AAPL") is None


async def test_get_last_price_returns_last_polled_price():
    payload = snapshot_payload({"AAPL": {"lastTrade": {"p": 189.72}}})
    provider, _ = make_provider(lambda request: httpx.Response(200, json=payload))
    provider.add_ticker("AAPL")

    await provider.poll_once()

    assert provider.get_last_price("AAPL") == 189.72


async def test_poll_once_captures_session_open_from_prev_day_close():
    payload = snapshot_payload({"AAPL": {"lastTrade": {"p": 189.72}, "prevDay": {"c": 187.9}}})
    provider, _ = make_provider(lambda request: httpx.Response(200, json=payload))
    provider.add_ticker("AAPL")

    ticks = await provider.poll_once()

    assert ticks[0].session_open == 187.9


async def test_session_open_stays_fixed_once_captured():
    prices = iter([189.72, 195.0])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=snapshot_payload(
                {"AAPL": {"lastTrade": {"p": next(prices)}, "prevDay": {"c": 187.9}}}
            ),
        )

    provider, _ = make_provider(handler)
    provider.add_ticker("AAPL")

    first = await provider.poll_once()
    second = await provider.poll_once()

    assert first[0].session_open == 187.9
    assert second[0].session_open == 187.9


async def test_add_ticker_while_running_triggers_immediate_dedicated_poll():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=snapshot_payload({"AAPL": {"lastTrade": {"p": 189.72}}}))

    provider, received = make_provider(handler)
    provider._poll_interval_seconds = 100  # el ciclo normal no debe disparar en este test

    await provider.start()
    try:
        provider.add_ticker("AAPL")
        # da tiempo a que corra la tarea de fondo creada por add_ticker()
        for _ in range(50):
            if provider.get_last_price("AAPL") is not None:
                break
            await asyncio.sleep(0.01)
    finally:
        await provider.stop()

    assert provider.get_last_price("AAPL") == 189.72
    assert any(t.ticker == "AAPL" for t in received)
    # sondeo dedicado con un único ticker, no el ciclo periódico completo
    assert any(req.url.params["tickers"] == "AAPL" for req in captured)


async def test_add_ticker_while_not_running_does_not_poll_immediately():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=snapshot_payload({}))

    provider, _ = make_provider(handler)
    provider.add_ticker("AAPL")
    await asyncio.sleep(0)

    assert captured == []


async def test_stop_closes_the_http_client():
    provider, _ = make_provider(lambda request: httpx.Response(200, json=snapshot_payload({})))
    await provider.start()
    await provider.stop()

    assert provider._client.is_closed
