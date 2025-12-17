"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from policyflow.config import (
    WorkflowConfig,
    ModelConfig,
    CacheConfig,
    ThrottleConfig,
    PhoenixConfig,
    ConfidenceGateConfig,
    export_config_schema,
)


class TestModelConfig:
    """Tests for ModelConfig class."""

    def test_default_model_from_env(self):
        """Default model should come from POLICY_EVAL_MODEL env var."""
        with patch.dict(os.environ, {"POLICY_EVAL_MODEL": "anthropic/claude-opus-4"}):
            config = ModelConfig()
            assert config.default_model == "anthropic/claude-opus-4"

    def test_default_model_hardcoded_fallback(self):
        """Default model should fallback to hardcoded value if env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ModelConfig()
            assert config.default_model == "anthropic/claude-sonnet-4-20250514"

    def test_node_type_models_from_env(self):
        """Node type models should be loaded from env vars."""
        with patch.dict(
            os.environ,
            {
                "CLASSIFIER_MODEL": "anthropic/claude-haiku-3-5",
                "DATA_EXTRACTOR_MODEL": "anthropic/claude-opus-4",
                "SENTIMENT_MODEL": "anthropic/claude-haiku-3-5",
                "SAMPLER_MODEL": "anthropic/claude-sonnet-4",
            },
        ):
            config = ModelConfig()
            assert config.classifier_model == "anthropic/claude-haiku-3-5"
            assert config.data_extractor_model == "anthropic/claude-opus-4"
            assert config.sentiment_model == "anthropic/claude-haiku-3-5"
            assert config.sampler_model == "anthropic/claude-sonnet-4"

    def test_node_type_models_optional(self):
        """Node type models should be None if env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ModelConfig()
            assert config.classifier_model is None
            assert config.data_extractor_model is None
            assert config.sentiment_model is None
            assert config.sampler_model is None

    def test_cli_task_models_from_env(self):
        """CLI task models should be loaded from env vars."""
        with patch.dict(
            os.environ,
            {
                "GENERATE_MODEL": "anthropic/claude-opus-4",
                "ANALYZE_MODEL": "anthropic/claude-sonnet-4",
                "HYPOTHESIZE_MODEL": "anthropic/claude-opus-4",
                "OPTIMIZE_MODEL": "anthropic/claude-sonnet-4",
            },
        ):
            config = ModelConfig()
            assert config.generate_model == "anthropic/claude-opus-4"
            assert config.analyze_model == "anthropic/claude-sonnet-4"
            assert config.hypothesize_model == "anthropic/claude-opus-4"
            assert config.optimize_model == "anthropic/claude-sonnet-4"

    def test_cli_task_models_optional(self):
        """CLI task models should be None if env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ModelConfig()
            assert config.generate_model is None
            assert config.analyze_model is None
            assert config.hypothesize_model is None
            assert config.optimize_model is None

    def test_get_model_for_node_type_with_specific_config(self):
        """get_model_for_node_type should return type-specific model if configured."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
                "CLASSIFIER_MODEL": "anthropic/claude-haiku-3-5",
            },
        ):
            config = ModelConfig()
            assert (
                config.get_model_for_node_type("ClassifierNode")
                == "anthropic/claude-haiku-3-5"
            )

    def test_get_model_for_node_type_fallback_to_default(self):
        """get_model_for_node_type should fallback to default if type not configured."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
            },
            clear=True,
        ):
            config = ModelConfig()
            # No CLASSIFIER_MODEL set, should use default
            assert (
                config.get_model_for_node_type("ClassifierNode")
                == "anthropic/claude-sonnet-4"
            )

    def test_get_model_for_node_type_unknown_type(self):
        """get_model_for_node_type should return default for unknown node types."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
            },
            clear=True,
        ):
            config = ModelConfig()
            assert (
                config.get_model_for_node_type("UnknownNode")
                == "anthropic/claude-sonnet-4"
            )

    def test_get_model_for_node_type_all_types(self):
        """get_model_for_node_type should support all documented node types."""
        with patch.dict(
            os.environ,
            {
                "CLASSIFIER_MODEL": "model-1",
                "DATA_EXTRACTOR_MODEL": "model-2",
                "SENTIMENT_MODEL": "model-3",
                "SAMPLER_MODEL": "model-4",
            },
        ):
            config = ModelConfig()
            assert config.get_model_for_node_type("ClassifierNode") == "model-1"
            assert config.get_model_for_node_type("DataExtractorNode") == "model-2"
            assert config.get_model_for_node_type("SentimentNode") == "model-3"
            assert config.get_model_for_node_type("SamplerNode") == "model-4"

    def test_get_model_for_task_with_specific_config(self):
        """get_model_for_task should return task-specific model if configured."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
                "GENERATE_MODEL": "anthropic/claude-opus-4",
            },
        ):
            config = ModelConfig()
            assert (
                config.get_model_for_task("generate") == "anthropic/claude-opus-4"
            )

    def test_get_model_for_task_fallback_to_default(self):
        """get_model_for_task should fallback to default if task not configured."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
            },
            clear=True,
        ):
            config = ModelConfig()
            # No GENERATE_MODEL set, should use default
            assert config.get_model_for_task("generate") == "anthropic/claude-sonnet-4"

    def test_get_model_for_task_unknown_task(self):
        """get_model_for_task should return default for unknown tasks."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
            },
            clear=True,
        ):
            config = ModelConfig()
            assert (
                config.get_model_for_task("unknown_task")
                == "anthropic/claude-sonnet-4"
            )

    def test_get_model_for_task_all_tasks(self):
        """get_model_for_task should support all documented CLI tasks."""
        with patch.dict(
            os.environ,
            {
                "GENERATE_MODEL": "model-1",
                "ANALYZE_MODEL": "model-2",
                "HYPOTHESIZE_MODEL": "model-3",
                "OPTIMIZE_MODEL": "model-4",
            },
        ):
            config = ModelConfig()
            assert config.get_model_for_task("generate") == "model-1"
            assert config.get_model_for_task("analyze") == "model-2"
            assert config.get_model_for_task("hypothesize") == "model-3"
            assert config.get_model_for_task("optimize") == "model-4"


class TestWorkflowConfigWithModels:
    """Tests for WorkflowConfig integration with ModelConfig."""

    def test_workflow_config_includes_model_config(self):
        """WorkflowConfig should include a models field."""
        config = WorkflowConfig()
        assert hasattr(config, "models")
        assert isinstance(config.models, ModelConfig)

    def test_workflow_config_models_uses_env_vars(self):
        """WorkflowConfig.models should respect environment variables."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-opus-4",
                "CLASSIFIER_MODEL": "anthropic/claude-haiku-3-5",
            },
        ):
            config = WorkflowConfig()
            assert config.models.default_model == "anthropic/claude-opus-4"
            assert config.models.classifier_model == "anthropic/claude-haiku-3-5"


class TestModelConfigPriority:
    """Tests for model selection priority hierarchy."""

    def test_priority_node_specific_over_default(self):
        """Node-specific env var should override global default."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
                "CLASSIFIER_MODEL": "anthropic/claude-haiku-3-5",
            },
        ):
            config = ModelConfig()
            # Classifier should use specific config
            assert (
                config.get_model_for_node_type("ClassifierNode")
                == "anthropic/claude-haiku-3-5"
            )
            # Other node types should use default
            assert (
                config.get_model_for_node_type("SentimentNode")
                == "anthropic/claude-sonnet-4"
            )

    def test_priority_task_specific_over_default(self):
        """Task-specific env var should override global default."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
                "GENERATE_MODEL": "anthropic/claude-opus-4",
            },
        ):
            config = ModelConfig()
            # Generate should use specific config
            assert config.get_model_for_task("generate") == "anthropic/claude-opus-4"
            # Other tasks should use default
            assert config.get_model_for_task("analyze") == "anthropic/claude-sonnet-4"

    def test_mixed_configuration(self):
        """Should handle mixed configuration of node types and tasks."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_MODEL": "anthropic/claude-sonnet-4",
                "CLASSIFIER_MODEL": "anthropic/claude-haiku-3-5",
                "GENERATE_MODEL": "anthropic/claude-opus-4",
                "DATA_EXTRACTOR_MODEL": "anthropic/claude-opus-4",
            },
        ):
            config = ModelConfig()

            # Check node types
            assert (
                config.get_model_for_node_type("ClassifierNode")
                == "anthropic/claude-haiku-3-5"
            )
            assert (
                config.get_model_for_node_type("DataExtractorNode")
                == "anthropic/claude-opus-4"
            )
            assert (
                config.get_model_for_node_type("SentimentNode")
                == "anthropic/claude-sonnet-4"
            )

            # Check tasks
            assert config.get_model_for_task("generate") == "anthropic/claude-opus-4"
            assert config.get_model_for_task("analyze") == "anthropic/claude-sonnet-4"


class TestCacheConfigWithSettings:
    """Tests for CacheConfig using pydantic-settings."""

    def test_cache_enabled_from_env(self):
        """Cache enabled should load from POLICY_EVAL_CACHE_ENABLED."""
        with patch.dict(os.environ, {"POLICY_EVAL_CACHE_ENABLED": "true"}):
            config = CacheConfig()
            assert config.enabled is True

        with patch.dict(os.environ, {"POLICY_EVAL_CACHE_ENABLED": "false"}):
            config = CacheConfig()
            assert config.enabled is False

    def test_cache_ttl_from_env(self):
        """Cache TTL should load from POLICY_EVAL_CACHE_TTL."""
        with patch.dict(os.environ, {"POLICY_EVAL_CACHE_TTL": "7200"}):
            config = CacheConfig()
            assert config.ttl == 7200

    def test_cache_directory_from_env(self):
        """Cache directory should load from POLICY_EVAL_CACHE_DIR."""
        with patch.dict(os.environ, {"POLICY_EVAL_CACHE_DIR": "/tmp/cache"}):
            config = CacheConfig()
            assert config.directory == "/tmp/cache"

    def test_cache_defaults(self):
        """Cache config should use defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = CacheConfig()
            assert config.enabled is True
            assert config.ttl == 3600
            assert config.directory == ".cache"

    def test_cache_ttl_validation(self):
        """Cache TTL should validate non-negative."""
        with patch.dict(os.environ, {"POLICY_EVAL_CACHE_TTL": "-1"}):
            with pytest.raises(ValidationError):
                CacheConfig()


class TestThrottleConfigWithSettings:
    """Tests for ThrottleConfig using pydantic-settings."""

    def test_throttle_enabled_from_env(self):
        """Throttle enabled should load from POLICY_EVAL_THROTTLE_ENABLED."""
        with patch.dict(os.environ, {"POLICY_EVAL_THROTTLE_ENABLED": "true"}):
            config = ThrottleConfig()
            assert config.enabled is True

        with patch.dict(os.environ, {"POLICY_EVAL_THROTTLE_ENABLED": "false"}):
            config = ThrottleConfig()
            assert config.enabled is False

    def test_throttle_rpm_from_env(self):
        """Throttle RPM should load from POLICY_EVAL_THROTTLE_RPM."""
        with patch.dict(os.environ, {"POLICY_EVAL_THROTTLE_RPM": "120"}):
            config = ThrottleConfig()
            assert config.requests_per_minute == 120

    def test_throttle_defaults(self):
        """Throttle config should use defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ThrottleConfig()
            assert config.enabled is False
            assert config.requests_per_minute == 60

    def test_throttle_rpm_validation(self):
        """Throttle RPM should validate >= 1."""
        with patch.dict(os.environ, {"POLICY_EVAL_THROTTLE_RPM": "0"}):
            with pytest.raises(ValidationError):
                ThrottleConfig()


class TestPhoenixConfigWithSettings:
    """Tests for PhoenixConfig using pydantic-settings."""

    def test_phoenix_enabled_from_env(self):
        """Phoenix enabled should load from PHOENIX_ENABLED."""
        with patch.dict(os.environ, {"PHOENIX_ENABLED": "true"}):
            config = PhoenixConfig()
            assert config.enabled is True

        with patch.dict(os.environ, {"PHOENIX_ENABLED": "false"}):
            config = PhoenixConfig()
            assert config.enabled is False

    def test_phoenix_endpoint_from_env(self):
        """Phoenix endpoint should load from PHOENIX_COLLECTOR_ENDPOINT."""
        with patch.dict(
            os.environ, {"PHOENIX_COLLECTOR_ENDPOINT": "http://phoenix:6007"}
        ):
            config = PhoenixConfig()
            assert config.endpoint == "http://phoenix:6007"

    def test_phoenix_project_name_from_env(self):
        """Phoenix project name should load from PHOENIX_PROJECT_NAME."""
        with patch.dict(os.environ, {"PHOENIX_PROJECT_NAME": "test-project"}):
            config = PhoenixConfig()
            assert config.project_name == "test-project"

    def test_phoenix_defaults(self):
        """Phoenix config should use defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = PhoenixConfig()
            assert config.enabled is False
            assert config.endpoint == "http://localhost:6007"
            assert config.project_name == "policyflow"


class TestConfidenceGateValidation:
    """Tests for ConfidenceGateConfig cross-field validation."""

    def test_valid_thresholds(self):
        """Valid thresholds should pass validation."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_CONFIDENCE_HIGH": "0.8",
                "POLICY_EVAL_CONFIDENCE_LOW": "0.5",
            },
        ):
            config = ConfidenceGateConfig()
            assert config.high_threshold == 0.8
            assert config.low_threshold == 0.5

    def test_equal_thresholds(self):
        """Equal thresholds should pass validation."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_CONFIDENCE_HIGH": "0.7",
                "POLICY_EVAL_CONFIDENCE_LOW": "0.7",
            },
        ):
            config = ConfidenceGateConfig()
            assert config.high_threshold == 0.7
            assert config.low_threshold == 0.7

    def test_invalid_threshold_order(self):
        """High threshold below low threshold should fail validation."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_CONFIDENCE_HIGH": "0.4",
                "POLICY_EVAL_CONFIDENCE_LOW": "0.6",
            },
        ):
            with pytest.raises(ValidationError) as exc_info:
                ConfidenceGateConfig()
            assert "high_threshold must be >= low_threshold" in str(exc_info.value)

    def test_threshold_bounds(self):
        """Thresholds should validate 0.0 <= x <= 1.0."""
        with patch.dict(os.environ, {"POLICY_EVAL_CONFIDENCE_HIGH": "1.5"}):
            with pytest.raises(ValidationError):
                ConfidenceGateConfig()

        with patch.dict(os.environ, {"POLICY_EVAL_CONFIDENCE_LOW": "-0.1"}):
            with pytest.raises(ValidationError):
                ConfidenceGateConfig()

    def test_defaults_are_valid(self):
        """Default thresholds should pass validation."""
        with patch.dict(os.environ, {}, clear=True):
            config = ConfidenceGateConfig()
            assert config.high_threshold >= config.low_threshold


class TestWorkflowConfigSettings:
    """Tests for WorkflowConfig using pydantic-settings."""

    def test_workflow_temperature_from_env(self):
        """Workflow temperature should load from POLICY_EVAL_TEMPERATURE."""
        with patch.dict(os.environ, {"POLICY_EVAL_TEMPERATURE": "0.5"}):
            config = WorkflowConfig()
            assert config.temperature == 0.5

    def test_workflow_max_retries_from_env(self):
        """Workflow max retries should load from POLICY_EVAL_MAX_RETRIES."""
        with patch.dict(os.environ, {"POLICY_EVAL_MAX_RETRIES": "5"}):
            config = WorkflowConfig()
            assert config.max_retries == 5

    def test_workflow_retry_wait_from_env(self):
        """Workflow retry wait should load from POLICY_EVAL_RETRY_WAIT."""
        with patch.dict(os.environ, {"POLICY_EVAL_RETRY_WAIT": "3"}):
            config = WorkflowConfig()
            assert config.retry_wait == 3

    def test_workflow_nested_configs(self):
        """WorkflowConfig should properly load all nested configs."""
        with patch.dict(
            os.environ,
            {
                "POLICY_EVAL_CACHE_ENABLED": "false",
                "POLICY_EVAL_THROTTLE_ENABLED": "true",
                "PHOENIX_ENABLED": "true",
                "POLICY_EVAL_CONFIDENCE_HIGH": "0.9",
            },
        ):
            config = WorkflowConfig()
            assert config.cache.enabled is False
            assert config.throttle.enabled is True
            assert config.phoenix.enabled is True
            assert config.confidence_gate.high_threshold == 0.9


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing env vars."""

    def test_all_original_env_vars_still_work(self):
        """All env vars from .env.example should still work."""
        env_vars = {
            # Model config
            "POLICY_EVAL_MODEL": "anthropic/claude-opus-4",
            "CLASSIFIER_MODEL": "anthropic/claude-haiku-3-5",
            "DATA_EXTRACTOR_MODEL": "anthropic/claude-sonnet-4",
            "SENTIMENT_MODEL": "anthropic/claude-haiku-3-5",
            "SAMPLER_MODEL": "anthropic/claude-sonnet-4",
            "GENERATE_MODEL": "anthropic/claude-opus-4",
            "ANALYZE_MODEL": "anthropic/claude-sonnet-4",
            "HYPOTHESIZE_MODEL": "anthropic/claude-opus-4",
            "OPTIMIZE_MODEL": "anthropic/claude-sonnet-4",
            # Workflow config
            "POLICY_EVAL_TEMPERATURE": "0.5",
            "POLICY_EVAL_MAX_RETRIES": "5",
            "POLICY_EVAL_RETRY_WAIT": "3",
            # Confidence thresholds
            "POLICY_EVAL_CONFIDENCE_HIGH": "0.85",
            "POLICY_EVAL_CONFIDENCE_LOW": "0.45",
            # Cache config
            "POLICY_EVAL_CACHE_ENABLED": "false",
            "POLICY_EVAL_CACHE_TTL": "7200",
            "POLICY_EVAL_CACHE_DIR": "/tmp/test-cache",
            # Throttle config
            "POLICY_EVAL_THROTTLE_ENABLED": "true",
            "POLICY_EVAL_THROTTLE_RPM": "120",
            # Phoenix config
            "PHOENIX_ENABLED": "true",
            "PHOENIX_COLLECTOR_ENDPOINT": "http://phoenix:6007",
            "PHOENIX_PROJECT_NAME": "test-policyflow",
        }

        with patch.dict(os.environ, env_vars):
            config = WorkflowConfig()

            # Check all values are loaded correctly
            assert config.models.default_model == "anthropic/claude-opus-4"
            assert config.models.classifier_model == "anthropic/claude-haiku-3-5"
            assert config.models.data_extractor_model == "anthropic/claude-sonnet-4"
            assert config.models.sentiment_model == "anthropic/claude-haiku-3-5"
            assert config.models.sampler_model == "anthropic/claude-sonnet-4"
            assert config.models.generate_model == "anthropic/claude-opus-4"
            assert config.models.analyze_model == "anthropic/claude-sonnet-4"
            assert config.models.hypothesize_model == "anthropic/claude-opus-4"
            assert config.models.optimize_model == "anthropic/claude-sonnet-4"

            assert config.temperature == 0.5
            assert config.max_retries == 5
            assert config.retry_wait == 3

            assert config.confidence_gate.high_threshold == 0.85
            assert config.confidence_gate.low_threshold == 0.45

            assert config.cache.enabled is False
            assert config.cache.ttl == 7200
            assert config.cache.directory == "/tmp/test-cache"

            assert config.throttle.enabled is True
            assert config.throttle.requests_per_minute == 120

            assert config.phoenix.enabled is True
            assert config.phoenix.endpoint == "http://phoenix:6007"
            assert config.phoenix.project_name == "test-policyflow"


class TestConfigSchemaExport:
    """Tests for config schema export functionality."""

    def test_export_config_schema_returns_dict(self):
        """export_config_schema should return a dictionary."""
        schema = export_config_schema()
        assert isinstance(schema, dict)

    def test_schema_includes_all_config_classes(self):
        """Schema should include all config classes."""
        schema = export_config_schema()
        # Check that we have definitions for all our config classes
        assert "WorkflowConfig" in str(schema)
        assert "ModelConfig" in str(schema)
        assert "CacheConfig" in str(schema)
        assert "ThrottleConfig" in str(schema)
        assert "PhoenixConfig" in str(schema)
        assert "ConfidenceGateConfig" in str(schema)

    def test_schema_includes_descriptions(self):
        """Schema should include field descriptions."""
        schema = export_config_schema()
        # Schema should contain description text
        schema_str = str(schema)
        assert "description" in schema_str.lower()

    def test_schema_is_json_serializable(self):
        """Schema should be JSON serializable."""
        import json

        schema = export_config_schema()
        # Should not raise
        json_str = json.dumps(schema)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
