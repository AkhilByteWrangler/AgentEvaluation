"""Tool schemas passed to the Anthropic API.

Defines what tools are available to the agent (search, calculate, write_code, think).
Follows Anthropic's tool use format: name, description, input_schema.
"""

from __future__ import annotations


# Tool schemas sent to the API - tells the model what tools it can use
SCHEMAS: list[dict] = [
    {
        "name": "search",
        "description": "Search the web for factual information.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    {
        "name": "calculate",
        "description": (
            "Evaluate a math expression. Supports +, -, *, /, **, %, "
            "and round(), abs(), min(), max(), int(), float()."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "Python math expression"}},
            "required": ["expression"],
        },
    },
    {
        "name": "write_code",
        "description": "Write and return a formatted code snippet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "language": {"type": "string"},
                "code":     {"type": "string"},
                "filename": {"type": "string"},
            },
            "required": ["language", "code"],
        },
    },
    {
        "name": "think",
        "description": "Record internal reasoning before acting. Captured in transcript.",
        "input_schema": {
            "type": "object",
            "properties": {"thought": {"type": "string"}},
            "required": ["thought"],
        },
    },
]

__all__ = ["SCHEMAS"]
