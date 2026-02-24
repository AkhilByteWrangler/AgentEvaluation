"""Base grader classes and interfaces.

Three grader types:
  - CodeGrader: deterministic, fast (string/regex/tool checks)
  - LLMGrader: flexible, nuanced (model-as-judge)
  - TranscriptGrader: process evaluation (turns/tokens/tool usage)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agents import AgentResult


@dataclass
class GraderResult:
    """Single grader output for one trial."""
    grader_name: str
    passed: bool
    score: float  # 0.0-1.0
    assertions: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "grader_name": self.grader_name,
            "passed": self.passed,
            "score": self.score,
            "assertions": self.assertions,
            "reason": self.reason,
        }


class BaseGrader(ABC):
    """Grader interface. Subclasses implement grade()."""

    name: str = "base"

    @abstractmethod
    async def grade(self, result: AgentResult, task: dict[str, Any]) -> GraderResult:
        """Grade one trial."""
        ...

    @staticmethod
    def _find_config(task: dict[str, Any], grader_type: str) -> dict[str, Any]:
        """Extract grader config from task dict."""
        return next(
            (g for g in task.get("graders", []) if g.get("type") == grader_type),
            {}
        )
