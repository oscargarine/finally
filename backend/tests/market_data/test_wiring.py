from app.market_data.cache import price_cache
from app.market_data.types import PriceTick
from app.market_data.wiring import on_tick


async def test_on_tick_writes_through_to_the_shared_price_cache() -> None:
    tick = PriceTick.create("WIRE", 10.0, 9.0)
    await on_tick(tick)

    cached = price_cache.get("WIRE")

    assert cached is not None

    assert cached.price == 10.0
