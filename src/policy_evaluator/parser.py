"""Policy parsing using LLM."""

from .models import ParsedPolicy, ParsedWorkflowPolicy
from .config import WorkflowConfig
from .llm import call_llm
from .prompts import get_criteria_parser_prompt, get_workflow_parser_prompt

# Default model for parsing operations
DEFAULT_PARSER_MODEL = "anthropic/claude-sonnet-4-20250514"


def parse_policy(
    policy_markdown: str,
    config: WorkflowConfig | None = None,
    model: str | None = None,
) -> ParsedPolicy:
    """
    Parse a markdown policy document into structured criteria.

    This is the original parsing function that extracts criteria structure.
    For dynamic workflow generation, use parse_policy_to_workflow() instead.

    Args:
        policy_markdown: Raw markdown text of the policy
        config: Optional workflow configuration
        model: LLM model identifier (uses DEFAULT_PARSER_MODEL if not provided)

    Returns:
        ParsedPolicy with extracted criteria and logic
    """
    config = config or WorkflowConfig()
    model = model or DEFAULT_PARSER_MODEL

    data = call_llm(
        prompt=f"Parse this policy:\n\n{policy_markdown}",
        system_prompt=get_criteria_parser_prompt(),
        model=model,
        config=config,
        yaml_response=True,
        span_name="parse_policy_criteria",
    )

    return ParsedPolicy.model_validate({**data, "raw_text": policy_markdown})


def parse_policy_to_workflow(
    policy_markdown: str,
    config: WorkflowConfig | None = None,
    model: str | None = None,
) -> ParsedWorkflowPolicy:
    """
    Parse a markdown policy document into a dynamic workflow definition.

    This function uses the LLM to analyze the policy and generate a workflow
    configuration using available node types. The resulting workflow can be
    executed using DynamicWorkflowBuilder.

    The parser prompt is dynamically constructed to include documentation
    for all parser-exposed nodes, so the LLM knows what tools are available.

    Args:
        policy_markdown: Raw markdown text of the policy
        config: Optional workflow configuration
        model: LLM model identifier (uses DEFAULT_PARSER_MODEL if not provided)

    Returns:
        ParsedWorkflowPolicy with workflow definition ready for execution

    Example:
        >>> policy = '''
        ... # Content Moderation Policy
        ... All user content must be checked for:
        ... 1. Profanity or offensive language
        ... 2. Spam indicators (excessive links, repeated phrases)
        ... 3. Negative sentiment that may require human review
        ... '''
        >>> parsed = parse_policy_to_workflow(policy)
        >>> from policy_evaluator.workflow_builder import DynamicWorkflowBuilder
        >>> builder = DynamicWorkflowBuilder(parsed)
        >>> result = builder.run("Check this user message")
    """
    config = config or WorkflowConfig()
    model = model or DEFAULT_PARSER_MODEL

    data = call_llm(
        prompt=f"Parse this policy and generate a workflow:\n\n{policy_markdown}",
        system_prompt=get_workflow_parser_prompt(),
        model=model,
        config=config,
        yaml_response=True,
        span_name="parse_policy_to_workflow",
    )

    return ParsedWorkflowPolicy.model_validate({**data, "raw_text": policy_markdown})
