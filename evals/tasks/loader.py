"""Load task definitions from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

import config


def load_tasks(yaml_path: str | Path) -> list[dict[str, Any]]:
    """Load tasks from YAML file.
    
    Expects top-level 'tasks:' key with list of task dicts.
    Required fields: id, description, graders
    """
    path = Path(yaml_path)
    if not path.is_absolute():
        path = config.TASKS_DIR / path

    if not path.exists():
        raise FileNotFoundError(f"Task file not found: {path}")

    with path.open() as f:
        data = yaml.safe_load(f)

    tasks = data.get("tasks", [])

    # Validate required fields
    required = {"id", "description", "graders"}
    for i, task in enumerate(tasks):
        missing = required - task.keys()
        if missing:
            raise ValueError(f"Task #{i} in {path.name} missing fields: {missing}")
        if not task["graders"]:
            raise ValueError(f"Task '{task['id']}' has no graders")

    return tasks


def load_suite(suite_name: str) -> list[dict[str, Any]]:
    """Load named suite: maps to tasks/{suite_name}_tasks.yaml."""
    return load_tasks(config.TASKS_DIR / f"{suite_name}_tasks.yaml")
