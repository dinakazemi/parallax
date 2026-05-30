"""
Storytelling pipeline orchestrator.

Usage:
    python -m storytelling.pipeline 2401.00001
    python -m storytelling.pipeline path/to/paper.pdf
    python -m storytelling.pipeline 2401.00001 --output outputs/my_run
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

# Allow running as __main__ from repo root
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))
load_dotenv(_REPO_ROOT / ".env")

from src.ingestion.arxiv_fetcher import fetch_arxiv
from src.ingestion.pdf_parser import parse_pdf
from src.models import PaperContent
from storytelling.models import Concept, Essence, PipelineRun
from storytelling.stages.concept import develop_concept
from storytelling.stages.critique import critique_and_revise
from storytelling.stages.essence import extract_essence
from storytelling.stages.pitch import write_pitch
from storytelling.validation import validate_concept, validate_critique, validate_essence

console = Console()

_CACHE_ROOT = _REPO_ROOT / ".cache" / "storytelling"
_MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------

def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# Stage 1 cache key includes prompt + schema so any edit auto-invalidates.
_STAGE1_PROMPT_HASH = _md5(
    (_REPO_ROOT / "storytelling" / "prompts" / "stage1_essence.txt").read_text()
    + (_REPO_ROOT / "storytelling" / "schemas" / "essence_schema.json").read_text()
)


def _cache_path(stage: str, key: str, ext: str = "json") -> Path:
    p = _CACHE_ROOT / stage / f"{key}.{ext}"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_cache(stage: str, key: str, ext: str = "json") -> Optional[str]:
    p = _cache_path(stage, key, ext)
    return p.read_text() if p.exists() else None


def _save_cache(stage: str, key: str, text: str, ext: str = "json") -> None:
    _cache_path(stage, key, ext).write_text(text)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

_ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def _looks_like_arxiv(source: str) -> bool:
    s = source.strip()
    if _ARXIV_RE.match(s):
        return True
    return "arxiv.org" in s


def _ingest(source: str) -> PaperContent:
    if _looks_like_arxiv(source):
        arxiv_id = source.strip().split("/")[-1]
        console.print(f"[dim]Fetching arXiv:{arxiv_id}…[/dim]")
        return fetch_arxiv(arxiv_id)
    console.print(f"[dim]Parsing PDF: {source}…[/dim]")
    return parse_pdf(source)


# ---------------------------------------------------------------------------
# Stage runners with cache
# ---------------------------------------------------------------------------

def _run_stage1(paper: PaperContent) -> Essence:
    key = _md5(paper.body + _STAGE1_PROMPT_HASH)
    cached = _load_cache("stage1", key)
    if cached:
        console.print("[dim]Stage 1: cache hit[/dim]")
        return Essence(**json.loads(cached))

    console.print("[bold cyan]Stage 1:[/bold cyan] Extracting essence…")
    essence = extract_essence(paper)
    _save_cache("stage1", key, essence.model_dump_json())
    return essence


def _run_stage2(essence: Essence, critic_notes: Optional[str] = None) -> Concept:
    cache_input = essence.model_dump_json() + (critic_notes or "")
    key = _md5(cache_input)
    cached = _load_cache("stage2", key)
    if cached and not critic_notes:
        console.print("[dim]Stage 2: cache hit[/dim]")
        return Concept(**json.loads(cached))

    label = "Stage 2 (retry)" if critic_notes else "Stage 2"
    console.print(f"[bold cyan]{label}:[/bold cyan] Developing concept…")
    concept = develop_concept(essence, critic_notes)
    _save_cache("stage2", key, concept.model_dump_json())
    return concept


def _run_stage3(concept: Concept, essence: Essence) -> str:
    key = _md5(concept.model_dump_json())
    cached = _load_cache("stage3", key, ext="md")
    if cached:
        console.print("[dim]Stage 3: cache hit[/dim]")
        return cached

    console.print("[bold cyan]Stage 3:[/bold cyan] Writing pitch…")
    pitch = write_pitch(concept, essence)
    _save_cache("stage3", key, pitch, ext="md")
    return pitch


# ---------------------------------------------------------------------------
# Main run function
# ---------------------------------------------------------------------------

def run(
    source: str,
    output_dir: Optional[Path] = None,
    stop_after_stage: Optional[int] = None,
) -> PipelineRun:
    """Run the full storytelling pipeline.

    Args:
        source: arXiv ID, arXiv URL, or local PDF path.
        output_dir: Where to write outputs. Defaults to outputs/storytelling/<paper_id>.
        stop_after_stage: If set, stop and return a partial PipelineRun after this stage (1-4).
    """
    paper = _ingest(source)

    if output_dir is None:
        safe_id = re.sub(r"[^\w\-]", "_", paper.source)
        output_dir = _REPO_ROOT / "outputs" / "storytelling" / safe_id
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.rule(f"[bold]{paper.title[:80]}")

    # Stage 1
    essence = _run_stage1(paper)
    (output_dir / "essence.json").write_text(essence.model_dump_json(indent=2))
    for issue in validate_essence(essence):
        console.print(f"[yellow]⚠  Stage 1: {issue}[/yellow]")

    if stop_after_stage == 1:
        return PipelineRun(paper=paper, essence=essence)

    # Stage 2
    concept = _run_stage2(essence)
    (output_dir / "concept.json").write_text(concept.model_dump_json(indent=2))
    for issue in validate_concept(concept, essence):
        console.print(f"[yellow]⚠  Stage 2: {issue}[/yellow]")

    if stop_after_stage == 2:
        return PipelineRun(paper=paper, essence=essence, concept=concept)

    # Stage 3
    pitch = _run_stage3(concept, essence)
    (output_dir / "pitch.md").write_text(pitch)

    if stop_after_stage == 3:
        return PipelineRun(paper=paper, essence=essence, concept=concept, pitch=pitch, final_pitch=pitch)

    # Stage 4 with retry loop
    retry_count = 0
    current_concept = concept
    current_pitch = pitch

    while True:
        console.print("[bold cyan]Stage 4:[/bold cyan] Critique & revise…")
        critique = critique_and_revise(current_pitch, current_concept, essence)
        (output_dir / "critique.json").write_text(critique.model_dump_json(indent=2))

        console.print(f"[bold]Verdict:[/bold] {critique.verdict}")
        for issue in validate_critique(critique):
            console.print(f"[yellow]⚠  Stage 4: {issue}[/yellow]")

        if critique.verdict == "PASS":
            final_pitch = current_pitch
            status = "completed"
            break

        if critique.verdict == "REVISE":
            final_pitch = critique.revised_pitch or current_pitch
            status = "completed"
            break

        # RECONSIDER
        retry_count += 1
        if retry_count > _MAX_RETRIES:
            console.print(
                f"[yellow]Max retries ({_MAX_RETRIES}) reached. "
                "Surfacing best attempt with critic notes.[/yellow]"
            )
            final_pitch = current_pitch
            status = "max_retries_reached"
            break

        console.print(
            f"[yellow]RECONSIDER (attempt {retry_count}/{_MAX_RETRIES}):[/yellow] "
            f"{critique.reconsider_direction}"
        )
        current_concept = _run_stage2(essence, critic_notes=critique.reconsider_direction)
        (output_dir / f"concept_retry{retry_count}.json").write_text(
            current_concept.model_dump_json(indent=2)
        )
        current_pitch = _run_stage3(current_concept, essence)
        (output_dir / f"pitch_retry{retry_count}.md").write_text(current_pitch)

    (output_dir / "final_pitch.md").write_text(final_pitch)

    result = PipelineRun(
        paper=paper,
        essence=essence,
        concept=current_concept,
        pitch=current_pitch,
        critique=critique,
        final_pitch=final_pitch,
        pipeline_status=status,
        retry_count=retry_count,
    )

    _display_result(result, output_dir)
    return result


# ---------------------------------------------------------------------------
# Rich display
# ---------------------------------------------------------------------------

def _display_result(result: PipelineRun, output_dir: Path) -> None:
    console.print()
    console.rule("[bold green]Final Pitch")
    console.print(result.final_pitch)

    if result.pipeline_status == "max_retries_reached":
        console.print()
        console.print(Panel(
            f"[yellow]Max retries reached. Critic's final notes attached.[/yellow]\n\n"
            f"{result.critique.model_dump_json(indent=2)}",
            title="Critic Notes",
        ))

    console.print()
    console.print(f"[dim]Outputs written to: {output_dir}[/dim]")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parallax Storytelling Engine")
    parser.add_argument("source", help="arXiv ID, arXiv URL, or local PDF path")
    parser.add_argument("--output", help="Output directory", default=None)
    parser.add_argument(
        "--stage", type=int, default=None,
        help="Stop after this stage (1-4) for debugging"
    )
    args = parser.parse_args()

    run(
        source=args.source,
        output_dir=Path(args.output) if args.output else None,
        stop_after_stage=args.stage,
    )
