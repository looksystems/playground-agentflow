# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "claude-agent-sdk",
#     "pydantic>=2.0",
# ]
# ///
"""
Personal Recommendation Evaluator

Evaluates whether an input text constitutes a "personal recommendation"
based on regulatory definition using Claude Agent SDK.

Usage:
    uv run personal_recommendation_evaluator.py
"""

from pydantic import BaseModel, Field
import asyncio
import json
import re


class CriterionEvaluation(BaseModel):
    """Evaluation result for a single criterion."""
    met: bool = Field(description="Whether this criterion is satisfied")
    reasoning: str = Field(description="Explanation for the evaluation")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")


class PersonalRecommendationResult(BaseModel):
    """Complete evaluation result for personal recommendation assessment."""
    is_personal_recommendation: bool = Field(
        description="True if ALL criteria are met"
    )
    criterion_1_recipient: CriterionEvaluation = Field(
        description="Criterion 1: Made to investor/potential investor or their agent"
    )
    criterion_2_action: CriterionEvaluation = Field(
        description="Criterion 2: Recommends buy/sell/subscribe/exchange/redeem/hold/underwrite"
    )
    criterion_3_personalization: CriterionEvaluation = Field(
        description="Criterion 3: Presented as suitable OR based on person's circumstances"
    )
    criterion_4_distribution: CriterionEvaluation = Field(
        description="Criterion 4: NOT issued exclusively to the public"
    )
    overall_reasoning: str = Field(description="Summary of the evaluation")
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence 0-1")


SYSTEM_PROMPT = """You are a regulatory compliance expert evaluating whether communications constitute "personal recommendations" under financial regulations.

## Definition of Personal Recommendation

A personal recommendation is a recommendation that meets ALL of the following criteria:

### Criterion 1 - Recipient
The recommendation is made to a person in their capacity as:
(a) an investor or potential investor; or
(b) agent for an investor or a potential investor

### Criterion 2 - Action
The recommendation is for the person to do any of the following (whether as principal or agent):
(a) buy, sell, subscribe for, exchange, redeem, hold or underwrite a particular investment which is a security, a structured deposit or a relevant investment; or
(b) exercise or not exercise any right conferred by such an investment to buy, sell, subscribe for, exchange or redeem such an investment

### Criterion 3 - Personalization
The recommendation is either:
(a) presented as suitable for the person to whom it is made; or
(b) based on a consideration of the circumstances of that person

### Criterion 4 - Distribution
The recommendation is NOT issued exclusively to the public.

## Output Format

You MUST respond with ONLY a JSON object (no markdown, no explanation outside JSON) matching this exact schema:

```json
{
  "is_personal_recommendation": boolean,
  "criterion_1_recipient": {
    "met": boolean,
    "reasoning": "string",
    "confidence": number (0.0-1.0)
  },
  "criterion_2_action": {
    "met": boolean,
    "reasoning": "string",
    "confidence": number (0.0-1.0)
  },
  "criterion_3_personalization": {
    "met": boolean,
    "reasoning": "string",
    "confidence": number (0.0-1.0)
  },
  "criterion_4_distribution": {
    "met": boolean,
    "reasoning": "string",
    "confidence": number (0.0-1.0)
  },
  "overall_reasoning": "string",
  "overall_confidence": number (0.0-1.0)
}
```

## Evaluation Instructions

1. Evaluate each criterion independently
2. Provide clear reasoning for each criterion
3. Assign a confidence score (0.0-1.0) for each criterion
4. The input is a personal recommendation ONLY if ALL four criteria are met
5. Be thorough but concise in your reasoning
6. Output ONLY the JSON object, nothing else
"""


def extract_json(text: str) -> dict:
    """Extract JSON from text that may contain markdown code blocks."""
    # Try to find JSON in code block
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_block_match:
        text = code_block_match.group(1)

    # Try to parse as JSON directly
    text = text.strip()
    return json.loads(text)


async def evaluate_personal_recommendation(input_text: str) -> PersonalRecommendationResult:
    """
    Evaluate whether input_text constitutes a personal recommendation.

    Args:
        input_text: The text to evaluate

    Returns:
        PersonalRecommendationResult with detailed criterion-by-criterion evaluation
    """
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

    prompt = f"""Evaluate whether the following text constitutes a "personal recommendation" under the regulatory definition.

TEXT TO EVALUATE:
---
{input_text}
---

Respond with ONLY the JSON evaluation object."""

    full_response = ""

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            max_turns=1
        )
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    full_response += block.text

    if not full_response:
        raise RuntimeError("No response received from agent")

    try:
        data = extract_json(full_response)
        return PersonalRecommendationResult.model_validate(data)
    except (json.JSONDecodeError, Exception) as e:
        raise RuntimeError(f"Failed to parse response as JSON: {e}\nResponse: {full_response}")


def print_result(result: PersonalRecommendationResult) -> None:
    """Pretty print the evaluation result."""
    print("\n" + "=" * 60)
    print("PERSONAL RECOMMENDATION EVALUATION RESULT")
    print("=" * 60)

    status = "YES" if result.is_personal_recommendation else "NO"
    print(f"\nIs Personal Recommendation: {status}")
    print(f"Overall Confidence: {result.overall_confidence:.1%}")

    print("\n" + "-" * 60)
    print("CRITERION BREAKDOWN")
    print("-" * 60)

    criteria = [
        ("1. Recipient (investor/potential investor)", result.criterion_1_recipient),
        ("2. Action (buy/sell/subscribe etc.)", result.criterion_2_action),
        ("3. Personalization (suitable/circumstance-based)", result.criterion_3_personalization),
        ("4. Distribution (NOT public-only)", result.criterion_4_distribution),
    ]

    for name, criterion in criteria:
        status = "MET" if criterion.met else "NOT MET"
        print(f"\n{name}")
        print(f"  Status: {status} (confidence: {criterion.confidence:.1%})")
        print(f"  Reasoning: {criterion.reasoning}")

    print("\n" + "-" * 60)
    print("OVERALL REASONING")
    print("-" * 60)
    print(result.overall_reasoning)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Example test cases
    test_inputs = [
        # Should be a personal recommendation
        "Based on your risk profile and investment goals, I recommend you purchase shares in XYZ Corp.",

        # Should NOT be a personal recommendation (public broadcast)
        "Our analysts believe XYZ Corp is a strong buy for 2024. This report is published for all subscribers.",
    ]

    async def main():
        for i, test_input in enumerate(test_inputs, 1):
            print(f"\n{'#' * 60}")
            print(f"TEST CASE {i}")
            print(f"{'#' * 60}")
            print(f"Input: {test_input}")

            result = await evaluate_personal_recommendation(test_input)
            print_result(result)

    asyncio.run(main())
