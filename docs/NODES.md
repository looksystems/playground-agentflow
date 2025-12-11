# Node Quick Reference

## Node Lifecycle

```
shared dict → prep() → exec() → post() → action string → next node
```

## Available Nodes

### Deterministic Nodes (No LLM)

| Node | Description | Parameters | Actions |
|------|-------------|------------|---------|
| **PatternMatchNode** | Match regex/keyword patterns | `patterns: list[str]`, `mode: any\|all\|none` | `matched`, `not_matched` |
| **LengthGateNode** | Route by text length | `min_length: int`, `max_length: int` | `within_range`, `too_short`, `too_long` |
| **KeywordScorerNode** | Score weighted keywords | `keywords: dict[str, float]`, `threshold: float` | `above_threshold`, `below_threshold` |
| **TransformNode** | Preprocess text | `operations: list[str]` | `default` |

**TransformNode operations:** `lowercase`, `strip_html`, `truncate:N`, `normalize_whitespace`

### LLM-Based Nodes

| Node | Description | Parameters | Actions |
|------|-------------|------------|---------|
| **ClassifierNode** | Classify into categories | `categories: list[str]`, `description: str` | category names |
| **SentimentNode** | Analyze sentiment/tone | `granularity: basic\|detailed` | `positive`, `negative`, `neutral`, `mixed` |
| **DataExtractorNode** | Extract structured data | `fields: list[str]`, `description: str` | `extracted`, `no_data` |
| **SamplerNode** | Run N evaluations for consensus | `samples: int`, `threshold: float` | `consensus`, `no_consensus` |

### Internal Nodes (Used by Parser)

| Node | Description | Actions |
|------|-------------|---------|
| **CriterionEvaluationNode** | Evaluate single criterion | `default` |
| **SubCriterionNode** | Evaluate sub-criteria | `default` |
| **ResultAggregatorNode** | Aggregate with AND/OR logic | `default` |
| **ConfidenceGateNode** | Route by confidence | `high_confidence`, `needs_review`, `low_confidence` |

## Shared Store Keys

### Input Keys
- `input_text` - Main text to evaluate
- `policy` - Parsed policy object
- `workflow_config` - Configuration settings

### Output Keys
- `pattern_match_result` - PatternMatchNode result
- `keyword_score` - KeywordScorerNode score
- `length_info` - LengthGateNode info
- `classification` - ClassifierNode result
- `sentiment` - SentimentNode result
- `extracted_data` - DataExtractorNode result
- `criterion_results` - List of criterion evaluations
- `evaluation_result` - Final aggregated result

## Creating a Custom Node

```python
from pocketflow import Node
from policy_evaluator.nodes import NodeSchema, NodeParameter, register_node

class MyNode(Node):
    parser_schema = NodeSchema(
        name="MyNode",
        description="What this node does",
        category="deterministic",  # or "llm", "internal"
        parameters=[
            NodeParameter("param1", "str", "Description", required=True),
            NodeParameter("param2", "int", "Optional param", required=False, default=10),
        ],
        actions=["action1", "action2"],
        parser_exposed=True,
    )

    def __init__(self, param1: str, param2: int = 10):
        super().__init__()
        self.param1 = param1
        self.param2 = param2

    def prep(self, shared: dict) -> dict:
        return {"text": shared.get("input_text", "")}

    def exec(self, prep_res: dict) -> dict:
        # Your logic here
        return {"result": prep_res["text"].upper()}

    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        shared["my_result"] = exec_res["result"]
        return "action1"

# Register the node
register_node(MyNode)
```

## Creating an LLM Node

```python
from policy_evaluator.nodes import LLMNode, NodeSchema, NodeParameter

class MyLLMNode(LLMNode):
    parser_schema = NodeSchema(
        name="MyLLMNode",
        description="LLM-powered analysis",
        category="llm",
        parameters=[...],
        actions=["success", "failure"],
        parser_exposed=True,
    )

    def __init__(self, config, prompt: str, cache_ttl: int = 3600):
        super().__init__(config=config, cache_ttl=cache_ttl)
        self.prompt = prompt

    def prep(self, shared: dict) -> dict:
        return {"text": shared.get("input_text", "")}

    def exec(self, prep_res: dict) -> dict:
        return self.call_llm(
            prompt=f"{self.prompt}\n\nText: {prep_res['text']}",
            system_prompt="You are an analyst.",
            yaml_response=True,
            span_name="my_llm_node"
        )

    def post(self, shared: dict, prep_res: dict, exec_res: dict) -> str:
        shared["my_analysis"] = exec_res
        return "success"
```

## Node Routing

```python
# Linear flow
node1 >> node2 >> node3

# Conditional routing
node1 - "action1" >> node2
node1 - "action2" >> node3

# Example: LengthGateNode routing
length_gate - "within_range" >> classifier
length_gate - "too_short" >> reject_node
length_gate - "too_long" >> truncate_node
```

## Registry Functions

```python
from policy_evaluator.nodes import (
    register_node,
    get_node_class,
    get_all_nodes,
    get_parser_schemas,
)

# Register a node
register_node(MyNode)

# Get node class by name
cls = get_node_class("PatternMatchNode")

# Get all registered nodes
all_nodes = get_all_nodes()

# Get schemas for parser-exposed nodes
schemas = get_parser_schemas()
```
