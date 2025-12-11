# Personal Recommendation Evaluation Workflow

## Status: ✅ Implemented

## Objective
Standalone Python script using Anthropic's Agent SDK that evaluates whether an input text constitutes a "personal recommendation" based on regulatory definition.

## Definition Criteria (from policy.md)
A personal recommendation must satisfy ALL of:
1. **Recipient**: Made to a person as an investor/potential investor (or their agent)
2. **Action**: Recommends buying/selling/subscribing/exchanging/redeeming/holding/underwriting a security, structured deposit, or relevant investment
3. **Personalization**: Either presented as suitable for the person OR based on their circumstances
4. **Distribution**: NOT issued exclusively to the public

---

## Implementation

### File: `personal_recommendation_evaluator.py`

**Run with:**
```bash
uv run personal_recommendation_evaluator.py
```

### Architecture
- **Single agent approach**: Uses Claude Agent SDK with `query()` function
- **JSON output parsing**: System prompt instructs Claude to return structured JSON
- **Pydantic validation**: Response parsed and validated with Pydantic models

### Key Components

1. **Pydantic Models** (`CriterionEvaluation`, `PersonalRecommendationResult`)
   - Structured output with per-criterion evaluation
   - Confidence scores (0.0-1.0) for each criterion
   - Detailed reasoning strings

2. **System Prompt**
   - Embeds full regulatory definition of personal recommendation
   - Specifies exact JSON output schema
   - Instructions for independent criterion evaluation

3. **`evaluate_personal_recommendation(input_text: str)`**
   - Async function using `claude-agent-sdk`
   - Returns `PersonalRecommendationResult` with detailed breakdown

### Dependencies (via uv inline script)
```
claude-agent-sdk
pydantic>=2.0
```

---

## Test Results

### Test Case 1: Personal Recommendation
**Input:** "Based on your risk profile and investment goals, I recommend you purchase shares in XYZ Corp."

**Result:** ✅ IS a personal recommendation (97% confidence)
- Criterion 1 (Recipient): MET - Addressed to potential investor
- Criterion 2 (Action): MET - Recommends buying shares
- Criterion 3 (Personalization): MET - Based on risk profile/goals
- Criterion 4 (Distribution): MET - Private communication

### Test Case 2: Public Broadcast
**Input:** "Our analysts believe XYZ Corp is a strong buy for 2024. This report is published for all subscribers."

**Result:** ❌ NOT a personal recommendation (92% confidence)
- Criterion 1 (Recipient): MET - Subscribers are investors
- Criterion 2 (Action): MET - Recommends buying
- Criterion 3 (Personalization): NOT MET - No individual consideration
- Criterion 4 (Distribution): NOT MET - Published to all subscribers

---

## Usage

### Programmatic
```python
from personal_recommendation_evaluator import evaluate_personal_recommendation
import asyncio

result = asyncio.run(evaluate_personal_recommendation("Your text here"))
print(result.is_personal_recommendation)
print(result.overall_reasoning)
```

### CLI
```bash
uv run personal_recommendation_evaluator.py
```
