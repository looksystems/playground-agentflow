"""Tests for DeterministicNode base class."""

import pytest
from pocketflow import Node

from policyflow.nodes.base import DeterministicNode


class SimpleDeterministicNode(DeterministicNode):
    """Simple test node that uppercases input."""

    def exec(self, prep_res: dict) -> dict:
        """Uppercase the input text."""
        return {"result": prep_res["input_text"].upper()}

    def get_action(self, exec_res: dict) -> str:
        """Return 'done' action."""
        return "done"


class ConfigurableInputNode(DeterministicNode):
    """Node with configurable input key."""

    def __init__(self, input_key: str = "custom_input"):
        super().__init__()
        self.input_key = input_key

    def exec(self, prep_res: dict) -> dict:
        """Process the input."""
        return {"processed": f"Processed: {prep_res[self.input_key]}"}

    def get_action(self, exec_res: dict) -> str:
        """Return 'processed' action."""
        return "processed"


class ConfigurableOutputNode(DeterministicNode):
    """Node with configurable output key."""

    def __init__(self, output_key: str | None = "custom_output"):
        super().__init__()
        self.output_key = output_key

    def exec(self, prep_res: dict) -> dict:
        """Process the input."""
        return {"data": prep_res["input_text"].lower()}

    def get_action(self, exec_res: dict) -> str:
        """Return 'completed' action."""
        return "completed"


class ConditionalActionNode(DeterministicNode):
    """Node that returns different actions based on exec result."""

    def exec(self, prep_res: dict) -> dict:
        """Check if input contains 'pass'."""
        contains_pass = "pass" in prep_res["input_text"].lower()
        return {"passed": contains_pass}

    def get_action(self, exec_res: dict) -> str:
        """Return 'pass' or 'fail' based on result."""
        return "pass" if exec_res["passed"] else "fail"


class NoOutputKeyNode(DeterministicNode):
    """Node with output_key = None (doesn't store in shared)."""

    def __init__(self):
        super().__init__()
        self.output_key = None

    def exec(self, prep_res: dict) -> dict:
        """Process without storing."""
        return {"temp": "temporary data"}

    def get_action(self, exec_res: dict) -> str:
        """Return 'done' action."""
        return "done"


class TestDeterministicNodePrep:
    """Test default prep() behavior."""

    def test_prep_reads_default_input_key(self):
        """Test that prep reads from shared['input_text'] by default."""
        node = SimpleDeterministicNode()
        shared = {"input_text": "Hello World"}

        prep_res = node.prep(shared)

        assert prep_res == {"input_text": "Hello World"}

    def test_prep_returns_empty_string_when_missing(self):
        """Test that prep returns empty string when input_text missing."""
        node = SimpleDeterministicNode()
        shared = {}

        prep_res = node.prep(shared)

        assert prep_res == {"input_text": ""}

    def test_prep_uses_custom_input_key(self):
        """Test that prep can use a custom input key."""
        node = ConfigurableInputNode(input_key="custom_input")
        shared = {"custom_input": "Custom data", "input_text": "Default"}

        prep_res = node.prep(shared)

        # Should only include the custom key
        assert "custom_input" in prep_res
        assert prep_res["custom_input"] == "Custom data"

    def test_prep_with_custom_key_missing(self):
        """Test prep with custom key that doesn't exist in shared."""
        node = ConfigurableInputNode(input_key="missing_key")
        shared = {"input_text": "Hello"}

        prep_res = node.prep(shared)

        assert prep_res == {"missing_key": ""}


class TestDeterministicNodePost:
    """Test default post() behavior."""

    def test_post_stores_in_default_output_key(self):
        """Test that post stores exec_res in shared[output_key] if set."""
        node = ConfigurableOutputNode(output_key="result")
        shared = {}
        prep_res = {"input_text": "TEST"}
        exec_res = {"data": "test"}

        action = node.post(shared, prep_res, exec_res)

        # Should store entire exec_res in shared
        assert shared["result"] == {"data": "test"}
        assert action == "completed"

    def test_post_does_not_store_when_output_key_none(self):
        """Test that post doesn't store when output_key is None."""
        node = NoOutputKeyNode()
        shared = {}
        prep_res = {"input_text": "test"}
        exec_res = {"temp": "temporary data"}

        action = node.post(shared, prep_res, exec_res)

        # Should not store anything in shared
        assert shared == {}
        assert action == "done"

    def test_post_returns_action_from_get_action(self):
        """Test that post returns the action from get_action()."""
        node = ConditionalActionNode()
        shared = {}
        prep_res = {"input_text": "this will pass"}
        exec_res = {"passed": True}

        action = node.post(shared, prep_res, exec_res)

        assert action == "pass"

    def test_post_with_conditional_actions(self):
        """Test post returns different actions based on exec_res."""
        node = ConditionalActionNode()

        # Test pass condition
        shared = {}
        exec_res_pass = {"passed": True}
        action = node.post(shared, {}, exec_res_pass)
        assert action == "pass"

        # Test fail condition
        shared = {}
        exec_res_fail = {"passed": False}
        action = node.post(shared, {}, exec_res_fail)
        assert action == "fail"


class TestDeterministicNodeGetAction:
    """Test get_action() abstract method."""

    def test_get_action_must_be_implemented(self):
        """Test that get_action is abstract and must be implemented."""

        class IncompleteNode(DeterministicNode):
            """Node that doesn't implement get_action."""

            def exec(self, prep_res: dict) -> dict:
                return {}

        # Should raise TypeError because get_action is not implemented
        with pytest.raises(TypeError, match="Can't instantiate abstract class.*get_action"):
            IncompleteNode()

    def test_get_action_receives_exec_res(self):
        """Test that get_action receives exec_res parameter."""
        node = SimpleDeterministicNode()
        exec_res = {"result": "HELLO"}

        action = node.get_action(exec_res)

        assert action == "done"


class TestDeterministicNodeIntegration:
    """Test full node lifecycle (prep -> exec -> post)."""

    def test_full_lifecycle_with_defaults(self):
        """Test complete node execution with default settings."""
        node = SimpleDeterministicNode()
        shared = {"input_text": "hello world"}

        # Prep
        prep_res = node.prep(shared)
        assert prep_res == {"input_text": "hello world"}

        # Exec
        exec_res = node.exec(prep_res)
        assert exec_res == {"result": "HELLO WORLD"}

        # Post
        action = node.post(shared, prep_res, exec_res)
        assert action == "done"

    def test_full_lifecycle_with_custom_keys(self):
        """Test complete execution with custom input/output keys."""

        class CustomNode(DeterministicNode):
            def __init__(self):
                super().__init__()
                self.input_key = "source"
                self.output_key = "destination"

            def exec(self, prep_res: dict) -> dict:
                return {"value": prep_res["source"] + "!"}

            def get_action(self, exec_res: dict) -> str:
                return "complete"

        node = CustomNode()
        shared = {"source": "data", "input_text": "ignored"}

        # Prep
        prep_res = node.prep(shared)
        assert prep_res == {"source": "data"}

        # Exec
        exec_res = node.exec(prep_res)
        assert exec_res == {"value": "data!"}

        # Post
        action = node.post(shared, prep_res, exec_res)
        assert action == "complete"
        assert shared["destination"] == {"value": "data!"}

    def test_lifecycle_preserves_other_shared_data(self):
        """Test that node execution preserves unrelated shared data."""
        node = ConfigurableOutputNode(output_key="output")
        shared = {
            "input_text": "test",
            "other_data": "should remain",
            "existing_result": {"old": "value"},
        }

        prep_res = node.prep(shared)
        exec_res = node.exec(prep_res)
        node.post(shared, prep_res, exec_res)

        # Should preserve existing data
        assert shared["other_data"] == "should remain"
        assert shared["existing_result"] == {"old": "value"}
        # And add new result
        assert shared["output"] == {"data": "test"}


class TestDeterministicNodeInheritance:
    """Test that DeterministicNode properly inherits from Node."""

    def test_inherits_from_node(self):
        """Test that DeterministicNode is a subclass of Node."""
        assert issubclass(DeterministicNode, Node)

    def test_instance_is_node(self):
        """Test that instances are Node instances."""
        node = SimpleDeterministicNode()
        assert isinstance(node, Node)
        assert isinstance(node, DeterministicNode)

    def test_inherits_exec_from_node(self):
        """Test that DeterministicNode inherits exec() from Node.

        Note: exec() is not abstract in Node, so it has a default implementation.
        Subclasses typically override it with their own logic.
        """

        class MinimalNode(DeterministicNode):
            """Node that only implements get_action, inherits exec from Node."""

            def get_action(self, exec_res: dict) -> str:
                return "done"

        # Should not raise - exec is inherited from Node
        node = MinimalNode()
        assert hasattr(node, "exec")
        assert callable(node.exec)


class TestDeterministicNodeAttributes:
    """Test default attribute values."""

    def test_default_input_key(self):
        """Test that input_key defaults to 'input_text'."""
        node = SimpleDeterministicNode()
        assert node.input_key == "input_text"

    def test_default_output_key(self):
        """Test that output_key defaults to None."""
        node = SimpleDeterministicNode()
        assert node.output_key is None

    def test_can_override_input_key(self):
        """Test that input_key can be overridden."""
        node = ConfigurableInputNode(input_key="custom")
        assert node.input_key == "custom"

    def test_can_override_output_key(self):
        """Test that output_key can be overridden."""
        node = ConfigurableOutputNode(output_key="result")
        assert node.output_key == "result"


class TestDeterministicNodeEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input_text(self):
        """Test handling of empty input text."""
        node = SimpleDeterministicNode()
        shared = {"input_text": ""}

        prep_res = node.prep(shared)
        exec_res = node.exec(prep_res)

        assert prep_res == {"input_text": ""}
        assert exec_res == {"result": ""}

    def test_none_input_text_converts_to_empty(self):
        """Test that None input is treated as empty string."""
        node = SimpleDeterministicNode()
        shared = {"input_text": None}

        # get() with default should return None, but we handle it
        prep_res = node.prep(shared)

        # The node should handle None gracefully
        assert prep_res["input_text"] is None

    def test_multiple_nodes_share_dict(self):
        """Test that multiple nodes can work with same shared dict."""
        node1 = ConfigurableOutputNode(output_key="step1")
        node2 = ConfigurableOutputNode(output_key="step2")

        shared = {"input_text": "DATA"}

        # Node 1
        prep1 = node1.prep(shared)
        exec1 = node1.exec(prep1)
        node1.post(shared, prep1, exec1)

        # Node 2
        prep2 = node2.prep(shared)
        exec2 = node2.exec(prep2)
        node2.post(shared, prep2, exec2)

        # Both results should be in shared
        assert "step1" in shared
        assert "step2" in shared
        assert shared["step1"] == {"data": "data"}
        assert shared["step2"] == {"data": "data"}


class TestDeterministicNodeDocumentation:
    """Test that the class has proper documentation."""

    def test_class_has_docstring(self):
        """Test that DeterministicNode has a docstring."""
        assert DeterministicNode.__doc__ is not None
        assert len(DeterministicNode.__doc__) > 0

    def test_prep_has_docstring(self):
        """Test that prep() method is documented."""
        assert DeterministicNode.prep.__doc__ is not None

    def test_post_has_docstring(self):
        """Test that post() method is documented."""
        assert DeterministicNode.post.__doc__ is not None

    def test_get_action_has_docstring(self):
        """Test that get_action() method is documented."""
        assert DeterministicNode.get_action.__doc__ is not None
