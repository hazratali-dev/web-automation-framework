from src.shared.retry import compute_backoff


def test_backoff_grows_with_attempt_number():
    delays = [compute_backoff(a, base_delay=1.0, max_delay=100.0) for a in (1, 2, 3, 4)]
    # jitter adds noise, but the underlying exponential base still dominates
    # by a wide margin at these attempt counts (1, 2, 4, 8 base seconds).
    assert delays[0] < delays[1] < delays[2] < delays[3]


def test_backoff_respects_max_delay_cap():
    delay = compute_backoff(20, base_delay=1.0, max_delay=5.0)
    assert delay <= 5.0 * 1.3  # max_delay plus the worst-case jitter on top of it


def test_backoff_is_never_negative_or_zero():
    for attempt in range(1, 10):
        assert compute_backoff(attempt, base_delay=0.5) > 0
