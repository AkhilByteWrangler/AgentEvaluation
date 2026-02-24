# AgentEval

An evaluation harness for testing AI agents before production. Tests output quality, reasoning patterns, and tool usage.

Inspired by Anthropic's ["Demystifying Evals for AI Agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

## What Problem Does This Solve?

Without evals, you find bugs reactively: a user reports an issue, you manually reproduce it, fix it, and hope it works. With evals, you catch failures before deployment by running automated tests that measure agent performance across multiple attempts.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Run a simple evaluation
python main.py --suite coding --trials 3
```

This runs coding tasks 3 times each and shows you pass rates. Results are saved to `results/` with full transcripts.

## How It Works

### 1. Define Tasks (YAML)
Create test cases in `evals/tasks/`. Each task specifies what the agent should do and how to grade it:

```yaml
- id: "fibonacci"
  description: "Write a function to calculate fibonacci numbers"
  tags: ["coding", "capability"]
  graders:
    - type: code
      assertions:
        - check: contains
          value: "fibonacci"
```

### 2. Run Multiple Trials
Agents behave non-deterministically, so we run each task multiple times to measure consistency:

```bash
python main.py --suite coding --trials 5
```

### 3. Grade Results with Three Types of Graders

**CodeGrader** - Fast checks on final output
- Does the output contain specific text?
- Does it match a regex pattern?
- Was a specific tool called?

**LLMGrader** - Nuanced judgment calls
- Is the explanation accurate?
- Is the tone appropriate?
- Does it answer the question?

**TranscriptGrader** - Process validation
- Did the agent use the right tools?
- Did it complete in a reasonable number of turns?
- Did it follow expected workflow?

### 4. Analyze Metrics

Two key metrics tell different stories:

**pass@k** = probability of at least 1 success in k attempts
- Useful for: Coding tasks where you just need one correct solution
- Example: pass@5 = 95% means high capability

**pass^k** = probability that all k attempts succeed  
- Useful for: Production where every interaction must work
- Example: pass^5 = 20% means reliability issues

If pass@5 is high but pass^5 is low, your agent can solve the task but inconsistently.

## Project Structure

```
AgentEval/
├── agents/
│   └── task_agent.py           # The agent being tested
│
├── evals/
│   ├── harness.py              # Test runner
│   ├── metrics.py              # pass@k calculations
│   ├── graders/                # Three grader types
│   │   ├── code_grader.py
│   │   ├── llm_grader.py
│   │   ├── transcript_grader.py
│   │   └── rubrics/            # Criteria for LLM judges
│   └── tasks/                  # Test cases
│       ├── coding_tasks.yaml
│       ├── research_tasks.yaml
│       └── conversational_tasks.yaml
│
├── results/
│   ├── *.json                  # Aggregate results
│   └── transcripts/            # Full agent traces
│
└── main.py                     # Command-line interface
```

## Common Usage Patterns

### Run Specific Test Suites
```bash
python main.py --suite coding
python main.py --suite research
python main.py --suite conversational
```

### Test New vs Existing Features
```bash
# Test new capabilities under development
python main.py --tags capability

# Ensure existing features still work
python main.py --tags regression
```

### Debug Failures
```bash
# See full agent transcripts
python main.py --suite coding --show-transcripts

# Inspect a specific transcript file
cat results/transcripts/code_fibonacci_trial1.json | python -m json.tool
```

Transcripts show:
- Every tool call the agent made
- All reasoning steps
- Whether failures are agent errors or grading issues

### Compare Models
Edit `.env` to test different models:
```bash
AGENT_MODEL=claude-opus-4-5
JUDGE_MODEL=claude-sonnet-4-5
```

Run the same eval suite with different configurations to compare performance.

## Writing Good Tasks

### Balance Positive and Negative Cases
Don't just test "can it use search?" Test both:
- Tasks where search is required
- Tasks where search wastes time

This prevents agents from always calling tools "just in case."

### Tag by Purpose
```yaml
tags: ["capability"]   # New feature, expect low initial scores
tags: ["regression"]   # Stable feature, expect 95%+ scores
```

### Start Simple
If a task has 0% pass rate, it's usually misconfigured. Test that humans can pass it first.

## Key Concepts

### Terminology
- **Task**: One test case (one YAML entry)
- **Trial**: One agent attempt at a task
- **Suite**: Group of related tasks (coding, research, etc.)
- **Transcript**: Full record of an agent run

### Statistical Insight
With 60% per-trial success rate:
- pass@1 = 60%
- pass@5 = 99% (at least one success)
- pass^5 = 8% (all five succeed)

This shows capability exists but consistency doesn't.

## Advanced Features

### Custom Graders
Add your own grading logic in `evals/graders/`:

```python
class CustomGrader(BaseGrader):
    def grade(self, outcome: str, transcript: List) -> GradeResult:
        # Your logic here
        return GradeResult(passed=True, feedback="Looks good")
```

### Production Monitoring
Convert real failures into regression tests:
1. User reports a bug
2. Add it as a task with `tags: ["regression"]`
3. Fix the bug
4. Task now ensures it doesn't regress

### Saturation Detection
When pass@k exceeds 95%, tasks become too easy. Add harder variants to keep improving.

## Command Reference

```bash
# Run everything
python main.py

# Specific suite with more trials
python main.py --suite research --trials 10

# Filter by tags
python main.py --tags capability
python main.py --tags regression

# See agent traces
python main.py --show-transcripts

# Test different model
python main.py --model claude-haiku-3-5
```

## References

- [Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) - Anthropic
- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) - Anthropic
- Eval frameworks: Harbor, Promptfoo, Braintrust, LangSmith
- Agent benchmarks: SWE-bench, Terminal-Bench, WebArena, OSWorld
