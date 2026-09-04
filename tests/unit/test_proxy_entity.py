from src.domain.entities.proxy import Proxy


def make_proxy(**overrides) -> Proxy:
    defaults = dict(host="1.2.3.4", port=8080)
    defaults.update(overrides)
    return Proxy(**defaults)


def test_success_rate_defaults_to_1_when_no_history():
    proxy = make_proxy()
    assert proxy.success_rate == 1.0


def test_success_rate_reflects_history():
    proxy = make_proxy(success_count=3, failure_count=1)
    assert proxy.success_rate == 0.75


def test_record_success_resets_consecutive_failures_and_reactivates():
    proxy = make_proxy(is_active=False, consecutive_failures=2)
    proxy.record_success(latency_ms=120)
    assert proxy.is_active is True
    assert proxy.consecutive_failures == 0
    assert proxy.success_count == 1
    assert proxy.avg_latency_ms == 120


def test_record_failure_deactivates_after_threshold():
    proxy = make_proxy()
    proxy.record_failure(deactivate_after=3)
    assert proxy.is_active is True
    assert proxy.consecutive_failures == 1

    proxy.record_failure(deactivate_after=3)
    assert proxy.is_active is True

    proxy.record_failure(deactivate_after=3)
    assert proxy.is_active is False
    assert proxy.consecutive_failures == 3
    assert proxy.failure_count == 3


def test_proxy_url_includes_auth_when_present():
    proxy = make_proxy(username="u", password="p")
    assert proxy.proxy_url() == "http://u:p@1.2.3.4:8080"


def test_proxy_url_without_auth():
    proxy = make_proxy()
    assert proxy.proxy_url() == "http://1.2.3.4:8080"
