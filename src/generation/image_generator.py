import os
import httpx
from pathlib import Path
from runwayml import RunwayML, TaskFailedError
from src.models import CinematicConcept, ImageResult

_RATIO = "1280:720"  # cinematic 16:9, confirmed supported by Runway


def generate_images(
    concept: CinematicConcept,
    output_dir: Path,
    model: str = "gen4_image",
    num_images: int = 4,
) -> list[ImageResult]:
    client = RunwayML(api_key=os.environ["RUNWAY_API_KEY"])
    results: list[ImageResult] = []

    for i in range(num_images):
        try:
            task = client.text_to_image.create(
                model=model,
                prompt_text=concept.runway_prompt,
                ratio=_RATIO,
            ).wait_for_task_output()
        except TaskFailedError as e:
            raise RuntimeError(
                f"Image generation failed for variant {i + 1}.\n{e.task_details}"
            ) from e

        image_url = task.output[0]
        local_path = output_dir / f"image_{i + 1:02d}.jpg"
        _download_file(image_url, local_path)

        results.append(
            ImageResult(
                index=i,
                url=image_url,
                local_path=str(local_path),
                model_used=model,
            )
        )

    return results


def _download_file(url: str, dest: Path) -> None:
    with httpx.Client(follow_redirects=True, timeout=60) as http:
        response = http.get(url)
        response.raise_for_status()
        dest.write_bytes(response.content)
