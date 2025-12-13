# Concepts & Workflow Primer

This document explains the core concepts and terminology used in PolicyFlow.

## What is PolicyFlow?

PolicyFlow automatically parses structured policy documents (in markdown) and evaluates any text against the extracted criteria. It's designed for:

- Financial regulation compliance
- Content moderation
- Contract analysis
- Any domain requiring automated policy enforcement with auditable results

## Design Philosophy

PolicyFlow is built around a key insight: **LLMs are powerful but imperfect**. They excel at semantic understanding but can hallucinate, lack consistency, and struggle to explain their reasoning in auditable ways. The architecture addresses these limitations while preserving the benefits of LLM-powered evaluation.

### Structured Intermediate Representations

**The Problem**: When an LLM parses a policy document directly into evaluation logic, failures are opaque. Did it misunderstand the policy? Generate wrong criteria? Route incorrectly?

**The Solution**: Two-step parsing with a human-readable intermediate format.

From an engineering perspective, this separation of concerns means:
- **Debuggability**: Inspect the normalized policy YAML to see exactly what the LLM understood
- **Reproducibility**: Same normalized policy always generates the same workflow
- **Editability**: Humans can correct LLM parsing errors before workflow generation

From an LLM reasoning perspective:
- **Decomposition**: Complex tasks (understand policy → generate workflow) are split into simpler subtasks
- **Verification checkpoints**: Each step's output can be validated before proceeding
- **Error localization**: When something fails, you know which step to investigate

### Explainable by Design

**The Problem**: LLMs often produce correct answers with no clear reasoning trail. In compliance domains, "trust me" isn't acceptable.

**The Solution**: Node IDs directly correspond to clause numbers (`clause_1_1_a`).

From an engineering perspective:
- **Traceability**: Every evaluation result maps to specific policy text
- **Auditability**: Compliance officers can verify exactly which requirements were checked
- **Debugging**: When clause 1.2.b fails, you know exactly where to look

From an LLM reasoning perspective:
- **Grounded outputs**: The LLM's decisions are anchored to source document locations
- **Structured reasoning**: Instead of free-form explanation, reasoning follows the policy structure
- **Reviewable chain of thought**: Each clause evaluation is a discrete, inspectable decision

### Calibrated Uncertainty

**The Problem**: LLMs don't naturally express uncertainty well. They may confidently state incorrect answers or hedge unnecessarily on clear cases.

**The Solution**: Explicit confidence scores with threshold-based routing.

From an engineering perspective:
- **Risk management**: High-stakes decisions can require higher confidence thresholds
- **Human escalation**: Low confidence triggers review rather than silent failures
- **Quality metrics**: Track confidence distributions to identify systematic issues

From an LLM reasoning perspective:
- **Epistemic humility**: Force the model to quantify its uncertainty rather than assert
- **Calibration feedback**: Benchmark results reveal if confidence scores are meaningful
- **Graceful degradation**: Uncertain cases route to humans instead of producing errors

### Hybrid Evaluation Strategy

**The Problem**: LLM calls are slow and expensive. Using them for every check is wasteful when simple patterns would suffice.

**The Solution**: Mix deterministic nodes (regex, keywords) with LLM nodes (classification, sentiment).

From an engineering perspective:
- **Cost optimization**: Reserve expensive LLM calls for semantic understanding
- **Latency reduction**: Deterministic checks run in milliseconds
- **Predictability**: Regex patterns don't hallucinate or vary between runs

From an LLM reasoning perspective:
- **Appropriate tool selection**: Not every problem needs semantic understanding
- **Filtering before reasoning**: Deterministic checks can pre-filter obvious cases
- **Complementary strengths**: Patterns catch exact matches; LLMs handle nuance

### Continuous Improvement Loop

**The Problem**: LLM-based systems are hard to improve systematically. Without measurement, changes are guesswork.

**The Solution**: Integrated benchmark system with golden datasets and optimization.

From an engineering perspective:
- **Regression testing**: Ensure improvements don't break previously correct cases
- **Systematic iteration**: Measure → analyze → hypothesize → test cycle
- **Version comparison**: Track which workflow version performs best

From an LLM reasoning perspective:
- **Ground truth feedback**: Compare LLM outputs against known-correct labels
- **Failure pattern analysis**: Identify systematic errors (certain clause types, edge cases)
- **Prompt optimization**: Test prompt variations with controlled experiments

## Core Terminology

### Policy Structure

```
Policy (markdown document)
  └── Section (logical grouping)
        └── Clause (evaluatable requirement)
              └── Sub-clause (nested requirement)
```

**Clause**: An individual evaluatable requirement with hierarchical numbering (e.g., `1`, `1.1`, `1.1.a`). Each clause has:
- `number`: Hierarchical identifier
- `text`: The requirement text
- `clause_type`: REQUIREMENT, DEFINITION, CONDITION, EXCEPTION, or REFERENCE
- `logic`: How sub-clauses combine (ALL or ANY)
- `sub_clauses`: Nested requirements

**Section**: A logical grouping of related clauses within a policy.

### Logic Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `ALL` | All sub-clauses must be satisfied (AND) | "must include (a) and (b)" |
| `ANY` | At least one sub-clause must be satisfied (OR) | "must include (a) or (b)" |

### Clause Types

| Type | Description | Typical Handling |
|------|-------------|------------------|
| `REQUIREMENT` | Must be evaluated/checked | PatternMatchNode, ClassifierNode |
| `DEFINITION` | Defines terms for context | Context only, not evaluated |
| `CONDITION` | If/then logic | ClassifierNode with routing |
| `EXCEPTION` | Exceptions to rules | Short-circuit evaluation |
| `REFERENCE` | References external docs | Context only |

### Confidence Levels

| Level | Threshold | Meaning |
|-------|-----------|---------|
| `HIGH` | ≥ 0.8 | High certainty in evaluation |
| `MEDIUM` | 0.5 - 0.8 | Moderate uncertainty |
| `LOW` | < 0.5 | Low confidence, needs review |

Results with `MEDIUM` or `LOW` confidence are flagged for human review via the `needs_review` field.

## Two-Step Parsing

PolicyFlow uses a two-step parsing process for maximum control and auditability:

```
┌─────────────────────┐
│  Raw Policy (.md)   │
└─────────┬───────────┘
          │
          ▼ Step 1: Normalize
┌─────────────────────┐
│ NormalizedPolicy    │  ← Human-reviewable YAML
│  - sections         │    Can be edited before
│  - clauses          │    workflow generation
│  - hierarchy        │
└─────────┬───────────┘
          │
          ▼ Step 2: Generate Workflow
┌─────────────────────┐
│ ParsedWorkflowPolicy│  ← Executable workflow
│  - nodes            │    Node IDs = clause numbers
│  - routes           │    (clause_1_1_a)
│  - hierarchy        │
└─────────┬───────────┘
          │
          ▼ Execution
┌─────────────────────┐
│  EvaluationResult   │  ← Per-clause results
│  - policy_satisfied │    with confidence and
│  - clause_results   │    reasoning
└─────────────────────┘
```

### Step 1: Normalization

Converts raw markdown to a structured `NormalizedPolicy`:

```python
from policyflow import normalize_policy

normalized = normalize_policy(policy_markdown)
normalized.save_yaml("normalized.yaml")  # Review/edit if needed
```

The normalized output preserves:
- Document hierarchy (sections → clauses → sub-clauses)
- Original clause text
- Inferred logic operators (ALL/ANY)
- Clause types

### Step 2: Workflow Generation

Converts `NormalizedPolicy` to executable `ParsedWorkflowPolicy`:

```python
from policyflow import generate_workflow_from_normalized

workflow = generate_workflow_from_normalized(normalized)
workflow.save_yaml("workflow.yaml")
```

Key feature: **Node IDs match clause numbers** for traceability:
- Clause `1.1` → Node ID `clause_1_1`
- Clause `1.1.a` → Node ID `clause_1_1_a`

### Combined Parsing

For convenience, both steps can run together:

```python
from policyflow import parse_policy

workflow = parse_policy(policy_markdown, save_normalized="normalized.yaml")
```

## Evaluation Workflow

```
┌─────────────────┐     ┌─────────────────┐
│   Input Text    │────▶│  Workflow       │
└─────────────────┘     │  (Node Graph)   │
                        └────────┬────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ clause_1_1    │    │ clause_1_2    │    │ clause_2_1    │
│ (Classifier)  │    │ (Pattern)     │    │ (Sentiment)   │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Aggregate       │
                    │ Results         │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ EvaluationResult│
                    │ - satisfied     │
                    │ - confidence    │
                    │ - clause_results│
                    └─────────────────┘
```

## Node Types

Nodes are the building blocks of evaluation workflows. There are two categories:

### LLM-Based Nodes

Use LLM calls for semantic understanding:

| Node | Purpose |
|------|---------|
| `ClassifierNode` | Classify text into categories |
| `SentimentNode` | Analyze sentiment/tone |
| `DataExtractorNode` | Extract structured data |
| `SamplerNode` | Run multiple evaluations for consensus |

### Deterministic Nodes

No LLM required, fast and predictable:

| Node | Purpose |
|------|---------|
| `PatternMatchNode` | Regex/keyword pattern matching |
| `KeywordScorerNode` | Weighted keyword scoring |
| `TransformNode` | Text preprocessing |
| `LengthGateNode` | Route by text length |

### Internal Nodes

Used by the system for routing:

| Node | Purpose |
|------|---------|
| `ConfidenceGateNode` | Route based on confidence thresholds |

## Result Structure

```yaml
policy_satisfied: true           # Overall decision
overall_confidence: 0.87         # Average confidence
confidence_level: high           # HIGH, MEDIUM, or LOW
needs_review: false              # Flag for human review
low_confidence_clauses: []       # IDs of uncertain clauses

clause_results:
  - clause_id: clause_1_1
    clause_name: "Recipient Capacity"
    met: true
    confidence: 0.92
    reasoning: "Text addresses investor directly"
    sub_results:
      - clause_id: clause_1_1_a
        met: true
        confidence: 0.95
        reasoning: "Clear investor status reference"
```

## Benchmark System

PolicyFlow includes a comprehensive system for testing and optimizing workflows:

```
┌─────────────────┐
│ Golden Dataset  │  ← Test cases with expected results
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Benchmark       │  ← Run workflow against test cases
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analysis        │  ← Identify failure patterns
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Hypothesize     │  ← Generate improvement ideas
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Optimize        │  ← Apply and test improvements
└─────────────────┘
```

See the [User Guide](USERGUIDE.md#benchmarking-api) for detailed usage.
