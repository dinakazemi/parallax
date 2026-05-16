# Parallax 🌌
 
**Scientific papers → cinematic visuals.**
 
Parallax is an AI pipeline that reads scientific papers and transforms them into short cinematic video clips. It uses a multi-agent architecture to bridge the gap between dense research and visual storytelling — extracting the science, designing a cinematic concept, and rendering it as imagery and video.
 
Named after the shift in perspective that reveals depth.

Parallax runs in stages, each handled by a specialised component:
 
```
Paper (arXiv / DOI / PDF)
        │
        ▼
┌─────────────────┐
│  Paper Ingestion │  ← Accepts arXiv links, DOIs, or local PDFs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Scientific Agent │  ← Reads the paper, extracts core concepts,
│                  │     key phenomena, and visual potential
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│ Creative Director │  ← Designs a cinematic concept: visual
│     Agent         │     metaphors, colour palette, composition,
│                   │     mood, and camera language
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│ Image Generation │  ← Renders a still frame via Runway Gen-4
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Video Generation │  ← Animates the frame via Runway Gen-4.5
└────────┬────────┘
         │
         ▼
    Cinematic clip
```

## Requirements

- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com/)
- A [Runway API key](https://app.runwayml.com/)

## Setup

```bash
# Clone the repo
git clone https://github.com/dinakazemi/parallax.git
cd parallax

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your API keys
cp .env.example .env   # then fill in the values
```

Your `.env` should contain:

```
ANTHROPIC_API_KEY=your_anthropic_key_here
RUNWAY_API_KEY=your_runway_key_here
```

## Usage

```bash
python main.py <source> [OPTIONS]
```

**`source`** can be:
- An arXiv ID: `2301.07658`
- An arXiv URL: `https://arxiv.org/abs/2301.07658`
- A local PDF path: `paper.pdf`
- A remote PDF URL

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output-dir`, `-o` | `outputs/` | Where to save images and videos |
| `--images`, `-n` | `4` | Number of image variants to generate |
| `--duration`, `-d` | `5` | Video clip length in seconds (`5` or `10`) |
| `--auto` | off | Skip interactive prompts; use defaults and select all images |

### Examples

```bash
# From an arXiv ID (interactive)
python main.py 2301.07658

# From a local PDF, 10-second clips, fully automatic
python main.py paper.pdf --duration 10 --auto

# Custom output directory and image count
python main.py https://arxiv.org/abs/2301.07658 -o my_outputs -n 6
```

## Models used

| Stage | Model |
|-------|-------|
| Science comprehension | Claude Opus 4 (`claude-opus-4-7`) |
| Creative direction | Claude Opus 4 (`claude-opus-4-7`) |
| Image generation | Runway Gen-4 Image |
| Video generation | Runway Gen-4 Turbo or Gen-3 Alpha Turbo (selectable) |
## The Two-Agent Approach
 
The pipeline deliberately separates scientific understanding from creative direction.
 
The **Scientific Agent** reads the paper with precision — identifying the core phenomena, the key visual structures, what makes the research novel, and what would be lost if visualised incorrectly. It produces a structured brief, not a prompt.
 
The **Creative Director Agent** receives that brief and thinks cinematically — translating concepts into visual metaphors, colour palettes, compositions, lighting moods, and camera language. It designs a scene, not a description.
 
This separation matters because a single-step "summarise and visualise" approach tends to produce either scientifically accurate but visually generic output, or visually striking but scientifically hollow imagery. The two-agent architecture gives you both.
 
## Known Limitations
 
- **Video prompting is rigid.** The current video prompt is a fairly direct transformation of the cinematic concept. It needs a more intelligent mapping from scientific concept to motion, camera behaviour, and temporal arc.
- **No iterative refinement.** The pipeline runs once per paper. A future version should allow reviewing and regenerating at each stage.
- **Single visual per paper.** Complex papers may warrant multiple visual interpretations. Currently Parallax produces one.
- **Midjourney produces stronger imagery** for scene composition, but has no API — so that path remains manual.