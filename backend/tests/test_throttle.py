"""Tests for the token-bucket RateLimiter (app/throttle.py). The clock is injected so
time advances deterministically without sleeping."""
from __future__ import annotations

from app.throttle import RateLimiter


def test_allows_up_to_capacity_then_blocks():
    rl = RateLimiter(capacity=3, refill_per_s=0, clock=lambda: 0.0)  # frozen clock, no refill
    assert rl.allow() and rl.allow() and rl.allow()
    assert not rl.allow()  # bucket empty


def test_refills_over_time():
    now = [0.0]
    rl = RateLimiter(capacity=2, refill_per_s=1.0, clock=lambda: now[0])
    assert rl.allow() and rl.allow()  # drained
    assert not rl.allow()
    now[0] = 1.0  # one second → one token back
    assert rl.allow()
    assert not rl.allow()


def test_refill_is_capped_at_capacity():
    now = [0.0]
    rl = RateLimiter(capacity=2, refill_per_s=10.0, clock=lambda: now[0])
    now[0] = 100.0  # a huge gap must not overflow the bucket to 1000 tokens
    assert rl.allow() and rl.allow()
    assert not rl.allow()  # only `capacity` tokens accrued, not elapsed * refill
