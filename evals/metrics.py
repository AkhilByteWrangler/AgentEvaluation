"""
pass@k: probability of ≥1 success in k attempts (optimistic, for tools/coding)
pass^k: probability all k attempts succeed (pessimistic, for customer-facing agents)

Requires multiple trials per task to be meaningful.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from tabulate import tabulate


@dataclass
class TaskMetrics:
    """Aggregated metrics for one task across all trials."""
    task_id: str
    n_trials: int
    n_passed: int            # Trials where ALL graders passed

    # pass@k: P(at least 1 success in k attempts)
    pass_at_1: float
    pass_at_k: float         # Using all n_trials as k

    # pass^k: P(all k attempts succeed)
    pass_hat_1: float
    pass_hat_k: float        # Using all n_trials as k

    avg_score: float         # Mean score across graders and trials
    avg_turns: float
    avg_tokens: float
    avg_latency: float


def pass_at_k(n_trials: int, n_passed: int, k: int) -> float:
    """Probability of ≥1 success in k attempts: 1 - C(n-c, k) / C(n, k)"""
    if n_trials == 0:
        return 0.0
    if k >= n_trials:
        p_trial = n_passed / n_trials
        return 1.0 - (1.0 - p_trial) ** k

    n_failed = n_trials - n_passed
    if n_failed < k:
        return 1.0

    return 1.0 - math.comb(n_failed, k) / math.comb(n_trials, k)


def pass_hat_k(n_trials: int, n_passed: int, k: int) -> float:
    """Probability all k attempts succeed: (n_passed / n_trials) ^ k"""
    if n_trials == 0:
        return 0.0
    p_trial = n_passed / n_trials
    return p_trial ** k


def aggregate_trial_results(task_id: str, trial_results: list[dict]) -> TaskMetrics:
    """Compute pass@k, pass^k, and average metrics across all trials for a task."""
    n = len(trial_results)
    if n == 0:
        return TaskMetrics(task_id, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    passed = [r for r in trial_results if r.get("overall_passed", False)]
    n_passed = len(passed)

    p_at_1 = pass_at_k(n, n_passed, 1)
    p_at_n = pass_at_k(n, n_passed, n)
    p_hat_1 = pass_hat_k(n, n_passed, 1)
    p_hat_n = pass_hat_k(n, n_passed, n)

    scores = [r.get("overall_score", 0.0) for r in trial_results]
    turns = [r.get("n_turns", 0) for r in trial_results]
    tokens = [r.get("n_total_tokens", 0) for r in trial_results]
    latencies = [r.get("latency_seconds", 0.0) for r in trial_results]

    return TaskMetrics(
        task_id=task_id,
        n_trials=n,
        n_passed=n_passed,
        pass_at_1=p_at_1,
        pass_at_k=p_at_n,
        pass_hat_1=p_hat_1,
        pass_hat_k=p_hat_n,
        avg_score=sum(scores) / n,
        avg_turns=sum(turns) / n,
        avg_tokens=sum(tokens) / n,
        avg_latency=sum(latencies) / n,
    )


def summarize_metrics(task_metrics: list[TaskMetrics]) -> str:
    """Produce a table summarizing all tasks in an eval run."""
    if not task_metrics:
        return "No results."

    headers = [
        "Task ID", "Trials", "Passed",
        "pass@1", "pass@k", "pass^1", "pass^k",
        "Avg Score", "Avg Turns", "Avg Tokens",
    ]

    rows = []
    for m in task_metrics:
        rows.append([
            m.task_id,
            m.n_trials,
            m.n_passed,
            f"{m.pass_at_1:.0%}",
            f"{m.pass_at_k:.0%}",
            f"{m.pass_hat_1:.0%}",
            f"{m.pass_hat_k:.0%}",
            f"{m.avg_score:.2f}",
            f"{m.avg_turns:.1f}",
            f"{int(m.avg_tokens)}",
        ])

    return tabulate(rows, headers=headers, tablefmt="rounded_grid")
