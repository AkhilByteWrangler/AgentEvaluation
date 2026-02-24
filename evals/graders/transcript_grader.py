"""Process/workflow grader - evaluates how the agent solved the task.

Checks:
  - Turn/token limits (efficiency)
  - Required/forbidden tools (workflow correctness)
  - Think usage (reasoning transparency)

Also collects metrics for reporting.
"""

from __future__ import annotations

from typing import Any

from agents import AgentResult
from evals.graders.base import BaseGrader, GraderResult


class TranscriptGrader(BaseGrader):
    """Grades agent workflow from transcript."""

    name = "transcript"

    async def grade(self, result: AgentResult, task: dict[str, Any]) -> GraderResult:
        cfg = self._find_config(task, "transcript")
        
        # Build efficient tool lookups
        tools_used = {tc.tool_name for tc in result.tool_calls}
        think_count = sum(1 for tc in result.tool_calls if tc.tool_name == "think")
        
        checks: dict[str, dict[str, Any]] = {}
        passed = 0
        
        # Max turns
        if (limit := cfg.get("max_turns")) is not None:
            ok = result.n_turns <= limit
            checks["max_turns"] = {
                "passed": ok,
                "detail": f"{result.n_turns}/{limit} turns",
            }
            passed += ok
        
        # Max tokens
        if (limit := cfg.get("max_tokens")) is not None:
            ok = result.n_total_tokens <= limit
            checks["max_tokens"] = {
                "passed": ok,
                "detail": f"{result.n_total_tokens}/{limit} tokens",
            }
            passed += ok
        
        # Required tools
        for tool in cfg.get("required_tools", []):
            ok = tool in tools_used
            checks[f"req:{tool}"] = {
                "passed": ok,
                "detail": f"'{tool}' {'used' if ok else 'missing'}",
            }
            passed += ok
        
        # Forbidden tools
        for tool in cfg.get("forbidden_tools", []):
            ok = tool not in tools_used
            checks[f"forbid:{tool}"] = {
                "passed": ok,
                "detail": f"'{tool}' {'absent' if ok else 'used'}",
            }
            passed += ok
        
        # Min think calls
        if (min_think := cfg.get("min_think_calls")) is not None:
            ok = think_count >= min_think
            checks["min_think"] = {
                "passed": ok,
                "detail": f"think used {think_count}× (min {min_think})",
            }
            passed += ok
        
        total = len(checks)
        if total == 0:
            return GraderResult(
                grader_name=self.name,
                passed=True,
                score=1.0,
                assertions=_metrics(result),
                reason="No constraints; metrics only",
            )
        
        checks.update(_metrics(result))
        return GraderResult(
            grader_name=self.name,
            passed=passed == total,
            score=passed / total,
            assertions=checks,
            reason=f"{passed}/{total} checks passed",
        )


def _metrics(result: AgentResult) -> dict[str, Any]:
    """Collect metrics for reporting (not graded)."""
    return {
        "_metric:n_turns": result.n_turns,
        "_metric:n_toolcalls": len(result.tool_calls),
        "_metric:n_tokens": result.n_total_tokens,
        "_metric:latency_s": round(result.latency_seconds, 2),
        "_metric:tools": sorted({tc.tool_name for tc in result.tool_calls}),
    }
