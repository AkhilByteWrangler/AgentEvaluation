"""
Evaluation harness: runs tasks concurrently, grades results, computes pass@k metrics.
Each trial uses a fresh agent (isolated state). Transcripts saved to results/.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import print as rprint

import config
from agents import TaskAgent, AgentResult
from evals.graders.code_grader import CodeGrader
from evals.graders.llm_grader import LLMGrader
from evals.graders.transcript_grader import TranscriptGrader
from evals.metrics import aggregate_trial_results, summarize_metrics, TaskMetrics

console = Console()


@dataclass
class TrialResult:
    """Complete graded record for one trial (agent run + all grader results)."""
    task_id: str
    trial_number: int
    overall_passed: bool
    overall_score: float           # 0.0–1.0 weighted across all graders
    grader_results: list[dict]     # One GraderResult.to_dict() per grader
    transcript: list[dict]         # Full messages array (the agent's trace)
    tool_calls: list[dict]         # Structured tool call log
    n_turns: int
    n_total_tokens: int
    latency_seconds: float
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "trial_number": self.trial_number,
            "overall_passed": self.overall_passed,
            "overall_score": self.overall_score,
            "grader_results": self.grader_results,
            "n_turns": self.n_turns,
            "n_total_tokens": self.n_total_tokens,
            "latency_seconds": self.latency_seconds,
            "error": self.error,
        }


@dataclass
class TaskResult:
    """All trials for one task, plus aggregated metrics."""
    task: dict                          # Raw task config from YAML
    trials: list[TrialResult] = field(default_factory=list)
    metrics: TaskMetrics | None = None


@dataclass
class EvalReport:
    """Final report from one complete eval run."""
    suite_name: str
    run_id: str
    started_at: str
    finished_at: str
    task_results: list[TaskResult]
    summary_table: str              # Rendered text table

    def to_dict(self) -> dict:
        return {
            "suite_name": self.suite_name,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "tasks": [
                {
                    "task_id": tr.task["id"],
                    "metrics": {
                        "n_trials": tr.metrics.n_trials if tr.metrics else 0,
                        "n_passed": tr.metrics.n_passed if tr.metrics else 0,
                        "pass_at_1": tr.metrics.pass_at_1 if tr.metrics else 0.0,
                        "pass_hat_k": tr.metrics.pass_hat_k if tr.metrics else 0.0,
                    },
                    "trials": [t.to_dict() for t in tr.trials],
                }
                for tr in self.task_results
            ],
        }


class EvalHarness:
    """Runs eval suites: executes tasks with n_trials each, grades, computes metrics."""

    def __init__(self, agent_model: str = config.AGENT_MODEL):
        self.agent_model = agent_model
        self.graders = {
            "code": CodeGrader(),
            "llm": LLMGrader(),
            "transcript": TranscriptGrader(),
        }
        self._semaphore = asyncio.Semaphore(config.EVAL_CONCURRENCY)

    async def run_suite(
        self,
        tasks: list[dict],
        suite_name: str = "eval",
        n_trials: int = config.DEFAULT_N_TRIALS,
    ) -> EvalReport:
        """Run all tasks (n_trials each) concurrently, grade, aggregate metrics."""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        started_at = datetime.now().isoformat()

        console.print(Panel(
            f"[bold cyan]AgentEval Harness[/]\n"
            f"Suite: [bold]{suite_name}[/]  |  Tasks: {len(tasks)}  |  "
            f"Trials/task: {n_trials}  |  Run ID: {run_id}",
            border_style="cyan",
        ))

        task_results: list[TaskResult] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            total_trials = len(tasks) * n_trials
            prog_task = progress.add_task("[cyan]Running trials...", total=total_trials)

            task_coros = [
                self._run_task_all_trials(task, n_trials, progress, prog_task)
                for task in tasks
            ]
            task_results = await asyncio.gather(*task_coros)

        all_metrics: list[TaskMetrics] = []
        for tr in task_results:
            trial_dicts = [t.to_dict() for t in tr.trials]
            tr.metrics = aggregate_trial_results(tr.task["id"], trial_dicts)
            all_metrics.append(tr.metrics)

        finished_at = datetime.now().isoformat()
        summary = summarize_metrics(all_metrics)

        report = EvalReport(
            suite_name=suite_name,
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            task_results=task_results,
            summary_table=summary,
        )

        self._save_report(report)

        return report

    def print_report(self, report: EvalReport, show_transcripts: bool = False) -> None:
        """Print summary table. Set show_transcripts=True to see tool calls per trial."""
        console.print("\n")
        console.print(Panel(
            f"[bold green]Eval Complete[/]  |  Run: {report.run_id}\n"
            f"Suite: {report.suite_name}  |  "
            f"Finished: {report.finished_at}",
            border_style="green",
        ))

        console.print("\n[bold]Summary:[/]")
        console.print(report.summary_table)

        if show_transcripts:
            for task_result in report.task_results:
                self._print_task_detail(task_result)

    async def _run_task_all_trials(
        self,
        task: dict,
        n_trials: int,
        progress: Progress,
        prog_task,
    ) -> TaskResult:
        """Run n_trials for one task sequentially (isolated environments)."""
        task_result = TaskResult(task=task)

        for trial_num in range(1, n_trials + 1):
            async with self._semaphore:
                trial = await self._run_single_trial(task, trial_num)
                task_result.trials.append(trial)
                progress.advance(prog_task)

        return task_result

    async def _run_single_trial(self, task: dict, trial_number: int) -> TrialResult:
        """Run one trial: fresh agent → grade → record. Isolation via fresh TaskAgent."""
        agent = TaskAgent(model=self.agent_model)

        agent_result: AgentResult = await agent.run(
            task_id=task["id"],
            instruction=task.get("instruction", task.get("description", "")),
            trial_number=trial_number,
        )

        grader_types_in_task = {g["type"] for g in task.get("graders", [])}

        grader_results = []
        all_passed = True
        total_score = 0.0
        n_graders = 0

        for gtype, grader in self.graders.items():
            if gtype not in grader_types_in_task:
                continue
            try:
                gresult = await grader.grade(agent_result, task)
                grader_results.append(gresult.to_dict())
                if not gresult.passed:
                    all_passed = False
                total_score += gresult.score
                n_graders += 1
            except Exception as e:
                grader_results.append({
                    "grader_name": gtype,
                    "passed": False,
                    "score": 0.0,
                    "reason": f"Grader raised exception: {e}",
                })
                all_passed = False
                n_graders += 1

        if agent_result.error:
            all_passed = False

        overall_score = total_score / n_graders if n_graders > 0 else 0.0

        self._save_transcript(task["id"], trial_number, agent_result)

        return TrialResult(
            task_id=task["id"],
            trial_number=trial_number,
            overall_passed=all_passed,
            overall_score=overall_score,
            grader_results=grader_results,
            transcript=agent_result.messages,
            tool_calls=[
                {
                    "turn": tc.turn,
                    "tool": tc.tool_name,
                    "input": tc.tool_input,
                    "result_preview": tc.tool_result[:200],
                }
                for tc in agent_result.tool_calls
            ],
            n_turns=agent_result.n_turns,
            n_total_tokens=agent_result.n_total_tokens,
            latency_seconds=agent_result.latency_seconds,
            error=agent_result.error,
        )

    def _save_report(self, report: EvalReport) -> None:
        out_path = config.RESULTS_DIR / f"{report.suite_name}_{report.run_id}.json"
        out_path.write_text(json.dumps(report.to_dict(), indent=2))
        console.print(f"\n[dim]Report saved → {out_path}[/]")

    @staticmethod
    def _save_transcript(task_id: str, trial_num: int, result: AgentResult) -> None:
        """Save full transcript to results/transcripts/ for post-hoc inspection."""
        transcripts_dir = config.RESULTS_DIR / "transcripts"
        transcripts_dir.mkdir(exist_ok=True)
        path = transcripts_dir / f"{task_id}_trial{trial_num}.json"
        path.write_text(json.dumps({
            "task_id": task_id,
            "trial_number": trial_num,
            "messages": result.messages,
            "tool_calls": [
                {
                    "turn": tc.turn,
                    "tool": tc.tool_name,
                    "input": tc.tool_input,
                    "result": tc.tool_result,
                }
                for tc in result.tool_calls
            ],
            "n_turns": result.n_turns,
            "n_total_tokens": result.n_total_tokens,
            "latency_seconds": result.latency_seconds,
        }, indent=2))

    def _print_task_detail(self, task_result: TaskResult) -> None:
        task_id = task_result.task["id"]
        console.print(f"\n[bold yellow]Task: {task_id}[/]")

        for trial in task_result.trials:
            status = "PASS" if trial.overall_passed else "FAIL"
            console.print(
                f"  Trial {trial.trial_number}: {status}  "
                f"score={trial.overall_score:.2f}  "
                f"turns={trial.n_turns}  tokens={trial.n_total_tokens}"
            )
            for tc in trial.tool_calls:
                console.print(
                    f"    [dim]↳ [{tc['tool']}] {str(tc['input'])[:80]}[/]"
                )
            for gr in trial.grader_results:
                status = "PASS" if gr.get("passed") else "FAIL"
                console.print(
                    f"    {status} [{gr['grader_name']}] score={gr.get('score', 0):.2f} "
                    f"— {gr.get('reason', '')}"
                )
