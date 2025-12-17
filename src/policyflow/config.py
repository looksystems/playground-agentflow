"""Configuration management using pydantic-settings."""

from dotenv import find_dotenv, load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Load environment variables from .env file
_env_file = find_dotenv()
if _env_file:
    load_dotenv(_env_file)


class CacheConfig(BaseSettings):
    """Configuration for LLM response caching."""

    model_config = SettingsConfigDict(env_prefix="POLICY_EVAL_CACHE_", extra="allow")

    enabled: bool = Field(
        default=True,
        description="Whether caching is enabled",
    )
    ttl: int = Field(
        default=3600,
        ge=0,
        description="Cache TTL in seconds (0 = no expiration)",
    )
    dir: str = Field(
        default=".cache",
        description="Directory for cache files",
    )

    @property
    def directory(self) -> str:
        """Alias for dir to maintain backward compatibility."""
        return self.dir


class ThrottleConfig(BaseSettings):
    """Configuration for LLM rate limiting."""

    model_config = SettingsConfigDict(env_prefix="POLICY_EVAL_THROTTLE_", extra="allow")

    enabled: bool = Field(
        default=False,
        description="Whether rate limiting is enabled",
    )
    rpm: int = Field(
        default=60,
        ge=1,
        description="Maximum requests per minute",
    )

    @property
    def requests_per_minute(self) -> int:
        """Alias for rpm to maintain backward compatibility."""
        return self.rpm


class ConfidenceGateConfig(BaseSettings):
    """Configuration for confidence-based routing."""

    model_config = SettingsConfigDict(env_prefix="POLICY_EVAL_CONFIDENCE_", extra="allow")

    high: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence above this is high confidence",
    )
    low: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence below this needs review",
    )

    @property
    def high_threshold(self) -> float:
        """Alias for high to maintain backward compatibility."""
        return self.high

    @property
    def low_threshold(self) -> float:
        """Alias for low to maintain backward compatibility."""
        return self.low

    @model_validator(mode="after")
    def validate_threshold_order(self):
        """Ensure high_threshold >= low_threshold."""
        if self.high < self.low:
            raise ValueError("high_threshold must be >= low_threshold")
        return self


class PhoenixConfig(BaseSettings):
    """Configuration for Arize Phoenix observability/tracing."""

    model_config = SettingsConfigDict(env_prefix="PHOENIX_", extra="allow")

    enabled: bool = Field(
        default=False,
        description="Enable Phoenix tracing (requires Phoenix server)",
    )
    collector_endpoint: str = Field(
        default="http://localhost:6007",
        description="Phoenix collector base URL (OTLP endpoint)",
    )
    project_name: str = Field(
        default="policyflow",
        description="Project name in Phoenix UI",
    )

    @property
    def endpoint(self) -> str:
        """Alias for collector_endpoint to maintain backward compatibility."""
        return self.collector_endpoint


class ModelConfig(BaseSettings):
    """Configuration for model selection at different levels."""

    model_config = SettingsConfigDict(env_prefix="", populate_by_name=True, extra="allow")

    # Global default
    policy_eval_model: str = Field(
        default="anthropic/claude-sonnet-4-20250514",
        description="Global default model for all operations",
    )

    @property
    def default_model(self) -> str:
        """Alias for policy_eval_model to maintain backward compatibility."""
        return self.policy_eval_model

    # Node type defaults
    classifier_model: str | None = Field(
        default=None,
        description="Default model for ClassifierNode",
    )
    data_extractor_model: str | None = Field(
        default=None,
        description="Default model for DataExtractorNode",
    )
    sentiment_model: str | None = Field(
        default=None,
        description="Default model for SentimentNode",
    )
    sampler_model: str | None = Field(
        default=None,
        description="Default model for SamplerNode",
    )

    # CLI task defaults
    generate_model: str | None = Field(
        default=None,
        description="Default model for generate-dataset command",
    )
    analyze_model: str | None = Field(
        default=None,
        description="Default model for analyze command",
    )
    hypothesize_model: str | None = Field(
        default=None,
        description="Default model for hypothesize command",
    )
    optimize_model: str | None = Field(
        default=None,
        description="Default model for optimize command",
    )

    def get_model_for_node_type(self, node_type: str) -> str:
        """Get model for a specific node type with fallback to default."""
        mapping = {
            "ClassifierNode": self.classifier_model,
            "DataExtractorNode": self.data_extractor_model,
            "SentimentNode": self.sentiment_model,
            "SamplerNode": self.sampler_model,
        }
        return mapping.get(node_type) or self.policy_eval_model

    def get_model_for_task(self, task: str) -> str:
        """Get model for a specific CLI task with fallback to default."""
        mapping = {
            "generate": self.generate_model,
            "analyze": self.analyze_model,
            "hypothesize": self.hypothesize_model,
            "optimize": self.optimize_model,
        }
        return mapping.get(task) or self.policy_eval_model


class WorkflowConfig(BaseSettings):
    """Configuration for the evaluation workflow."""

    model_config = SettingsConfigDict(env_prefix="POLICY_EVAL_", extra="allow")

    temperature: float = Field(
        default=0.0,
        description="LLM temperature",
    )
    max_retries: int = Field(
        default=3,
        description="Max retries per node",
    )
    retry_wait: int = Field(
        default=2,
        description="Seconds between retries",
    )
    confidence_gate: ConfidenceGateConfig = Field(
        default_factory=ConfidenceGateConfig,
        description="Confidence gate configuration",
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="LLM response cache configuration",
    )
    throttle: ThrottleConfig = Field(
        default_factory=ThrottleConfig,
        description="LLM rate limiting configuration",
    )
    phoenix: PhoenixConfig = Field(
        default_factory=PhoenixConfig,
        description="Phoenix observability configuration",
    )
    models: ModelConfig = Field(
        default_factory=ModelConfig,
        description="Model selection configuration",
    )


def get_config() -> WorkflowConfig:
    """Get the current workflow configuration."""
    return WorkflowConfig()


def export_config_schema() -> dict:
    """Export JSON schema for all config classes for documentation."""
    return WorkflowConfig.model_json_schema()
