"""Unit tests for CacheManager."""

import time
from pathlib import Path
from threading import Thread
from unittest.mock import patch

import pytest
import yaml

from policyflow.cache import CacheManager


class TestCacheManagerKeyGeneration:
    """Tests for cache key generation."""

    def test_generate_key_creates_sha256_hash(self):
        """Should generate SHA256 hash of prompt."""
        cache_mgr = CacheManager(cache_dir=Path(".cache"), ttl=3600)
        key = cache_mgr.generate_key("test prompt")

        # SHA256 hashes are 64 characters
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_generate_key_is_deterministic(self):
        """Same prompt should always generate same key."""
        cache_mgr = CacheManager(cache_dir=Path(".cache"), ttl=3600)

        key1 = cache_mgr.generate_key("test prompt")
        key2 = cache_mgr.generate_key("test prompt")

        assert key1 == key2

    def test_generate_key_different_prompts_different_keys(self):
        """Different prompts should generate different keys."""
        cache_mgr = CacheManager(cache_dir=Path(".cache"), ttl=3600)

        key1 = cache_mgr.generate_key("prompt 1")
        key2 = cache_mgr.generate_key("prompt 2")

        assert key1 != key2

    def test_generate_key_handles_unicode(self):
        """Should handle unicode characters in prompts."""
        cache_mgr = CacheManager(cache_dir=Path(".cache"), ttl=3600)

        key = cache_mgr.generate_key("测试 🚀 prompt")

        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestCacheManagerDisabled:
    """Tests for cache disabled mode (TTL=0)."""

    def test_disabled_cache_returns_none_on_get(self, tmp_path):
        """When TTL=0, get should always return None."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=0)

        result = cache_mgr.get("any_key")

        assert result is None

    def test_disabled_cache_does_not_store(self, tmp_path):
        """When TTL=0, set should not create cache files."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=0)

        cache_mgr.set("test_key", {"result": "data"})

        # No cache files should be created
        cache_files = list(tmp_path.glob("*.yaml"))
        assert len(cache_files) == 0

    def test_disabled_cache_does_not_create_directory(self, tmp_path):
        """When TTL=0, should not create cache directory."""
        cache_dir = tmp_path / "nonexistent"
        cache_mgr = CacheManager(cache_dir=cache_dir, ttl=0)

        cache_mgr.set("test_key", {"result": "data"})

        # Directory should not be created
        assert not cache_dir.exists()


class TestCacheManagerBasicOperations:
    """Tests for basic cache operations."""

    def test_cache_directory_creation(self, tmp_path):
        """Should create cache directory if it doesn't exist."""
        cache_dir = tmp_path / "test_cache"

        CacheManager(cache_dir=cache_dir, ttl=3600)

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_get_returns_none_for_missing_key(self, tmp_path):
        """Should return None for non-existent cache key."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)

        result = cache_mgr.get("nonexistent_key")

        assert result is None

    def test_set_and_get_roundtrip(self, tmp_path):
        """Should successfully store and retrieve cached data."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        test_data = {"result": "test value", "confidence": 0.95}

        cache_mgr.set("test_key", test_data)
        result = cache_mgr.get("test_key")

        assert result == test_data

    def test_set_creates_cache_file(self, tmp_path):
        """Should create cache file with correct name."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)

        cache_mgr.set("test_key", {"result": "data"})

        cache_file = tmp_path / "test_key.yaml"
        assert cache_file.exists()

    def test_cache_file_contains_timestamp(self, tmp_path):
        """Cache file should contain timestamp and result."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)

        cache_mgr.set("test_key", {"result": "data"})

        cache_file = tmp_path / "test_key.yaml"
        with open(cache_file, "r") as f:
            cached_data = yaml.safe_load(f)

        assert "timestamp" in cached_data
        assert "result" in cached_data
        assert cached_data["result"] == {"result": "data"}


class TestCacheManagerTTL:
    """Tests for TTL-based expiration."""

    def test_fresh_cache_returns_data(self, tmp_path):
        """Cache within TTL should return data."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        test_data = {"result": "fresh data"}

        cache_mgr.set("test_key", test_data)
        result = cache_mgr.get("test_key")

        assert result == test_data

    def test_expired_cache_returns_none(self, tmp_path):
        """Cache beyond TTL should return None."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=1)

        cache_mgr.set("test_key", {"result": "old data"})

        # Wait for cache to expire
        time.sleep(1.1)

        result = cache_mgr.get("test_key")
        assert result is None

    def test_expired_cache_deletes_file(self, tmp_path):
        """Expired cache file should be deleted."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=1)

        cache_mgr.set("test_key", {"result": "old data"})
        cache_file = tmp_path / "test_key.yaml"

        # Confirm file exists
        assert cache_file.exists()

        # Wait for expiration
        time.sleep(1.1)

        # Access expired cache
        cache_mgr.get("test_key")

        # File should be deleted
        assert not cache_file.exists()

    def test_cache_timestamp_is_recent(self, tmp_path):
        """Cache timestamp should be close to current time."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        before = time.time()

        cache_mgr.set("test_key", {"result": "data"})

        after = time.time()

        cache_file = tmp_path / "test_key.yaml"
        with open(cache_file, "r") as f:
            cached_data = yaml.safe_load(f)

        timestamp = cached_data["timestamp"]
        assert before <= timestamp <= after


class TestCacheManagerCorruptedData:
    """Tests for handling corrupted cache files."""

    def test_corrupted_yaml_returns_none(self, tmp_path):
        """Corrupted YAML should return None."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        cache_file = tmp_path / "test_key.yaml"

        # Write corrupted YAML
        cache_file.write_text("invalid: yaml: content: [[[")

        result = cache_mgr.get("test_key")

        assert result is None

    def test_corrupted_yaml_deletes_file(self, tmp_path):
        """Corrupted YAML file should be deleted."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        cache_file = tmp_path / "test_key.yaml"

        cache_file.write_text("invalid: yaml: content: [[[")

        cache_mgr.get("test_key")

        assert not cache_file.exists()

    def test_missing_timestamp_returns_none(self, tmp_path):
        """Cache file without timestamp should return None."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        cache_file = tmp_path / "test_key.yaml"

        # Write cache without timestamp
        cache_file.write_text("result: data")

        result = cache_mgr.get("test_key")

        assert result is None

    def test_missing_result_returns_none(self, tmp_path):
        """Cache file without result should return None."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        cache_file = tmp_path / "test_key.yaml"

        # Write cache without result
        cache_file.write_text(f"timestamp: {time.time()}")

        result = cache_mgr.get("test_key")

        assert result is None


class TestCacheManagerThreadSafety:
    """Tests for thread-safe operations."""

    def test_concurrent_writes_do_not_conflict(self, tmp_path):
        """Multiple threads writing should not conflict."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)

        def write_cache(key, value):
            cache_mgr.set(key, value)

        threads = []
        for i in range(10):
            thread = Thread(target=write_cache, args=(f"key_{i}", {"value": i}))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All cache files should exist
        cache_files = list(tmp_path.glob("*.yaml"))
        assert len(cache_files) == 10

    def test_concurrent_reads_do_not_conflict(self, tmp_path):
        """Multiple threads reading should not conflict."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        cache_mgr.set("shared_key", {"result": "shared data"})

        results = []

        def read_cache():
            result = cache_mgr.get("shared_key")
            results.append(result)

        threads = []
        for i in range(10):
            thread = Thread(target=read_cache)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All reads should succeed
        assert len(results) == 10
        assert all(r == {"result": "shared data"} for r in results)

    def test_concurrent_read_write_thread_safe(self, tmp_path):
        """Concurrent reads and writes should be thread-safe."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        cache_mgr.set("shared_key", {"result": "initial"})

        def read_cache():
            cache_mgr.get("shared_key")

        def write_cache():
            cache_mgr.set("shared_key", {"result": "updated"})

        threads = []
        for i in range(5):
            threads.append(Thread(target=read_cache))
            threads.append(Thread(target=write_cache))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not crash or corrupt cache
        result = cache_mgr.get("shared_key")
        assert result is not None
        assert "result" in result


class TestCacheManagerEdgeCases:
    """Tests for edge cases."""

    def test_empty_dict_can_be_cached(self, tmp_path):
        """Should be able to cache empty dict."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)

        cache_mgr.set("test_key", {})
        result = cache_mgr.get("test_key")

        assert result == {}

    def test_nested_dict_can_be_cached(self, tmp_path):
        """Should be able to cache nested dict."""
        cache_mgr = CacheManager(cache_dir=tmp_path, ttl=3600)
        nested_data = {
            "outer": {
                "inner": {
                    "deep": "value"
                }
            }
        }

        cache_mgr.set("test_key", nested_data)
        result = cache_mgr.get("test_key")

        assert result == nested_data

    def test_cache_write_failure_does_not_crash(self, tmp_path):
        """Should handle cache write failures gracefully."""
        cache_dir = tmp_path / "readonly"
        cache_dir.mkdir()
        cache_dir.chmod(0o444)  # Read-only

        cache_mgr = CacheManager(cache_dir=cache_dir, ttl=3600)

        # Should not raise exception
        cache_mgr.set("test_key", {"result": "data"})

        # Restore permissions for cleanup
        cache_dir.chmod(0o755)

    def test_different_cache_instances_share_files(self, tmp_path):
        """Different instances using same dir should share cache."""
        cache_mgr1 = CacheManager(cache_dir=tmp_path, ttl=3600)
        cache_mgr2 = CacheManager(cache_dir=tmp_path, ttl=3600)

        cache_mgr1.set("test_key", {"result": "data"})
        result = cache_mgr2.get("test_key")

        assert result == {"result": "data"}
