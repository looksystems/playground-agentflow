"""Pydantic data models for policy evaluation."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Self

import yaml
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .nodes.criterion import CriterionResult


class YAMLMixin:
    """Mixin class providing YAML serialization methods."""

    def to_yaml(self) -> str:
        """Serialize model to YAML string."""
        return yaml.dump(
            self.model_dump(mode="json"),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def save_yaml(self, path: str | Path) -> None:
        """Save model to a YAML file."""
        path = Path(path)
        with path.open("w") as f:
            f.write(self.to_yaml())

    @classmethod
    def from_yaml(cls, yaml_str: str) -> Self:
        """Load model from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)

    @classmethod
    def load_yaml(cls, path: str | Path) -> Self:
        """Load model from a YAML file."""
        path = Path(path)
        with path.open() as f:
            return cls.from_yaml(f.read())


class LogicOperator(str, Enum):
    """How criteria are combined."""

    ALL = "all"  # AND logic - all must match
    ANY = "any"  # OR logic - at least one must match


class Criterion(BaseModel):
    """A single criterion extracted from a policy."""

    id: str = Field(description="Unique identifier, e.g., 'criterion_1'")
    name: str = Field(description="Short name for the criterion")
    description: str = Field(description="Full text of the criterion")
    sub_criteria: list["Criterion"] = Field(
        default_factory=list,
        description="Nested sub-criteria (for OR within AND, etc.)",
    )
    sub_logic: LogicOperator | None = Field(
        default=None,
        description="Logic for combining sub-criteria",
    )


class ParsedPolicy(YAMLMixin, BaseModel):
    """Complete parsed policy structure."""

    title: str = Field(description="Policy title or name")
    description: str = Field(description="Overall policy description")
    criteria: list[Criterion] = Field(description="Top-level criteria")
    logic: LogicOperator = Field(
        default=LogicOperator.ALL,
        description="How top-level criteria are combined",
    )
    raw_text: str = Field(description="Original policy markdown text")


class ConfidenceLevel(str, Enum):
    """Confidence level classification."""

    HIGH = "high"  # Above high threshold
    MEDIUM = "medium"  # Between thresholds
    LOW = "low"  # Below low threshold


class EvaluationResult(YAMLMixin, BaseModel):
    """Complete evaluation result."""

    policy_satisfied: bool = Field(
        description="Whether the overall policy is satisfied"
    )
    input_text: str = Field(description="The text that was evaluated")
    policy_title: str = Field(description="Title of the policy used")
    criterion_results: list[CriterionResult] = Field(
        description="Per-criterion evaluation results"
    )
    overall_reasoning: str = Field(description="Summary of the evaluation")
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence score",
    )
    confidence_level: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Classified confidence level",
    )
    needs_review: bool = Field(
        default=False,
        description="Whether human review is recommended",
    )
    low_confidence_criteria: list[str] = Field(
        default_factory=list,
        description="IDs of criteria with low confidence scores",
    )


# ============================================================================
# Dynamic Workflow Models
# ============================================================================


class NodeConfig(BaseModel):
    """Configuration for a single node in a dynamic workflow."""

    id: str = Field(description="Unique node identifier")
    type: str = Field(description="Node class name (e.g., 'PatternMatchNode')")
    params: dict = Field(
        default_factory=dict,
        description="Node constructor parameters",
    )
    routes: dict[str, str] = Field(
        default_factory=dict,
        description="Action -> next node ID mapping",
    )


class WorkflowDefinition(BaseModel):
    """Definition of a workflow's node graph."""

    nodes: list[NodeConfig] = Field(description="List of node configurations")
    start_node: str = Field(description="ID of the starting node")


class ParsedWorkflowPolicy(YAMLMixin, BaseModel):
    """Policy parsed into a dynamic workflow definition."""

    title: str = Field(description="Policy title")
    description: str = Field(description="Policy description")
    workflow: WorkflowDefinition = Field(description="Workflow configuration")
    raw_text: str = Field(default="", description="Original policy markdown")


def _rebuild_models():
    """Rebuild models that use forward references from node modules."""
    from .nodes.criterion import CriterionResult
    EvaluationResult.model_rebuild()


_rebuild_models()
