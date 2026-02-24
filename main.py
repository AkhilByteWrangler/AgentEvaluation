"""Entry point for AgentEval CLI."""

import argparse
import asyncio

from rich.console import Console
from rich.rule import Rule

import config
from evals.harness import EvalHarness
from evals.tasks.loader import load_suite, load_tasks

console = Console()

AVAILABLE_SUITES = ["coding", "research", "conversational"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AgentEval — Evaluate AI Agent Thinking, Workflow, and Output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--suite",
        choices=AVAILABLE_SUITES + ["all"],
        default="all",
        help="Which eval suite to run (default: all)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=config.DEFAULT_N_TRIALS,
        help=f"Number of trials per task (default: {config.DEFAULT_N_TRIALS})",
    )
    parser.add_argument(
        "--model",
        default=config.AGENT_MODEL,
        help=f"Agent model (default: {config.AGENT_MODEL})",
    )
    parser.add_argument(
        "--show-transcripts",
        action="store_true",
        help="Print per-trial tool-call detail",
    )
    parser.add_argument(
        "--tags",
        nargs="*",
        help="Only run tasks with these tags (e.g. --tags capability regression)",
    )
    return parser.parse_args()


def filter_by_tags(tasks: list[dict], tags: list[str] | None) -> list[dict]:
    """Filter tasks by tag."""
    if not tags:
        return tasks
    return [t for t in tasks if any(tag in t.get("tags", []) for tag in tags)]


async def run(args: argparse.Namespace) -> None:
    harness = EvalHarness(agent_model=args.model)

    suites_to_run = AVAILABLE_SUITES if args.suite == "all" else [args.suite]

    for suite_name in suites_to_run:
        console.print(Rule(f"[bold cyan] Suite: {suite_name} [/]", style="cyan"))

        tasks = load_suite(suite_name)
        tasks = filter_by_tags(tasks, args.tags)

        if not tasks:
            console.print(f"[yellow]No tasks found for suite '{suite_name}' with given filters.[/]")
            continue

        console.print(
            f"[dim]Loaded {len(tasks)} tasks  |  "
            f"{args.trials} trials each  |  "
            f"model: {args.model}[/]\n"
        )

        report = await harness.run_suite(
            tasks=tasks,
            suite_name=suite_name,
            n_trials=args.trials,
        )

        harness.print_report(report, show_transcripts=args.show_transcripts)


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
