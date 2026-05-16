import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from src.models import ImageResult

console = Console()


def select_images_interactive(images: list[ImageResult]) -> list[ImageResult]:
    """Open images in the system viewer and let the user pick which to send to video."""
    _open_in_viewer([img.local_path for img in images])

    console.print()
    _print_image_table(images)
    console.print()
    console.print("[bold cyan]Images have been opened in your viewer.[/bold cyan]")
    console.print("Enter the numbers of the images you want to turn into video clips.")
    console.print("[dim]Example: 1,3  or  2  or  1,2,3,4[/dim]")

    while True:
        raw = Prompt.ask("[bold]Your selection")
        selected = _parse_selection(raw, len(images))
        if selected:
            return [images[i - 1] for i in selected]
        console.print("[red]Invalid selection. Enter numbers separated by commas.[/red]")


def select_images_auto(images: list[ImageResult]) -> list[ImageResult]:
    """Auto mode: select all generated images."""
    console.print(f"[dim]Auto-selecting all {len(images)} generated images.[/dim]")
    return images


def _open_in_viewer(paths: list[str]) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open"] + paths, check=False)
    elif sys.platform.startswith("linux"):
        for p in paths:
            subprocess.Popen(["xdg-open", p])
    elif sys.platform == "win32":
        for p in paths:
            subprocess.Popen(["start", p], shell=True)


def _print_image_table(images: list[ImageResult]) -> None:
    table = Table(title="Generated Images", show_header=True, header_style="bold magenta")
    table.add_column("#", style="bold", width=4)
    table.add_column("File", style="cyan")
    table.add_column("Model", style="dim")

    for img in images:
        table.add_row(
            str(img.index + 1),
            Path(img.local_path).name,
            img.model_used,
        )
    console.print(table)


def _parse_selection(raw: str, max_index: int) -> list[int] | None:
    try:
        indices = [int(x.strip()) for x in raw.split(",") if x.strip()]
        if all(1 <= i <= max_index for i in indices) and len(indices) > 0:
            return sorted(set(indices))
    except ValueError:
        pass
    return None
