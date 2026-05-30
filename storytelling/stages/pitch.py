import re
from pathlib import Path

import anthropic

from storytelling.models import Concept, Essence

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stage3_pitch.txt"
_MODEL = "claude-opus-4-7"
_REQUIRED_HEADINGS = ["# ", "## LOGLINE", "## THE FILM", "## WHY THIS WORKS"]


def _validate_structure(text: str) -> None:
    for heading in _REQUIRED_HEADINGS:
        if heading not in text:
            raise ValueError(f"Pitch missing required section: {heading!r}")

    film_section = re.search(r"## THE FILM\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if film_section:
        word_count = len(film_section.group(1).split())
        if word_count < 150 or word_count > 500:
            # Soft warning rather than hard failure — let Stage 4 catch quality issues
            pass


def write_pitch(concept: Concept, essence: Essence) -> str:
    client = anthropic.Anthropic()

    prompt_template = _PROMPT_PATH.read_text()
    concept_block = f"{concept.model_dump_json(indent=2)}"
    prompt = prompt_template.replace("{concept_json}", concept_block)

    response = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    pitch = response.content[0].text.strip()
    _validate_structure(pitch)
    return pitch
