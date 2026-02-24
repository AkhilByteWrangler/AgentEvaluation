"""Central configuration for AgentEval."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


ROOT_DIR = Path(__file__).parent
RESULTS_DIR = ROOT_DIR / os.getenv("RESULTS_DIR", "results")
TASKS_DIR = ROOT_DIR / "evals" / "tasks"
RUBRICS_DIR = ROOT_DIR / "evals" / "graders" / "rubrics"

RESULTS_DIR.mkdir(exist_ok=True)


ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    raise EnvironmentError("ANTHROPIC_API_KEY is not set. Copy .env.example → .env and add your key.")

AGENT_MODEL: str = os.getenv("AGENT_MODEL")
JUDGE_MODEL: str = os.getenv("JUDGE_MODEL")


LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "agent-eval")
LANGSMITH_ENABLED: bool = bool(LANGSMITH_API_KEY)  

if LANGSMITH_ENABLED:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT


DEFAULT_N_TRIALS: int = 3
EVAL_CONCURRENCY: int = int(os.getenv("EVAL_CONCURRENCY", "5"))
MAX_AGENT_TURNS: int = 20

# Pass/Fail Threshold: trials pass if overall_score >= this value (0.0-1.0)
PASS_THRESHOLD: float = float(os.getenv("PASS_THRESHOLD", "0.7"))
