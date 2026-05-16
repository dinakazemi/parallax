import typer
from pathlib import Path
from src.pipeline import run

app = typer.Typer(help="Turn a scientific paper into a cinematic image and video clip.")


@app.command()
def main(
    source: str = typer.Argument(
        ...,
        help="ArXiv ID (e.g. 2301.07658), ArXiv URL, local PDF path, or PDF URL.",
    ),
    output_dir: Path = typer.Option(
        Path("outputs"),
        "--output-dir", "-o",
        help="Directory to save generated images and videos.",
    ),
    num_images: int = typer.Option(
        4,
        "--images", "-n",
        help="Number of image variants to generate.",
    ),
    duration: int = typer.Option(
        5,
        "--duration", "-d",
        help="Video clip duration in seconds (5 or 10).",
    ),
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Skip interactive prompts: use default models and select all images.",
    ),
):
    result = run(
        source=source,
        output_dir=output_dir,
        num_images=num_images,
        video_duration=duration,
        auto=auto,
    )

    typer.echo(f"\nDone. {len(result.videos)} video clip(s) in: {output_dir}")


if __name__ == "__main__":
    app()
