"""Base class for LLM-based nodes with caching and rate limiting."""

from pathlib import Path
from typing import Optional

from pocketflow import Node

from ..cache import CacheManager
from ..config import WorkflowConfig
from ..llm import call_llm as _call_llm
from ..rate_limiter import RateLimiter


class LLMNode(Node):
    """Base class for LLM-based nodes with caching and throttling."""

    # Class-level default model - subclasses should override
    default_model: str = "anthropic/claude-sonnet-4-20250514"

    def __init__(
        self,
        config: WorkflowConfig,
        model: str | None = None,
        cache_ttl: int = 3600,
        rate_limit: int = None,
    ):
        """
        Initialize LLM node with caching and rate limiting.

        Args:
            config: Workflow configuration
            model: LLM model identifier (uses config-based default if not provided)
            cache_ttl: Cache time-to-live in seconds, 0 = disabled
            rate_limit: Requests per minute, None = unlimited
        """
        super().__init__(max_retries=config.max_retries)
        self.config = config

        # Model selection hierarchy: explicit param > config for node type > class default
        if model is not None:
            self.model = model
        else:
            node_type = self.__class__.__name__
            self.model = config.models.get_model_for_node_type(node_type)

        self.cache_ttl = cache_ttl  # seconds, 0 = disabled
        self.rate_limit = rate_limit  # requests per minute, None = unlimited

        # Initialize cache and rate limiter managers
        self._cache_manager = CacheManager(cache_dir=Path(".cache"), ttl=cache_ttl)
        self._rate_limiter = RateLimiter(rate_limit=rate_limit)

    def call_llm(
        self,
        prompt: str,
        system_prompt: str | None = None,
        yaml_response: bool = True,
        span_name: str | None = None,
    ) -> dict:
        """
        Call LLM with caching and throttling. Used by subclasses in exec().

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            yaml_response: Whether to parse response as YAML
            span_name: Optional name for the trace span (for observability)

        Returns:
            LLM response as dict (if yaml_response=True) or string
        """
        # Generate cache key from both prompts
        cache_input = f"{system_prompt or ''}\n{prompt}"
        cache_key = self._cache_manager.generate_key(cache_input)

        # Check cache first
        cached_result = self._cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Check rate limit (will wait if needed)
        self._rate_limiter.wait_if_needed()

        # Call LLM
        result = _call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.model,
            config=self.config,
            yaml_response=yaml_response,
            span_name=span_name,
        )

        # Store in cache
        if yaml_response and isinstance(result, dict):
            self._cache_manager.set(cache_key, result)

        return result
