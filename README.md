# AgentEval

Eval harness for AI agents. Tests thinking, workflow, and output quality.

Based on Anthropic's ["Demystifying Evals for AI Agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

## Overview

Evals catch agent failures before production. Without them, debugging becomes reactive: user reports issue → manual reproduction → fix → deployment uncertainty.

This implementation provides a complete eval system with three grader types, multiple trial support, and transcript analysis.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

python main.py --suite coding --trials 2
```

## Project Structure

```
AgentEval/
├── agents/
│   └── task_agent.py        # Agent being evaluated (bootstrapped)
│
├── evals/
│   ├── harness.py           # Runs tasks, grades results
│   ├── metrics.py           # pass@k and pass^k calculations
│   │
│   ├── graders/             # Three grader types
│   │   ├── code_grader.py        Fast deterministic checks
│   │   ├── llm_grader.py         LLM-as-judge
│   │   ├── transcript_grader.py  Workflow/process checks
│   │   └── rubrics/              Judging criteria
│   │
│   └── tasks/              # Task definitions (YAML)
│       ├── coding_tasks.yaml
│       ├── research_tasks.yaml
│       └── conversational_tasks.yaml
│
├── results/                # Eval results + transcripts
├── main.py                 # CLI entry point
└── config.py               # Model selection, settings
```

## Core Concepts

### Terminology

- **Task**: One test case with inputs and success criteria (one YAML entry)
- **Trial**: One attempt at a task (one agent run)
- **Transcript**: Full record of tool calls and reasoning
- **Outcome**: Final state (what the grader sees, not what the agent claims)
- **Grader**: Code that scores performance
- **Suite**: Collection of tasks measuring specific capabilities

### Three Types of Graders

**CodeGrader** - Fast deterministic checks on final output
- Examples: `contains "fibonacci"`, regex matches, `tool_was_called`
- Near-instant, free, deterministic

**LLMGrader** - Judges nuanced aspects requiring interpretation
- Examples: "Is this explanation accurate?", "Is the tone appropriate?"
- Slower, costs API calls, non-deterministic

**TranscriptGrader** - Process/workflow checks
- Examples: `max_turns: 8`, `required_tools: [search]`, `min_think_calls: 1`
- Fast, free, deterministic
- Validates agent followed expected process

### pass@k vs pass^k

Agent behavior varies between runs. These metrics quantify that variance:

- **pass@k**: Probability of ≥1 success in k attempts. Rises as k increases. Relevant for coding tasks where one correct solution suffices.
- **pass^k**: Probability that all k attempts succeed. Falls as k increases. Relevant for production where every interaction must work.

Example: Agent succeeds 3 out of 5 trials (60% per-trial success rate)
- pass@1 = 60%, pass^1 = 60% (identical at k=1)
- pass@3 ≈ 94%, pass^3 ≈ 22% (diverging)
- pass@5 ≈ 99%, pass^5 ≈ 8% (opposite stories)

High pass@k with low pass^k indicates consistency issues rather than capability limits.

Implementation: `evals/metrics.py`

### Capability vs Regression Tasks

Tasks can be tagged by purpose:
- `tags: ["capability"]` - New functionality being developed, typically start with low pass rates
- `tags: ["regression"]` - Existing functionality, should maintain near 100% pass rates

Filter by tag:
```bash
python main.py --tags capability
python main.py --tags regression --trials 1
```

### Balanced Problem Sets

Evals include both positive and negative cases. For search behavior testing:
- Tasks where search is required (`should-search`)
- Tasks where search is unnecessary (`should-not-search`)

This prevents optimization toward always-search or never-search behavior.

`research_tasks.yaml` demonstrates this. `TranscriptGrader` enforces balance via `required_tools` and `forbidden_tools`.

## Transcript Analysis

Full transcripts are saved to `results/transcripts/` after each eval run.

```bash
# Run with detailed output
python main.py --suite coding --trials 3 --show-transcripts

# Inspect raw transcript
cat results/transcripts/code_fibonacci_trial1.json | python -m json.tool | head -100
```

Transcripts show:
1. Whether grader judgments match actual behavior
2. Whether agent mistakes are genuine or grader misses valid solutions
3. Tool call sequences and their appropriateness
4. Turn count and efficiency

## Task Format

Tasks are defined in YAML:

```yaml
- id: "task_identifier"
  description: "Task description"
  tags: ["capability", "coding"]
  graders:
    - type: code
      assertions:
        - check: contains
          value: "expected output"
    - type: llm
      assertions:
        - "The code is correct and efficient"
```

Run with: `python main.py --suite coding --trials 2 --show-transcripts`

Note: 0% pass@k typically indicates task misconfiguration rather than agent incapability.

## Variance Analysis

Compare results across different trial counts:

```bash
python main.py --suite coding --trials 1
python main.py --suite coding --trials 5
```

Higher trial counts reveal which tasks have high variance vs consistent behavior.

## Model Configuration

Models are configured in `.env`:
```
AGENT_MODEL=claude-opus-4-5
JUDGE_MODEL=claude-sonnet-4-5
```

Different model combinations can be compared by running the same eval suite with different configurations.

## CLI Reference

```bash
# Run everything
python main.py

# Single suite
python main.py --suite coding
python main.py --suite research
python main.py --suite conversational

# More trials = better metrics
python main.py --trials 5

# Filter by tag
python main.py --tags capability
python main.py --tags regression

# See detailed output
python main.py --show-transcripts

# Different model
python main.py --model claude-haiku-3-5
```

## Extension Possibilities

1. **Production monitoring**: Convert real agent failures into eval tasks
2. **Saturation monitoring**: Track when pass rates exceed 95% (indicates need for harder tasks)
3. **Human calibration**: Verify LLM judge consistency against human judgments
4. **Pairwise comparisons**: Compare pass@k across different models
5. **Partial credit**: Implement weighted grader scoring for multi-component tasks

## Implementation Details

Key patterns from the article implemented here:

- Multiple trials per task (handles non-determinism)
- Fresh agent per trial (isolation, no shared state)
- Three grader types (fast deterministic + nuanced judgment + workflow checks)
- Transcripts saved (post-hoc inspection)
- Balanced problem sets (both positive and negative cases)
- Capability vs regression tagging
- pass@k and pass^k metrics

See code in `evals/harness.py`, `evals/metrics.py`, and `evals/graders/`.

## References

- [Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) - Anthropic Engineering
- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) - Anthropic Engineering
- Benchmarks: SWE-bench Verified, Terminal-Bench, τ-Bench, WebArena, OSWorld
- Frameworks: Harbor, Promptfoo, Braintrust, LangSmith, Langfuse
