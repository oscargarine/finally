import random
import statistics

from app.market_data.correlation import correlated_shocks


def test_correlated_shocks_covers_all_tickers() -> None:
    rng = random.Random(1)
    sectors = {"AAPL": "tech", "MSFT": "tech", "JPM": "finance"}
    shocks = correlated_shocks(rng, sectors)
    assert set(shocks.keys()) == set(sectors.keys())


def test_shocks_are_roughly_standard_normal() -> None:
    rng = random.Random(7)
    sectors = {f"T{i}": "tech" for i in range(20)}

    samples: list[float] = []
    for _ in range(500):
        shocks = correlated_shocks(rng, sectors)
        samples.extend(shocks.values())

    mean = statistics.mean(samples)
    stdev = statistics.stdev(samples)
    assert abs(mean) < 0.1
    assert 0.85 < stdev < 1.15


def test_same_sector_tickers_move_more_alike_than_different_sectors() -> None:
    rng = random.Random(42)
    sectors = {"A1": "tech", "A2": "tech", "B1": "finance"}

    same_sector_diffs = []
    diff_sector_diffs = []
    for _ in range(300):
        shocks = correlated_shocks(rng, sectors)
        same_sector_diffs.append(abs(shocks["A1"] - shocks["A2"]))
        diff_sector_diffs.append(abs(shocks["A1"] - shocks["B1"]))

    assert statistics.mean(same_sector_diffs) < statistics.mean(diff_sector_diffs)


def test_deterministic_given_same_seed() -> None:
    sectors = {"AAPL": "tech"}
    shocks_a = correlated_shocks(random.Random(99), sectors)
    shocks_b = correlated_shocks(random.Random(99), sectors)
    assert shocks_a == shocks_b


def test_handles_a_brand_new_sector_not_seen_before() -> None:
    rng = random.Random(5)
    sectors = {"AAPL": "tech", "PYPL": "fintech-startup"}

    shocks = correlated_shocks(rng, sectors)

    assert set(shocks.keys()) == {"AAPL", "PYPL"}
    assert all(isinstance(z, float) for z in shocks.values())
