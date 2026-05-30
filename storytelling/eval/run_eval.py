"""
Eval harness: run the storytelling pipeline against the test paper corpus.

Usage:
    python storytelling/eval/run_eval.py
    python storytelling/eval/run_eval.py --stage 1          # Stage 1 only
    python storytelling/eval/run_eval.py --paper 2402.03349 # single paper
"""
import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from storytelling import pipeline as st_pipeline

PAPERS_FILE = Path(__file__).parent / "test_papers" / "papers.json"
RUBRIC_FILE = Path(__file__).parent / "rubric.md"
OUTPUTS_DIR = Path(__file__).parent / "outputs"

console = Console()


def load_papers() -> list[dict]:
    return json.loads(PAPERS_FILE.read_text())


def run_single(paper: dict, stage: int | None, output_dir: Path) -> dict:
    arxiv_id = paper["arxiv_id"]
    console.rule(f"[bold]{arxiv_id} — {paper['domain']}")

    paper_out = output_dir / arxiv_id
    paper_out.mkdir(parents=True, exist_ok=True)

    try:
        run = st_pipeline.run(arxiv_id, paper_out, stop_after_stage=stage)
        result = {
            "arxiv_id": arxiv_id,
            "status": "ok",
            "pipeline_status": run.pipeline_status if hasattr(run, "pipeline_status") else "partial",
        }

        if run.essence:
            expected = set(paper.get("expected_difficulty", []))
            actual = set(run.essence.honest_difficulty)
            missed = expected - actual
            result["difficulty_flags_match"] = not bool(missed)
            result["difficulty_missed"] = list(missed)
            console.print(f"honest_difficulty: {run.essence.honest_difficulty}")
            if missed:
                console.print(f"[yellow]MISSED expected flags: {missed}[/yellow]")

        if run.final_pitch:
            console.print(Panel(run.final_pitch[:600] + "…", title="final_pitch (truncated)"))

    except Exception as e:
        console.print(f"[red]ERROR: {e}[/red]")
        result = {"arxiv_id": arxiv_id, "status": "error", "error": str(e)}

    return result


def print_summary(results: list[dict]) -> None:
    table = Table(title="Eval Summary")
    table.add_column("Paper")
    table.add_column("Status")
    table.add_column("Difficulty flags match")
    table.add_column("Pipeline status")

    for r in results:
        table.add_row(
            r["arxiv_id"],
            r["status"],
            "✓" if r.get("difficulty_flags_match") else ("✗" if "difficulty_flags_match" in r else "—"),
            r.get("pipeline_status", "—"),
        )

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, default=None, help="Stop after this stage (1-4)")
    parser.add_argument("--paper", type=str, default=None, help="Run single paper by arXiv ID")
    args = parser.parse_args()

    papers = load_papers()
    if args.paper:
        papers = [p for p in papers if p["arxiv_id"] == args.paper]
        if not papers:
            console.print(f"[red]Paper {args.paper} not found in test corpus.[/red]")
            sys.exit(1)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    results = [run_single(p, args.stage, OUTPUTS_DIR) for p in papers]
    print_summary(results)


if __name__ == "__main__":
    main()
