"""Decorators for automatic node schema generation."""

import inspect
from typing import Any, Callable, TypeVar

from .schema import NodeParameter, NodeSchema

# Reserved parameter names that should not be included in parser schema
RESERVED_PARAMS = {"self", "config", "cache_ttl", "rate_limit"}

T = TypeVar("T")


def node_schema(
    description: str,
    category: str,
    actions: list[str] | None = None,
    yaml_example: str = "",
    parser_exposed: bool = True,
    parameter_descriptions: dict[str, str] | None = None,
) -> Callable[[type[T]], type[T]]:
    """
    Decorator that auto-generates NodeSchema from class __init__ signature.

    This decorator inspects the __init__ method of the decorated class and
    automatically generates a NodeSchema by extracting:
    - Parameter names and types from type annotations
    - Required vs optional (presence of default values)
    - Parameter descriptions from parameter_descriptions dict or auto-generated

    Reserved parameters (config, cache_ttl, rate_limit) are automatically excluded.

    Args:
        description: Brief description of what the node does
        category: Node category ("llm", "deterministic", "routing", "internal")
        actions: List of possible action strings the node can return
        yaml_example: Example YAML configuration for documentation
        parser_exposed: Whether to expose this node to the parser (default: True)
        parameter_descriptions: Optional dict mapping parameter names to descriptions

    Returns:
        Decorator function that adds parser_schema attribute to the class

    Example:
        @node_schema(
            description="Classify input into predefined categories",
            category="llm",
            actions=["<category_name>"],
            parameter_descriptions={
                "categories": "List of category names to classify into"
            }
        )
        class ClassifierNode(LLMNode):
            def __init__(
                self,
                categories: list[str],
                config: WorkflowConfig,
                model: str | None = None,
            ):
                ...
    """

    def decorator(cls: type[T]) -> type[T]:
        # Get __init__ signature
        sig = inspect.signature(cls.__init__)

        # Extract parameters from signature
        parameters: list[NodeParameter] = []
        param_descs = parameter_descriptions or {}

        for param_name, param in sig.parameters.items():
            # Skip reserved parameters
            if param_name in RESERVED_PARAMS:
                continue

            # Determine if parameter is required (no default value)
            is_required = param.default == inspect.Parameter.empty

            # Get default value if it exists
            default_value = None if is_required else param.default

            # Extract type annotation
            type_str = "Any"
            if param.annotation != inspect.Parameter.empty:
                # Convert annotation to string representation
                type_str = _format_type_annotation(param.annotation)

            # Generate or use provided description
            param_description = param_descs.get(
                param_name, _generate_default_description(param_name, type_str)
            )

            # Create NodeParameter
            node_param = NodeParameter(
                name=param_name,
                type=type_str,
                description=param_description,
                required=is_required,
                default=default_value,
            )
            parameters.append(node_param)

        # Create NodeSchema
        schema = NodeSchema(
            name=cls.__name__,
            description=description,
            category=category,
            parameters=parameters,
            actions=actions or [],
            yaml_example=yaml_example,
            parser_exposed=parser_exposed,
        )

        # Attach schema to class
        cls.parser_schema = schema

        return cls

    return decorator


def _format_type_annotation(annotation: Any) -> str:
    """
    Format a type annotation as a string.

    Args:
        annotation: Type annotation from inspect

    Returns:
        String representation of the type
    """
    # Handle string annotations (already formatted)
    if isinstance(annotation, str):
        return annotation

    # Get the string representation
    type_str = str(annotation)

    # Clean up common patterns
    # typing.List[str] -> list[str]
    type_str = type_str.replace("typing.", "")

    # <class 'str'> -> str
    if type_str.startswith("<class '") and type_str.endswith("'>"):
        type_str = type_str[8:-2]

    return type_str


def _generate_default_description(param_name: str, param_type: str) -> str:
    """
    Generate a default description for a parameter.

    Args:
        param_name: Parameter name
        param_type: Parameter type string

    Returns:
        Auto-generated description
    """
    # Convert snake_case to space-separated words
    words = param_name.replace("_", " ")

    # Capitalize first word
    description = f"{words.capitalize()} parameter"

    # Add type information if meaningful
    if param_type != "Any":
        description += f" ({param_type})"

    return description
