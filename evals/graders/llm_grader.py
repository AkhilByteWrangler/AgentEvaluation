"""LLM-as-judge grader for nuanced evaluation.

Each assertion is judged in isolation (parallel API calls).
Judge returns: PASS/FAIL/UNKNOWN with score 0.0-1.0 and reasoning.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import anthropic

import config
from agents import AgentResult
from evals.graders.base import BaseGrader, GraderResult


_SYSTEM = """Expert evaluator. Be precise, fair, evidence-based.
Respond ONLY in JSON (no extra text):
{
  "verdict": "PASS" | "FAIL" | "UNKNOWN",
  "score": 0.0-1.0,
  "reasoning": "1-3 sentence explanation"
}
Use UNKNOWN only when insufficient info."""

_PROMPT = """## Task
{task_description}

## Agent Output
{final_answer}

{transcript_section}
{rubric_section}

## Assertion
"{assertion}"

Does the output satisfy this? Respond in JSON only."""


class LLMGrader(BaseGrader):
    """Uses Claude to judge nuanced/subjective criteria."""

    name = "llm"

    def __init__(self, model: str = config.JUDGE_MODEL) -> None:
        self.model = model
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    async def grade(self, result: AgentResult, task: dict[str, Any]) -> GraderResult:
        cfg = self._find_config(task, "llm")
        assertions: list[str] = cfg.get("assertions", [])

        if not assertions:
            return GraderResult(
                grader_name=self.name, passed=True, score=1.0, reason="No LLM assertions"
            )

        # Load rubric
        rubric = ""
        if fname := cfg.get("rubric_file"):
            path = config.RUBRICS_DIR / Path(fname).name
            rubric = path.read_text() if path.exists() else ""

        # Build context
        transcript = ""
        if cfg.get("include_transcript", False):
            lines = [
                f"Turn {tc.turn}: [{tc.tool_name}] {tc.tool_input} → {tc.tool_result[:200]}"
                for tc in result.tool_calls
            ]
            transcript = f"## Transcript\n" + "\n".join(lines) if lines else ""

        rubric_section = f"## Rubric\n{rubric}" if rubric else ""
        output = result.full_output

        # Judge each assertion in parallel
        judgments = await asyncio.gather(
            *[
                self._judge(
                    assertion=a,
                    task_desc=task.get("description", ""),
                    output=output,
                    transcript=transcript,
                    rubric=rubric_section,
                )
                for a in assertions
            ]
        )

        # Aggregate
        results = {}
        total_score = 0.0
        passed = 0

        for assertion, (verdict, score, reasoning) in zip(assertions, judgments):
            is_pass = verdict == "PASS"
            passed += is_pass
            total_score += score
            results[assertion[:80]] = {
                "verdict": verdict,
                "score": score,
                "reasoning": reasoning,
            }

        n = len(assertions)
        avg = total_score / n
        return GraderResult(
            grader_name=self.name,
            passed=passed == n,
            score=avg,
            assertions=results,
            reason=f"{passed}/{n} passed (avg {avg:.2f})",
        )

    async def _judge(
        self,
        assertion: str,
        task_desc: str,
        output: str,
        transcript: str,
        rubric: str,
    ) -> tuple[str, float, str]:
        """Judge single assertion. Returns (verdict, score, reasoning)."""
        prompt = _PROMPT.format(
            task_description=task_desc,
            final_answer=output,
            transcript_section=transcript,
            rubric_section=rubric,
            assertion=assertion,
        )

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=512,
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code blocks if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
            parsed = json.loads(raw)
            verdict = parsed.get("verdict", "UNKNOWN").upper()
            score = float(parsed.get("score", 0.5))
            reasoning = parsed.get("reasoning", "")

            if verdict == "UNKNOWN":
                score = 0.5

            return verdict, score, reasoning
        except Exception as e:
            return "UNKNOWN", 0.5, f"Error: {e}"
