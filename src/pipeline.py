import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich import print as rprint

from src.models import (
    PaperContent, PipelineResult,
    IMAGE_MODELS, VIDEO_MODELS,
)
from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.arxiv_fetcher import fetch_arxiv
from src.agents.science_comprehension import extract_science_brief
from src.agents.creative_director import generate_cinematic_concept
from src.generation.image_generator import generate_images
from src.generation.video_generator import generate_videos
from src.selection.image_selector import select_images_interactive, select_images_auto

load_dotenv()
console = Console()


def run(
    source: str,
    output_dir: Path,
    num_images: int = 4,
    video_duration: int = 5,
    auto: bool = False,
) -> PipelineResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Ingest ────────────────────────────────────────────────────────
    paper = _ingest(source)
    console.print(Panel(
        f"[bold]{paper.title}[/bold]\n\n[dim]{paper.abstract[:400]}...[/dim]",
        title="[green]Paper Ingested[/green]",
        expand=False,
    ))

    # ── Step 2: Science comprehension ─────────────────────────────────────────
    with console.status("[bold cyan]Extracting scientific essence...[/bold cyan]"):
        brief = extract_science_brief(paper)

    console.print(Panel(
        f"[bold]Essence:[/bold] {brief.one_line_essence}\n\n"
        f"[bold]Phenomenon:[/bold] {brief.core_phenomenon}\n\n"
        f"[bold]Tones:[/bold] {', '.join(t.value for t in brief.emotional_tones)}",
        title="[green]Science Brief[/green]",
        expand=False,
    ))

    # ── Step 3: Creative direction ────────────────────────────────────────────
    with console.status("[bold cyan]Generating cinematic concept...[/bold cyan]"):
        concept = generate_cinematic_concept(brief)

    console.print(Panel(
        f"[bold]Logline:[/bold] {concept.logline}\n\n"
        f"[bold]Scene:[/bold] {concept.scene_description}\n\n"
        f"[bold]References:[/bold] {', '.join(concept.film_references)}",
        title="[green]Cinematic Concept[/green]",
        expand=False,
    ))

    # ── Step 4: Choose image model ────────────────────────────────────────────
    image_model = _choose_model("image generation", IMAGE_MODELS, auto)

    # ── Step 5: Generate images ───────────────────────────────────────────────
    console.print(f"\n[bold cyan]Generating {num_images} images with {image_model}...[/bold cyan]")
    with console.status(f"[dim]This may take a minute...[/dim]"):
        images = generate_images(concept, output_dir, model=image_model, num_images=num_images)

    console.print(f"[green]✓ {len(images)} images saved to {output_dir}[/green]")

    # ── Step 6: Image selection ───────────────────────────────────────────────
    if auto:
        selected = select_images_auto(images)
    else:
        selected = select_images_interactive(images)

    console.print(f"[green]✓ {len(selected)} image(s) selected for video generation[/green]")

    # ── Step 7: Choose video model ────────────────────────────────────────────
    video_model = _choose_model("video generation", VIDEO_MODELS, auto)

    # ── Step 8: Generate videos ───────────────────────────────────────────────
    console.print(f"\n[bold cyan]Generating video clips with {video_model}...[/bold cyan]")
    with console.status(f"[dim]Generating {len(selected)} clip(s), {video_duration}s each...[/dim]"):
        videos = generate_videos(selected, concept, output_dir, model=video_model, duration=video_duration)

    console.print(f"[green]✓ {len(videos)} video(s) saved to {output_dir}[/green]")
    for v in videos:
        console.print(f"  [dim]{v.local_path}[/dim]")

    return PipelineResult(
        paper_title=paper.title,
        paper_source=paper.source,
        science_brief=brief,
        cinematic_concept=concept,
        generated_images=images,
        selected_images=selected,
        videos=videos,
    )


def _ingest(source: str) -> PaperContent:
    # ArXiv ID patterns: "2301.07658", "arxiv:2301.07658", arxiv URLs
    if _looks_like_arxiv(source):
        with console.status("[bold cyan]Fetching from ArXiv...[/bold cyan]"):
            return fetch_arxiv(source)
    else:
        with console.status("[bold cyan]Parsing PDF...[/bold cyan]"):
            return parse_pdf(source)


def _looks_like_arxiv(source: str) -> bool:
    import re
    source = source.strip()
    return bool(
        re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", source)
        or source.lower().startswith("arxiv:")
        or "arxiv.org" in source
    )


def _choose_model(stage: str, models: dict[str, str], auto: bool) -> str:
    default = next(iter(models))
    if auto or len(models) == 1:
        return default

    console.print(f"\n[bold]Select model for {stage}:[/bold]")
    choices = list(models.items())
    for i, (model_id, description) in enumerate(choices, 1):
        console.print(f"  [bold cyan]{i}.[/bold cyan] {description}")

    console.print(f"  [dim]Default: {default}[/dim]")
    raw = Prompt.ask("Choice", default="1")

    try:
        idx = int(raw.strip()) - 1
        if 0 <= idx < len(choices):
            return choices[idx][0]
    except ValueError:
        pass

    return default
