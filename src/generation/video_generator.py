import os
import httpx
from pathlib import Path
from runwayml import RunwayML, TaskFailedError
from src.models import ImageResult, VideoResult, CinematicConcept

_RATIO = "1280:720"


def generate_videos(
    selected_images: list[ImageResult],
    concept: CinematicConcept,
    output_dir: Path,
    model: str = "veo3.1",
    duration: int = 8,
) -> list[VideoResult]:
    client = RunwayML(api_key=os.environ["RUNWAY_API_KEY"])
    results: list[VideoResult] = []

    for img in selected_images:
        try:
            task = client.image_to_video.create(
                model=model,
                prompt_image=img.url,
                prompt_text=concept.motion_prompt,
                duration=duration,
                ratio=_RATIO,
            ).wait_for_task_output()
        except TaskFailedError as e:
            raise RuntimeError(
                f"Video generation failed for image {img.index + 1}.\n{e.task_details}"
            ) from e

        video_url = task.output[0]
        local_path = output_dir / f"video_{img.index + 1:02d}.mp4"
        _download_file(video_url, local_path)

        results.append(
            VideoResult(
                url=video_url,
                local_path=str(local_path),
                source_image_index=img.index,
                model_used=model,
                duration=duration,
            )
        )

    return results



def _download_file(url: str, dest: Path) -> None:
    with httpx.Client(follow_redirects=True, timeout=120) as http:
        response = http.get(url)
        response.raise_for_status()
        dest.write_bytes(response.content)
