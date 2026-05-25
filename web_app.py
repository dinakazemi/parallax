import asyncio
import json
import queue
import re
import threading
import traceback
import uuid
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from src.agents.creative_director import generate_cinematic_concept
from src.agents.science_comprehension import extract_science_brief
from src.generation.image_generator import generate_images
from src.generation.video_generator import generate_videos
from src.ingestion.arxiv_fetcher import fetch_arxiv
from src.ingestion.pdf_parser import parse_pdf
from src.models import IMAGE_MODELS, VIDEO_MODELS

_OUTPUTS = Path("outputs/web")
_OUTPUTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Parallax")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

_jobs: dict[str, "_Job"] = {}


class _Job:
    def __init__(self):
        self.q: queue.Queue = queue.Queue()
        self.images = []
        self.selection_event = threading.Event()
        self.selected: list[int] = []


class _RunRequest(BaseModel):
    source: str
    num_images: int = 4
    image_model: str = "gemini_image3_pro"
    video_model: str = "veo3.1"
    duration: int = 8


class _SelectRequest(BaseModel):
    indices: list[int]


@app.get("/", response_class=HTMLResponse)
async def index():
    return (Path(__file__).parent / "templates" / "index.html").read_text()


@app.get("/models")
async def models():
    return {"image": IMAGE_MODELS, "video": VIDEO_MODELS}


@app.post("/jobs")
async def create_job(req: _RunRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = _Job()
    background_tasks.add_task(_run, job_id, req)
    return {"job_id": job_id}


@app.post("/jobs/upload")
async def create_job_from_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    num_images: int = Form(4),
    image_model: str = Form("gemini_image3_pro"),
    video_model: str = Form("veo3.1"),
    duration: int = Form(8),
):
    job_id = str(uuid.uuid4())
    dest = _OUTPUTS / job_id / "upload.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(await file.read())
    _jobs[job_id] = _Job()
    req = _RunRequest(
        source=str(dest),
        num_images=num_images,
        image_model=image_model,
        video_model=video_model,
        duration=duration,
    )
    background_tasks.add_task(_run, job_id, req)
    return {"job_id": job_id}


@app.get("/jobs/{job_id}/stream")
async def stream(job_id: str):
    if job_id not in _jobs:
        return HTMLResponse("not found", status_code=404)
    job = _jobs[job_id]

    async def generate():
        loop = asyncio.get_event_loop()
        while True:
            try:
                event = await loop.run_in_executor(None, lambda: job.q.get(timeout=30))
            except queue.Empty:
                yield 'data: {"type":"heartbeat"}\n\n'
                continue
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in ("done", "error"):
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/jobs/{job_id}/select")
async def select(job_id: str, req: _SelectRequest):
    if job_id not in _jobs:
        return HTMLResponse("not found", status_code=404)
    job = _jobs[job_id]
    job.selected = req.indices
    job.selection_event.set()
    return {"ok": True}


def _is_arxiv(source: str) -> bool:
    s = source.strip()
    return bool(
        re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", s)
        or s.lower().startswith("arxiv:")
        or "arxiv.org" in s
    )


def _web_url(local_path: str) -> str:
    return "/" + str(local_path).replace("\\", "/")


def _run(job_id: str, req: _RunRequest):
    job = _jobs[job_id]
    emit = job.q.put
    out = _OUTPUTS / job_id
    out.mkdir(parents=True, exist_ok=True)

    try:
        emit({"type": "step", "id": "ingest", "label": "Ingesting paper"})
        paper = (
            fetch_arxiv(req.source) if _is_arxiv(req.source) else parse_pdf(req.source)
        )
        emit({"type": "paper", "title": paper.title, "abstract": paper.abstract[:600]})

        emit({"type": "step", "id": "brief", "label": "Extracting scientific essence"})
        brief = extract_science_brief(paper)
        emit(
            {
                "type": "brief",
                "summary": brief.plain_summary,
                "essence": brief.one_line_essence,
                "phenomenon": brief.core_phenomenon,
                "tones": [t.value for t in brief.emotional_tones],
            }
        )

        emit({"type": "step", "id": "concept", "label": "Generating cinematic concept"})
        concept = generate_cinematic_concept(brief)
        emit(
            {
                "type": "concept",
                "logline": concept.logline,
                "scene": concept.scene_description,
                "image_prompt": concept.image_prompt,
                "motion_prompt": concept.motion_prompt,
                "references": concept.film_references,
            }
        )

        # emit(
        #     {
        #         "type": "step",
        #         "id": "images",
        #         "label": f"Generating {req.num_images} images",
        #     }
        # )
        # images = generate_images(concept, out, model=req.image_model, num_images=req.num_images)
        # job.images = images
        # emit({"type": "images_ready", "images": [
        #     {"index": img.index, "url": _web_url(img.local_path)} for img in images
        # ]})

        # emit({"type": "awaiting_selection"})
        # job.selection_event.wait()

        # selected = [images[i] for i in job.selected if i < len(images)] or images

        # emit({"type": "step", "id": "videos", "label": f"Generating {len(selected)} video clip(s)"})
        # videos = generate_videos(selected, concept, out, model=req.video_model, duration=req.duration)
        # emit({"type": "videos_ready", "videos": [
        #     {"url": _web_url(v.local_path), "source": v.source_image_index} for v in videos
        # ]})

        emit({"type": "done"})

    except Exception as exc:
        emit({"type": "error", "message": str(exc), "trace": traceback.format_exc()})


if __name__ == "__main__":
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
