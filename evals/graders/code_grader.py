"""Deterministic code-based grader.

Supported checks:
  - contains/not_contains: substring matching
  - regex: pattern matching
  - python_assert: eval expressions against result
  - tool_was_called/tool_was_not_called: tool usage
  - tool_param_check: tool param validation
  - code_block_present: markdown fence check
"""

from __future__ import annotations

import re
from typing import Any

from agents import AgentResult, ToolCall
from evals.graders.base import BaseGrader, GraderResult


class CodeGrader(BaseGrader):
    """Fast, deterministic rule-based grader."""

    name = "code"

    async def grade(self, result: AgentResult, task: dict[str, Any]) -> GraderResult:
        cfg = self._find_config(task, "code")
        assertions: list[dict[str, Any]] = cfg.get("assertions", [])

        if not assertions:
            return GraderResult(
                grader_name=self.name,
                passed=True,
                score=1.0,
                reason="No code assertions configured.",
            )

        # Build efficient lookup structures once (O(1) access)
        tool_index = _build_tool_index(result.tool_calls)
        full_output = result.full_output

        results = {}
        passed = 0

        for a in assertions:
            check = a.get("check", "")
            label = a.get("label", check)
            try:
                success, detail = self._check(
                    check, a, result, full_output, tool_index
                )
            except Exception as e:
                success, detail = False, f"Exception: {e}"

            results[label] = {"passed": success, "detail": detail}
            passed += success

        total = len(assertions)
        return GraderResult(
            grader_name=self.name,
            passed=passed == total,
            score=passed / total,
            assertions=results,
            reason=f"{passed}/{total} passed",
        )

    def _check(
        self,
        check: str,
        cfg: dict[str, Any],
        result: AgentResult,
        full_output: str,
        tool_index: dict[str, Any],
    ) -> tuple[bool, str]:
        """Run single assertion check."""
        text = full_output.lower()

        if check == "contains":
            val = cfg["value"].lower()
            found = val in text
            return found, f"'{cfg['value']}' {'found' if found else 'missing'}"

        if check == "not_contains":
            val = cfg["value"].lower()
            absent = val not in result.final_answer.lower()
            return absent, f"'{cfg['value']}' {'absent' if absent else 'present'}"

        if check == "regex":
            pattern = cfg["pattern"]
            match = bool(re.search(pattern, full_output, re.IGNORECASE))
            return match, f"/{pattern}/ {'matched' if match else 'no match'}"

        if check == "python_assert":
            expr = cfg["expr"]
            local = {"result": result}
            passes = bool(eval(expr, {"__builtins__": {}}, local))  # noqa: S307
            return passes, f"{expr} → {passes}"

        if check == "tool_was_called":
            tool = cfg["tool"]
            used = tool in tool_index["names"]
            return used, f"'{tool}' {'used' if used else 'not used'}"

        if check == "tool_was_not_called":
            tool = cfg["tool"]
            unused = tool not in tool_index["names"]
            return unused, f"'{tool}' {'not used' if unused else 'used'}"

        if check == "tool_param_check":
            tool = cfg["tool"]
            param = cfg["param"]
            substring = cfg.get("contains", "").lower()
            # O(1) lookup via index
            for call in tool_index["by_name"].get(tool, []):
                val = str(call.tool_input.get(param, "")).lower()
                if substring in val:
                    return True, f"'{tool}'.{param} contains '{substring}'"
            return False, f"'{tool}'.{param} missing '{substring}'"

        if check == "code_block_present":
            has_block = "```" in full_output
            return has_block, f"code block {'present' if has_block else 'missing'}"

        return False, f"Unknown check: '{check}'"


def _build_tool_index(calls: list[ToolCall]) -> dict[str, Any]:
    """Build O(1) lookup structures for tool checks."""
    by_name: dict[str, list[ToolCall]] = {}
    for call in calls:
        by_name.setdefault(call.tool_name, []).append(call)
    return {"names": set(by_name.keys()), "by_name": by_name}
