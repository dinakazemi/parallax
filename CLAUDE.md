# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# CLI
python main.py <arxiv_id_or_pdf> [--images 4] [--duration 8] [--auto]

# Web UI
python web_app.py          # serves at http://127.0.0.1:8000
```

`.env` requires `ANTHROPIC_API_KEY` and `RUNWAY_API_KEY`.

## Architecture

Parallax is a linear multi-stage pipeline: **ingest → science agent → creative agent → image generation → (interactive selection) → video generation**.

### Entry points

- **CLI** — `main.py` → `src/pipeline.py` runs all stages sequentially with Rich terminal output and interactive model/image selection prompts.
- **Web UI** — `web_app.py` (FastAPI) runs the same stages in a background thread per job, streaming SSE events to the browser. Jobs are stored in a module-level `_jobs` dict; the browser POSTs selected image indices to `/jobs/{id}/select` to unblock the pipeline thread waiting on `selection_event`.

### Pipeline stages (`src/`)

| Module | Role |
|---|---|
| `ingestion/arxiv_fetcher.py` | Downloads paper via the `arxiv` library, returns `PaperContent` |
| `ingestion/pdf_parser.py` | Parses local or remote PDFs with PyMuPDF, returns `PaperContent` |
| `agents/science_comprehension.py` | Claude Opus call with forced tool use → `ScienceBrief` |
| `agents/creative_director.py` | Claude Opus call with forced tool use → `CinematicConcept` |
| `generation/image_generator.py` | Runway text-to-image (`gemini_image3_pro` or `gen4_image`) |
| `generation/video_generator.py` | Runway image-to-video (`veo3.1`, `gen4_turbo`, `gen4.5`) |
| `selection/image_selector.py` | Interactive (Rich) or auto selection of images for video |

### Data models (`src/models.py`)

All inter-stage data is Pydantic: `PaperContent → ScienceBrief → CinematicConcept → ImageResult[] → VideoResult[]`. `IMAGE_MODELS` and `VIDEO_MODELS` dicts here control what's shown to users; add new Runway models here first.

### Agent design

Both agents use **forced tool use** (`tool_choice={"type": "tool", "name": "..."}`) so Claude always returns structured JSON. The science agent is instructed to ignore methods/equipment and focus on phenomenon and philosophical implication. The creative director is instructed never to name real people in `runway_prompt` (Runway rejects them) — only in `film_references`.

### Key constraints

- `runway_prompt` must be ≤ 1000 characters (enforced in the creative director system prompt) for cross-model compatibility.
- `gemini_image3_pro` requires ratio `1344:768`; `gen4_image` uses `1280:720` — handled in `_RATIO_BY_MODEL` in `image_generator.py`.
- Veo 3.1 duration supports 4/6/8 seconds; Gen-4 supports 2–10.
- Outputs are saved to `outputs/` (CLI) or `outputs/web/<job_id>/` (web).

### Git rules
- Before any commits, check the repo and add any irrelevant components to .gitingore
- Before any commits, check if CLOUDE.md needs to be updated