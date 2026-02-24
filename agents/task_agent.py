"""TaskAgent: runs tasks using Claude with tool calling.

Multi-turn loop where the agent can call tools (search, calculate, write_code, think)
until it produces a final answer or hits the turn limit.
"""

from __future__ import annotations

import asyncio
import time

import anthropic

import config
from agents.types import AgentResult, ToolCall
from agents.tools import dispatch
from agents.tool_schemas import SCHEMAS


# System prompt - tells the agent when to use tools
_SYSTEM_PROMPT = (
    "You are a capable AI assistant that solves tasks step by step.\n"
    "- Use `think` before acting on complex problems.\n"
    "- Use `search` when you need factual information you're not certain about.\n"
    "- Use `calculate` for any math.\n"
    "- Use `write_code` when asked to produce code.\n"
    "- State assumptions when a task is ambiguous."
)


class TaskAgent:
    """Runs tasks using Claude + tools. Tracks tokens, latency, turn count."""
    def __init__(self, model: str = config.AGENT_MODEL) -> None:
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._model = model

    async def run(self, task_id: str, instruction: str, trial_number: int = 1) -> AgentResult:
        """Run one trial of a task. Returns AgentResult with answer and metrics."""
        start = time.perf_counter()
        messages: list[dict] = [{"role": "user", "content": instruction}]
        tool_calls: list[ToolCall] = []
        total_tokens = 0
        final_answer = ""
        turn = 0
        error: str | None = None

        try:
            while turn < config.MAX_AGENT_TURNS:
                turn += 1
                # Call the Anthropic API with tool schemas
                response = await asyncio.to_thread(
                    self._client.messages.create,
                    model=self._model,
                    max_tokens=4096,
                    system=_SYSTEM_PROMPT,
                    tools=SCHEMAS,
                    messages=messages,
                )
                total_tokens += response.usage.input_tokens + response.usage.output_tokens

                # Parse response content and extract tool calls
                content: list[dict] = []
                tool_uses: list = []
                for block in response.content:
                    if block.type == "text":
                        final_answer = block.text
                        content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                        tool_uses.append(block)

                messages.append({"role": "assistant", "content": content})

                # If no tools were called or conversation ended, we're done
                if not tool_uses or response.stop_reason == "end_turn":
                    break

                # Execute all tool calls and collect results
                tool_results: list[dict] = []
                for block in tool_uses:
                    out = dispatch(block.name, block.input)
                    tool_calls.append(ToolCall(turn, block.name, dict(block.input), out))
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})

                messages.append({"role": "user", "content": tool_results})

        except Exception as e:
            error = str(e)

        return AgentResult(
            task_id=task_id,
            trial_number=trial_number,
            final_answer=final_answer,
            messages=messages,
            tool_calls=tool_calls,
            n_turns=turn,
            n_total_tokens=total_tokens,
            latency_seconds=time.perf_counter() - start,
            error=error,
        )


__all__ = ["TaskAgent"]
