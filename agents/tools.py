"""Tool implementations.

- search: Mock web search (hits a hardcoded knowledge base)
- calculate: Safe math eval using AST (no arbitrary code execution)
- write_code: Returns markdown-formatted code blocks
- think: No-op, just for logging reasoning in transcripts

dispatch() maps tool names to their implementations.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Callable

from agents.tool_schemas import SCHEMAS


_SEARCH_DB: dict[str, str] = {
    "anthropic opus 4.5 release date": (
        "Claude Opus 4.5 was released on January 15, 2026. Key improvements: "
        "extended 200k context window, improved code generation accuracy by 23%, "
        "reduced latency to 850ms p95 for standard requests."
    ),
    "swe-bench verified 2026 results": (
        "As of February 2026, top scores on SWE-bench Verified: Claude Opus 4.5 at 48.3%, "
        "GPT-5 at 46.1%, Gemini Ultra 2.0 at 44.7%. Baseline pass rate 2024 was 18.2%."
    ),
    "terminal-bench average completion time": (
        "Terminal-bench measures bash workflow completion. Current best: Claude Opus 4.5 "
        "achieves 67% task completion with average 12.4 tool calls per task. "
        "Previous best was 61% at 15.8 calls (GPT-4.5)."
    ),
    "webarena navigation success rate": (
        "WebArena tests web navigation agents. February 2026 benchmarks show 71% success rate "
        "for multi-step e-commerce tasks. Authentication handling remains challenging at 43% success."
    ),
    "tau-bench reasoning chains": (
        "τ-Bench evaluates reasoning chains in scientific problem-solving. "
        "Passing threshold: 85% factual accuracy + valid logic flow. "
        "Current SOTA: 78% (up from 64% in 2024)."
    ),
    "osworld file system operations": (
        "OSWorld benchmarks OS-level task automation. File operations subcategory: "
        "find/grep pipelines 82% success, permission management 67%, "
        "cross-directory batch operations 54%. Updated January 2026."
    ),
    "harbor eval framework pricing": (
        "Harbor pricing (February 2026): Free tier 5k evals/month, "
        "Pro $89/month for 100k evals, Enterprise $890/month for unlimited + SSO. "
        "Includes LLM judge caching and transcript viewer."
    ),
}

_SAFE_OPS: dict[type, Callable] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}

_SAFE_FNS: dict[str, Callable] = {
    "round": round, "abs": abs, "min": min, "max": max, "int": int, "float": float,
}


def _safe_eval(expr: str) -> int | float:
    """Eval math expressions safely via AST traversal."""
    def _eval(node: ast.expr) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp):
            return _SAFE_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return _SAFE_OPS[type(node.op)](_eval(node.operand))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _SAFE_FNS
        ):
            return _SAFE_FNS[node.func.id](*(_eval(a) for a in node.args))
        raise ValueError(f"Unsafe node: {ast.dump(node)}")

    try:
        return _eval(ast.parse(expr, mode="eval").body)
    except (KeyError, ValueError) as e:
        raise ValueError(f"Cannot evaluate '{expr}': {e}") from e


def _search(query: str) -> str:
    """Mock search against hardcoded knowledge base."""
    q = query.lower()
    match = next(
        (v for k, v in _SEARCH_DB.items() if k in q or any(w in q for w in k.split())),
        None,
    )
    prefix = f"Search results for '{query}':\n"
    return prefix + (match if match else "No results found. Use your training knowledge.")


def _calculate(expression: str) -> str:
    """Eval expression, return "expr = result" or error message."""
    try:
        return f"{expression} = {_safe_eval(expression)}"
    except ValueError as e:
        return f"Error: {e}"


def _write_code(language: str, code: str, filename: str = "") -> str:
    """Wrap code in markdown block with optional filename header."""
    header = f"# File: {filename}\n" if filename else ""
    return f"```{language}\n{header}{code}\n```"


_DISPATCH: dict[str, Callable[[dict[str, Any]], str]] = {
    "search":     lambda p: _search(p["query"]),
    "calculate":  lambda p: _calculate(p["expression"]),
    "write_code": lambda p: _write_code(p["language"], p["code"], p.get("filename", "")),
    "think":      lambda _: "Thought recorded.",
}


def dispatch(name: str, params: dict[str, Any]) -> str:
    """Call the right tool with the given params."""
    fn = _DISPATCH.get(name)
    return fn(params) if fn else f"Unknown tool: {name}"

# Re-export for convenience
__all__ = ["dispatch", "SCHEMAS"]
