from app.market_data.types import Direction, PriceTick


def test_create_sets_up_direction():
    tick = PriceTick.create("AAPL", 191.0, 190.0)
    assert tick.direction == Direction.UP

    tick = PriceTick.create("AAPL", 189.0, 190.0)
    assert tick.direction == Direction.DOWN

    tick = PriceTick.create("AAPL", 190.0, 190.0)
    assert tick.direction == Direction.FLAT


def test_create_rounds_prices():
    tick = PriceTick.create("AAPL", 191.123456, 190.987654)
    assert tick.price == 191.1235
    assert tick.prev_price == 190.9877


def test_create_sets_iso_utc_timestamp():
    tick = PriceTick.create("AAPL", 191.0, 190.0)
    assert tick.timestamp.endswith("+00:00")


def test_to_sse_dict_shape():
    tick = PriceTick.create("AAPL", 191.0, 190.0, session_open=188.0)
    payload = tick.to_sse_dict()
    assert payload == {
        "ticker": "AAPL",
        "price": 191.0,
        "prev_price": 190.0,
        "timestamp": tick.timestamp,
        "direction": "up",
        "session_open": 188.0,
    }


def test_create_defaults_session_open_to_price_when_not_given():
    tick = PriceTick.create("AAPL", 191.0, 190.0)
    assert tick.session_open == 191.0


def test_create_rounds_session_open():
    tick = PriceTick.create("AAPL", 191.0, 190.0, session_open=188.123456)
    assert tick.session_open == 188.1235
