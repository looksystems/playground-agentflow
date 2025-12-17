"""Tests for the @node_schema decorator."""

import pytest
from policyflow.nodes.decorators import node_schema
from policyflow.nodes.schema import NodeSchema, NodeParameter
from policyflow.nodes.llm_node import LLMNode
from policyflow.config import WorkflowConfig


class TestNodeSchemaDecorator:
    """Test the @node_schema decorator."""

    def test_basic_schema_generation(self):
        """Test that decorator generates basic schema from signature."""

        @node_schema(
            description="Test node for classification",
            category="llm",
            actions=["action1", "action2"],
        )
        class TestNode(LLMNode):
            def __init__(
                self,
                categories: list[str],
                config: WorkflowConfig,
                model: str | None = None,
            ):
                pass

        # Check that parser_schema was created
        assert hasattr(TestNode, "parser_schema")
        schema = TestNode.parser_schema
        assert isinstance(schema, NodeSchema)

        # Check basic attributes
        assert schema.name == "TestNode"
        assert schema.description == "Test node for classification"
        assert schema.category == "llm"
        assert schema.actions == ["action1", "action2"]
        assert schema.parser_exposed is True  # default

    def test_parameter_extraction_required(self):
        """Test that required parameters are correctly extracted."""

        @node_schema(
            description="Test node",
            category="llm",
        )
        class TestNode(LLMNode):
            def __init__(
                self,
                categories: list[str],
                threshold: int,
                config: WorkflowConfig,
            ):
                pass

        schema = TestNode.parser_schema

        # Should extract categories and threshold (not config)
        param_names = [p.name for p in schema.parameters]
        assert "categories" in param_names
        assert "threshold" in param_names
        assert "config" not in param_names  # config is reserved

        # Check they're marked as required
        categories_param = next(p for p in schema.parameters if p.name == "categories")
        assert categories_param.required is True
        assert categories_param.type == "list[str]"

    def test_parameter_extraction_optional(self):
        """Test that optional parameters are correctly extracted."""

        @node_schema(
            description="Test node",
            category="llm",
        )
        class TestNode(LLMNode):
            def __init__(
                self,
                categories: list[str],
                config: WorkflowConfig,
                model: str | None = None,
                descriptions: dict[str, str] | None = None,
                max_length: int = 1000,
                cache_ttl: int = 3600,
            ):
                pass

        schema = TestNode.parser_schema

        # Check optional parameters
        model_param = next(p for p in schema.parameters if p.name == "model")
        assert model_param.required is False
        assert model_param.default is None
        assert model_param.type == "str | None"

        descriptions_param = next(p for p in schema.parameters if p.name == "descriptions")
        assert descriptions_param.required is False
        assert descriptions_param.default is None
        assert descriptions_param.type == "dict[str, str] | None"

        max_length_param = next(p for p in schema.parameters if p.name == "max_length")
        assert max_length_param.required is False
        assert max_length_param.default == 1000
        assert max_length_param.type == "int"

    def test_reserved_parameters_excluded(self):
        """Test that reserved parameters are not included in schema."""

        @node_schema(
            description="Test node",
            category="llm",
        )
        class TestNode(LLMNode):
            def __init__(
                self,
                categories: list[str],
                config: WorkflowConfig,
                model: str | None = None,
                cache_ttl: int = 3600,
                rate_limit: int | None = None,
            ):
                pass

        schema = TestNode.parser_schema
        param_names = [p.name for p in schema.parameters]

        # Reserved parameters should be excluded
        assert "config" not in param_names
        assert "cache_ttl" not in param_names
        assert "rate_limit" not in param_names

        # Only non-reserved parameters should be included
        assert "categories" in param_names
        assert "model" in param_names

    def test_yaml_example_included(self):
        """Test that yaml_example is included in schema."""

        yaml_example = """- type: TestNode
  id: test_1
  params:
    categories:
      - cat1
      - cat2"""

        @node_schema(
            description="Test node",
            category="llm",
            yaml_example=yaml_example,
        )
        class TestNode(LLMNode):
            def __init__(self, categories: list[str], config: WorkflowConfig):
                pass

        schema = TestNode.parser_schema
        assert schema.yaml_example == yaml_example

    def test_parser_exposed_false(self):
        """Test that parser_exposed can be set to False."""

        @node_schema(
            description="Internal node",
            category="internal",
            parser_exposed=False,
        )
        class InternalNode(LLMNode):
            def __init__(self, config: WorkflowConfig):
                pass

        schema = InternalNode.parser_schema
        assert schema.parser_exposed is False

    def test_parameter_descriptions(self):
        """Test that parameter descriptions can be provided."""

        @node_schema(
            description="Test node",
            category="llm",
            parameter_descriptions={
                "categories": "List of category names to classify into",
                "threshold": "Minimum confidence threshold for classification",
            },
        )
        class TestNode(LLMNode):
            def __init__(
                self,
                categories: list[str],
                threshold: float,
                config: WorkflowConfig,
            ):
                pass

        schema = TestNode.parser_schema

        categories_param = next(p for p in schema.parameters if p.name == "categories")
        assert categories_param.description == "List of category names to classify into"

        threshold_param = next(p for p in schema.parameters if p.name == "threshold")
        assert threshold_param.description == "Minimum confidence threshold for classification"

    def test_default_parameter_descriptions(self):
        """Test that default descriptions are generated for parameters without custom descriptions."""

        @node_schema(
            description="Test node",
            category="llm",
        )
        class TestNode(LLMNode):
            def __init__(
                self,
                categories: list[str],
                config: WorkflowConfig,
            ):
                pass

        schema = TestNode.parser_schema

        categories_param = next(p for p in schema.parameters if p.name == "categories")
        # Should have some default description
        assert categories_param.description != ""
        assert "categories" in categories_param.description.lower()

    def test_self_parameter_excluded(self):
        """Test that 'self' parameter is not included in schema."""

        @node_schema(
            description="Test node",
            category="llm",
        )
        class TestNode(LLMNode):
            def __init__(self, categories: list[str], config: WorkflowConfig):
                pass

        schema = TestNode.parser_schema
        param_names = [p.name for p in schema.parameters]
        assert "self" not in param_names

    def test_no_type_annotation_fallback(self):
        """Test that parameters without type annotations default to 'Any'."""

        @node_schema(
            description="Test node",
            category="llm",
        )
        class TestNode(LLMNode):
            def __init__(self, categories, config: WorkflowConfig):
                pass

        schema = TestNode.parser_schema

        categories_param = next(p for p in schema.parameters if p.name == "categories")
        assert categories_param.type == "Any"

    def test_multiple_nodes_independent_schemas(self):
        """Test that multiple decorated nodes have independent schemas."""

        @node_schema(
            description="Node A",
            category="llm",
            actions=["a1", "a2"],
        )
        class NodeA(LLMNode):
            def __init__(self, param_a: str, config: WorkflowConfig):
                pass

        @node_schema(
            description="Node B",
            category="deterministic",
            actions=["b1"],
        )
        class NodeB(LLMNode):
            def __init__(self, param_b: int, config: WorkflowConfig):
                pass

        # Check that schemas are independent
        assert NodeA.parser_schema.name == "NodeA"
        assert NodeA.parser_schema.description == "Node A"
        assert NodeA.parser_schema.actions == ["a1", "a2"]

        assert NodeB.parser_schema.name == "NodeB"
        assert NodeB.parser_schema.description == "Node B"
        assert NodeB.parser_schema.actions == ["b1"]

        # Check parameters are different
        a_params = [p.name for p in NodeA.parser_schema.parameters]
        b_params = [p.name for p in NodeB.parser_schema.parameters]
        assert "param_a" in a_params
        assert "param_a" not in b_params
        assert "param_b" in b_params
        assert "param_b" not in a_params
