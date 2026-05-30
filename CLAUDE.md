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

## Storytelling Engine

A separate four-stage LLM pipeline that produces prose film pitches from scientific papers (no image/video generation).

```bash
python -m storytelling.pipeline <arxiv_id_or_pdf>
python -m storytelling.pipeline <arxiv_id_or_pdf> --stage 1   # stop after Stage 1
```

### Stages (`storytelling/`)

| Stage | Module | Model | Output |
|---|---|---|---|
| 1 — Essence | `stages/essence.py` | Haiku | `Essence` — dramatizable raw material |
| 2 — Concept | `stages/concept.py` | Opus 4.7 | `Concept` — one committed story direction |
| 3 — Pitch | `stages/pitch.py` | Opus 4.7 | Markdown prose pitch |
| 4 — Critique | `stages/critique.py` | Sonnet 4.6 | `CritiqueResult` — PASS / REVISE / RECONSIDER |

Stages 1–3 are cached by input hash at `.cache/storytelling/`. Stage 4 is never cached. RECONSIDER verdict triggers a retry loop (max 2) back to Stage 2.

Prompts live in `storytelling/prompts/*.txt` and schemas in `storytelling/schemas/*.json`. Edit these without touching Python. The Stage 1 cache key includes the prompt+schema hash, so any prompt or schema edit auto-invalidates.

Outputs are written to `outputs/storytelling/<paper_id>/`: `essence.json`, `concept.json`, `pitch.md`, `critique.json`, `final_pitch.md`.

### Key design notes

- Stage 1 returns `visual_elements`, `metaphor_surface`, `inviolable_truths`, `honest_difficulty` as **newline-delimited strings** (not JSON arrays), which `_expand()` in `models.py` splits into lists. `emotional_register` stays a proper JSON array (short, never had split issues).
- Stage 2 has a forced self-check: `inviolable_truths_check` must have at least as many items as `essence.inviolable_truths`. The runner retries up to 2× with feedback if it's missing.
- Stage 4 receives `essence` in addition to `pitch` and `concept` so the `scientific_integrity` rubric criterion can check against the original inviolable truths.

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

Both agents use **forced tool use** (`tool_choice={"type": "tool", "name": "..."}`) so Claude always returns structured JSON. The science agent is instructed to ignore methods/equipment and focus on phenomenon and philosophical implication. The creative director makes **two Claude calls**: pass 1 produces the image concept (including `image_prompt`), pass 2 receives the `image_prompt` + full science brief as explicit input and generates `motion_prompt` — guaranteeing the video prompt animates the exact scene designed in the image prompt. Real people's names must never appear in `image_prompt` — only in `film_references`.

### Key constraints

- `image_prompt` has no hard character limit — model-specific limits are handled by the image generator.
- `gemini_image3_pro` requires ratio `1344:768`; `gen4_image` uses `1280:720` — handled in `_RATIO_BY_MODEL` in `image_generator.py`.
- Veo 3.1 duration supports 4/6/8 seconds; Gen-4 supports 2–10.
- Outputs are saved to `outputs/` (CLI) or `outputs/web/<job_id>/` (web).

### Pre-commit rules
- Before any commits, check the repo and add any irrelevant components to .gitignore
- Before any commits, check if CLAUDE.md needs to be updated