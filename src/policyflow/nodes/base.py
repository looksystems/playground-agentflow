"""Base classes for node implementations."""

from abc import ABC, abstractmethod

from pocketflow import Node


class DeterministicNode(Node, ABC):
    """
    Base class for deterministic nodes with standardized input/output patterns.

    Provides default implementations of prep() and post() that handle common
    patterns for nodes that:
    - Read from a configurable input key in shared dict (default: "input_text")
    - Optionally write results to a configurable output key in shared dict
    - Determine routing action based on execution results

    Subclasses must implement:
    - exec(prep_res: dict) -> dict: Process the prepared input
    - get_action(exec_res: dict) -> str: Determine routing action from exec result

    Attributes:
        input_key: Key to read from shared dict in prep() (default: "input_text")
        output_key: Key to write exec_res to in post() (default: None = don't store)

    Example:
        class MyNode(DeterministicNode):
            def __init__(self):
                super().__init__()
                self.output_key = "my_result"  # Optional: store results

            def exec(self, prep_res: dict) -> dict:
                # Process the input
                return {"processed": prep_res["input_text"].upper()}

            def get_action(self, exec_res: dict) -> str:
                # Determine routing
                return "success"
    """

    input_key: str = "input_text"
    output_key: str | None = None

    def prep(self, shared: dict) -> dict:
        """
        Prepare input for execution by reading from shared dict.

        Reads value from shared[input_key] (defaults to empty string if missing)
        and returns it in a dict with the same key for exec() to process.

        Args:
            shared: Shared dictionary containing workflow state

        Returns:
            Dictionary with {input_key: value} for exec() to process
        """
        return {self.input_key: shared.get(self.input_key, "")}

    @abstractmethod
    def get_action(self, exec_res: dict) -> str:
        """
        Determine the routing action based on execution results.

        This method must be implemented by subclasses to define how the
        node determines which path to take in the workflow.

        Args:
            exec_res: Result dictionary from exec()

        Returns:
            Action string for workflow routing (e.g., "pass", "fail", "matched")
        """
        pass

    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        """
        Store execution results and return routing action.

        If output_key is set, stores the entire exec_res dict in shared[output_key].
        Always calls get_action() to determine the routing action.

        Args:
            shared: Shared dictionary containing workflow state
            prep_res: Result from prep() (unused in base implementation)
            exec_res: Result from exec()

        Returns:
            Action string from get_action() for workflow routing
        """
        # Store results if output_key is configured
        if self.output_key is not None:
            shared[self.output_key] = exec_res

        # Get routing action from subclass
        return self.get_action(exec_res)
