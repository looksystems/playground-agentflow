"""Cache manager for LLM responses."""

import hashlib
import time
from pathlib import Path
from threading import Lock
from typing import Optional

import yaml


class CacheManager:
    """Manages file-based caching with TTL expiration."""

    def __init__(self, cache_dir: Path, ttl: int):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live in seconds, 0 = disabled
        """
        self._cache_dir = cache_dir
        self._ttl = ttl
        self._lock = Lock()

        # Create cache directory if caching is enabled
        if self._ttl > 0:
            self._cache_dir.mkdir(exist_ok=True)

    def generate_key(self, prompt: str) -> str:
        """
        Generate cache key from prompt hash.

        Args:
            prompt: The prompt string to hash

        Returns:
            SHA256 hash of the prompt
        """
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[dict]:
        """
        Return cached result or None.

        Args:
            key: Cache key from generate_key()

        Returns:
            Cached result dict or None if not found/expired
        """
        if self._ttl == 0:
            return None

        cache_file = self._cache_dir / f"{key}.yaml"

        with self._lock:
            if not cache_file.exists():
                return None

            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = yaml.safe_load(f)

                # Check TTL
                if cached_data and "timestamp" in cached_data:
                    age = time.time() - cached_data["timestamp"]
                    if age < self._ttl:
                        return cached_data.get("result")

                # Cache expired, remove file
                cache_file.unlink(missing_ok=True)
            except (yaml.YAMLError, OSError, KeyError):
                # Corrupted cache, remove it
                cache_file.unlink(missing_ok=True)

        return None

    def set(self, key: str, value: dict) -> None:
        """
        Store result in cache.

        Args:
            key: Cache key from generate_key()
            value: Result dictionary to cache
        """
        if self._ttl == 0:
            return

        cache_file = self._cache_dir / f"{key}.yaml"
        cache_data = {"timestamp": time.time(), "result": value}

        with self._lock:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    yaml.safe_dump(cache_data, f, default_flow_style=False)
            except OSError:
                # Fail silently if cache write fails
                pass
