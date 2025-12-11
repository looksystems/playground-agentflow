"""Pydantic data models for policy evaluation."""

from enum import Enum
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, Field


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


class SubCriterionResult(BaseModel):
    """Evaluation result for a single sub-criterion."""

    sub_criterion_id: str = Field(description="ID of the sub-criterion")
    sub_criterion_name: str = Field(description="Name of the sub-criterion")
    met: bool = Field(description="Whether the sub-criterion is satisfied")
    reasoning: str = Field(description="Explanation for the evaluation")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0",
    )


class CriterionResult(BaseModel):
    """Evaluation result for a single criterion."""

    criterion_id: str = Field(description="ID of the evaluated criterion")
    criterion_name: str = Field(description="Name of the criterion")
    met: bool = Field(description="Whether the criterion is satisfied")
    reasoning: str = Field(description="Explanation for the evaluation")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0",
    )
    sub_results: list[SubCriterionResult] = Field(
        default_factory=list,
        description="Results for sub-criteria if any",
    )


class ConfidenceLevel(str, Enum):
    """Confidence level classification."""

    HIGH = "high"  # Above high threshold
    MEDIUM = "medium"  # Between thresholds
    LOW = "low"  # Below low threshold


class PatternMatchResult(BaseModel):
    """Result from PatternMatchNode."""

    matched: bool = Field(description="Whether patterns matched based on mode")
    matched_patterns: list[str] = Field(
        default_factory=list, description="List of patterns that matched"
    )
    match_details: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Pattern -> list of matched strings",
    )


class KeywordScoreResult(BaseModel):
    """Result from KeywordScorerNode."""

    score: float = Field(description="Total weighted score")
    level: str = Field(description="Score level: high, medium, or low")
    matched_keywords: dict[str, float] = Field(
        default_factory=dict,
        description="Keyword -> weight for matched keywords",
    )


class LengthInfo(BaseModel):
    """Result from LengthGateNode."""

    char_count: int = Field(description="Character count")
    word_count: int = Field(description="Word count")
    bucket: str = Field(description="Length bucket name")


class ClassificationResult(BaseModel):
    """Result from ClassifierNode."""

    category: str = Field(description="Classified category")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(default="", description="Explanation for classification")


class SentimentResult(BaseModel):
    """Result from SentimentNode."""

    label: str = Field(description="Sentiment label: positive, negative, neutral, mixed")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    intensity: str | None = Field(
        default=None, description="Intensity: strong, moderate, weak (detailed mode)"
    )
    emotions: list[str] = Field(
        default_factory=list, description="Detected emotions (detailed mode)"
    )


class SampleResults(BaseModel):
    """Result from SamplerNode."""

    individual_results: list[bool] = Field(description="Results from each sample")
    aggregated_result: bool = Field(description="Final aggregated result")
    agreement_ratio: float = Field(
        ge=0.0, le=1.0, description="Ratio of samples that agree"
    )
    action: str = Field(description="Action: consensus, majority, or split")


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
