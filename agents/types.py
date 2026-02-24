"""Core data types for agent execution.

- ToolCall: One tool invocation (what was called, what it returned)
- AgentResult: Full run record (answer, metrics, transcript, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    """One tool call. Tracks turn number, tool name, input params, and output."""
    turn: int
    tool_name: str
    tool_input: dict[str, Any]
    tool_result: str


@dataclass
class AgentResult:
    """Full execution record for one trial of a task.
    
    Captures answer, conversation transcript, tool usage, performance metrics, errors.
    """
    task_id: str
    trial_number: int
    final_answer: str
    messages: list[dict]
    tool_calls: list[ToolCall]
    n_turns: int
    n_total_tokens: int
    latency_seconds: float
    error: str | None = None

    @property
    def full_output(self) -> str:
        """Join all tool outputs + final answer. Useful for grading."""
        parts = [tc.tool_result for tc in self.tool_calls]
        if self.final_answer:
            parts.append(self.final_answer)
        return "\n".join(parts)


__all__ = ["ToolCall", "AgentResult"]
