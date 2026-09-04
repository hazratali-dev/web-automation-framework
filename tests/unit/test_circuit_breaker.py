import asyncio

import pytest

from src.infrastructure.resilience.circuit_breaker import (
    AsyncCircuitBreaker,
    CircuitOpenError,
    CircuitState,
    CircuitBreakerRegistry,
)


async def test_starts_closed_and_allows_calls():
    breaker = AsyncCircuitBreaker(fail_max=3, reset_timeout=10.0)
    assert breaker.state == CircuitState.CLOSED
    await breaker.before_call()  # should not raise


async def test_opens_after_fail_max_consecutive_failures():
    breaker = AsyncCircuitBreaker(fail_max=3, reset_timeout=10.0)
    for _ in range(3):
        await breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        await breaker.before_call()


async def test_success_resets_failure_count_and_stays_closed():
    breaker = AsyncCircuitBreaker(fail_max=3, reset_timeout=10.0)
    await breaker.record_failure()
    await breaker.record_failure()
    await breaker.record_success()
    await breaker.record_failure()  # only 1 consecutive failure since the reset
    assert breaker.state == CircuitState.CLOSED


async def test_transitions_to_half_open_after_reset_timeout():
    breaker = AsyncCircuitBreaker(fail_max=1, reset_timeout=0.05)
    await breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    await asyncio.sleep(0.1)
    assert breaker.state == CircuitState.HALF_OPEN
    await breaker.before_call()  # half-open allows exactly one probe through


async def test_half_open_failure_reopens_the_circuit():
    breaker = AsyncCircuitBreaker(fail_max=1, reset_timeout=0.05)
    await breaker.record_failure()
    await asyncio.sleep(0.1)
    assert breaker.state == CircuitState.HALF_OPEN
    await breaker.record_failure()
    assert breaker.state == CircuitState.OPEN


async def test_registry_returns_the_same_breaker_for_the_same_key():
    registry = CircuitBreakerRegistry()
    a = await registry.get("target:123")
    b = await registry.get("target:123")
    c = await registry.get("proxy:456")
    assert a is b
    assert a is not c
