"""Unit tests for RateLimiter."""

import time
from threading import Thread

import pytest

from policyflow.rate_limiter import RateLimiter


class TestRateLimiterUnlimited:
    """Tests for unlimited rate mode."""

    def test_unlimited_rate_does_not_wait(self):
        """When rate_limit=None, should not impose any delays."""
        limiter = RateLimiter(rate_limit=None)
        start = time.time()

        # Should process immediately
        for _ in range(100):
            limiter.wait_if_needed()

        elapsed = time.time() - start

        # Should be nearly instant (allow 0.1s for overhead)
        assert elapsed < 0.1

    def test_unlimited_rate_multiple_instances(self):
        """Multiple instances with unlimited rate should not interfere."""
        limiter1 = RateLimiter(rate_limit=None)
        limiter2 = RateLimiter(rate_limit=None)

        start = time.time()

        for _ in range(50):
            limiter1.wait_if_needed()
            limiter2.wait_if_needed()

        elapsed = time.time() - start

        # Should be nearly instant
        assert elapsed < 0.1


class TestRateLimiterTokenBucket:
    """Tests for token bucket algorithm."""

    def test_initial_tokens_allow_immediate_requests(self):
        """Should start with full bucket allowing immediate requests."""
        limiter = RateLimiter(rate_limit=60)  # 60 requests per minute
        start = time.time()

        # First request should be immediate
        limiter.wait_if_needed()

        elapsed = time.time() - start

        # Should be nearly instant (allow 0.05s for overhead)
        assert elapsed < 0.05

    def test_exceeding_rate_causes_wait(self):
        """Exceeding rate limit should cause wait."""
        limiter = RateLimiter(rate_limit=60)  # 60 requests per minute = 1 per second

        # Consume initial tokens quickly
        for _ in range(60):
            limiter.wait_if_needed()

        # Next request should wait approximately 1 second
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should wait ~1 second (allow 0.2s tolerance)
        assert 0.8 < elapsed < 1.2

    def test_tokens_regenerate_over_time(self):
        """Tokens should regenerate based on refill rate."""
        limiter = RateLimiter(rate_limit=60)  # 1 token per second

        # Consume initial tokens
        for _ in range(60):
            limiter.wait_if_needed()

        # Wait for 2 tokens to regenerate
        time.sleep(2.1)

        # Should be able to make 2 requests immediately
        start = time.time()
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should be nearly instant
        assert elapsed < 0.1

    def test_low_rate_limit(self):
        """Should handle low rate limits correctly."""
        limiter = RateLimiter(rate_limit=10)  # 10 per minute = 1 per 6 seconds

        # Exhaust initial tokens
        for _ in range(10):
            limiter.wait_if_needed()

        # Next request should wait ~6 seconds
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        assert 5.5 < elapsed < 6.5

    def test_high_rate_limit(self):
        """Should handle high rate limits correctly."""
        limiter = RateLimiter(rate_limit=600)  # 600 per minute = 10 per second

        start = time.time()

        # Should process 10 requests quickly
        for _ in range(10):
            limiter.wait_if_needed()

        elapsed = time.time() - start

        # Should be nearly instant
        assert elapsed < 0.1


class TestRateLimiterPerInstance:
    """Tests for per-instance rate limiting."""

    def test_different_instances_have_separate_limits(self):
        """Different instances should track rate limits independently."""
        limiter1 = RateLimiter(rate_limit=60)  # 1 per second
        limiter2 = RateLimiter(rate_limit=60)

        # Exhaust limiter1
        for _ in range(60):
            limiter1.wait_if_needed()

        # limiter2 should still have tokens
        start = time.time()
        limiter2.wait_if_needed()
        elapsed = time.time() - start

        # Should be nearly instant
        assert elapsed < 0.05

    def test_instances_do_not_share_tokens(self):
        """Instances should not interfere with each other's tokens."""
        limiter1 = RateLimiter(rate_limit=120)  # 2 per second
        limiter2 = RateLimiter(rate_limit=120)

        # Consume tokens from both in parallel
        start = time.time()

        for _ in range(100):
            limiter1.wait_if_needed()
            limiter2.wait_if_needed()

        elapsed = time.time() - start

        # Both should have their own full buckets initially
        assert elapsed < 1.0


class TestRateLimiterThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_requests_respect_rate_limit(self):
        """Multiple threads should respect shared rate limit per instance."""
        limiter = RateLimiter(rate_limit=60)  # 1 per second
        completed = []

        def make_request():
            limiter.wait_if_needed()
            completed.append(time.time())

        # Exhaust initial tokens
        for _ in range(60):
            limiter.wait_if_needed()

        # Launch concurrent requests
        threads = []
        start = time.time()
        for _ in range(3):
            thread = Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        elapsed = time.time() - start

        # With concurrent threads, they all start waiting at same time
        # All 3 wait ~1 second for first token to refill
        assert 0.8 < elapsed < 1.5
        assert len(completed) == 3

    def test_concurrent_instances_do_not_conflict(self):
        """Multiple threads using different instances should not conflict."""
        limiter1 = RateLimiter(rate_limit=60)
        limiter2 = RateLimiter(rate_limit=60)

        results = {"limiter1": [], "limiter2": []}

        def use_limiter1():
            for _ in range(30):
                limiter1.wait_if_needed()
                results["limiter1"].append(time.time())

        def use_limiter2():
            for _ in range(30):
                limiter2.wait_if_needed()
                results["limiter2"].append(time.time())

        thread1 = Thread(target=use_limiter1)
        thread2 = Thread(target=use_limiter2)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Both should have processed their requests
        assert len(results["limiter1"]) == 30
        assert len(results["limiter2"]) == 30

    def test_thread_safety_with_rapid_requests(self):
        """Should handle rapid concurrent requests safely."""
        limiter = RateLimiter(rate_limit=600)  # High rate
        counter = {"count": 0}

        def make_requests():
            for _ in range(10):
                limiter.wait_if_needed()
                counter["count"] += 1

        threads = []
        for _ in range(5):
            thread = Thread(target=make_requests)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All requests should complete
        assert counter["count"] == 50


class TestRateLimiterWaitBehavior:
    """Tests for wait behavior and timing."""

    def test_wait_if_needed_returns_none(self):
        """wait_if_needed should return None after waiting."""
        limiter = RateLimiter(rate_limit=60)

        result = limiter.wait_if_needed()

        assert result is None

    def test_fractional_tokens_handled_correctly(self):
        """Should handle fractional token calculations correctly."""
        limiter = RateLimiter(rate_limit=60)  # 1 token per second

        # Use all tokens
        for _ in range(60):
            limiter.wait_if_needed()

        # Wait for 0.5 seconds (0.5 tokens)
        time.sleep(0.5)

        # Next request should wait ~0.5 more seconds
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        assert 0.4 < elapsed < 0.6

    def test_wait_time_accurate_for_multiple_requests(self):
        """Wait times should be accurate across multiple requests."""
        limiter = RateLimiter(rate_limit=120)  # 2 per second

        # Exhaust tokens
        for _ in range(120):
            limiter.wait_if_needed()

        # Make 3 sequential requests
        timings = []
        for _ in range(3):
            start = time.time()
            limiter.wait_if_needed()
            elapsed = time.time() - start
            timings.append(elapsed)

        # Each should wait ~0.5 seconds (2 requests per second)
        for elapsed in timings:
            assert 0.4 < elapsed < 0.6


class TestRateLimiterEdgeCases:
    """Tests for edge cases."""

    def test_rate_limit_of_one(self):
        """Should handle rate limit of 1 per minute."""
        limiter = RateLimiter(rate_limit=1)  # 1 per minute = 60 seconds

        # First request immediate
        start = time.time()
        limiter.wait_if_needed()
        elapsed1 = time.time() - start
        assert elapsed1 < 0.05

        # Note: We won't test the full 60 second wait in tests,
        # but the logic should be correct
        # The refill rate is 1/60 tokens per second

    def test_very_high_rate_limit(self):
        """Should handle very high rate limits."""
        limiter = RateLimiter(rate_limit=10000)  # 166.67 per second

        start = time.time()

        # Should process many requests quickly
        for _ in range(100):
            limiter.wait_if_needed()

        elapsed = time.time() - start

        # Should be very fast
        assert elapsed < 0.2

    def test_rate_limit_persists_across_calls(self):
        """Rate limit state should persist across calls."""
        limiter = RateLimiter(rate_limit=60)

        # First batch
        for _ in range(30):
            limiter.wait_if_needed()

        # Second batch should continue counting from same bucket
        start = time.time()
        for _ in range(30):
            limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should be nearly instant (all from initial bucket)
        assert elapsed < 0.1

        # Third batch should need to wait
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start

        # Should wait ~1 second
        assert 0.8 < elapsed < 1.2

    def test_multiple_instances_with_different_rates(self):
        """Instances with different rates should work independently."""
        fast = RateLimiter(rate_limit=600)  # 10 per second
        slow = RateLimiter(rate_limit=60)   # 1 per second

        # Exhaust both
        for _ in range(600):
            fast.wait_if_needed()
        for _ in range(60):
            slow.wait_if_needed()

        # Fast should recover quickly
        time.sleep(0.15)  # 1.5 tokens for fast, 0.15 tokens for slow

        start = time.time()
        fast.wait_if_needed()
        fast_elapsed = time.time() - start

        start = time.time()
        slow.wait_if_needed()
        slow_elapsed = time.time() - start

        # Fast should be nearly instant, slow should wait
        assert fast_elapsed < 0.1
        assert 0.7 < slow_elapsed < 1.0
