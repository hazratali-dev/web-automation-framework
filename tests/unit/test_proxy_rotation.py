from src.domain.entities.proxy import Proxy
from src.infrastructure.proxy.rotation import RoundRobinRotator, select_proxy, weighted_select


def make_proxies(n: int) -> list[Proxy]:
    return [Proxy(host=f"10.0.0.{i}", port=8080) for i in range(n)]


def test_round_robin_cycles_through_all_proxies_before_repeating():
    proxies = make_proxies(3)
    rotator = RoundRobinRotator()

    picks = [rotator.select(proxies).id for _ in range(6)]
    ordered_ids = sorted(p.id for p in proxies)

    assert picks[0:3] == ordered_ids
    assert picks[3:6] == ordered_ids  # second lap repeats the same order


def test_round_robin_returns_none_for_empty_list():
    assert RoundRobinRotator().select([]) is None


def test_weighted_select_never_picks_from_empty_list():
    assert weighted_select([]) is None


def test_weighted_select_strongly_favors_high_success_rate():
    strong = Proxy(host="strong", port=1, success_count=100, failure_count=0)
    weak = Proxy(host="weak", port=2, success_count=1, failure_count=99)

    picks = [weighted_select([strong, weak]).host for _ in range(200)]
    strong_ratio = picks.count("strong") / len(picks)

    assert strong_ratio > 0.9  # statistical, but threshold is generous enough to not flake


def test_select_proxy_dispatches_on_strategy_string():
    proxies = make_proxies(2)
    assert select_proxy(proxies, "round_robin") in proxies
    assert select_proxy(proxies, "weighted") in proxies
    assert select_proxy(proxies, "unknown-defaults-to-round-robin") in proxies
