import json
from pathlib import Path

import anthropic

from src.models import PaperContent
from storytelling.models import Essence

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stage1_essence.txt"
_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "essence_schema.json"
_MODEL = "claude-haiku-4-5-20251001"


def extract_essence(paper: PaperContent) -> Essence:
    client = anthropic.Anthropic()

    prompt_template = _PROMPT_PATH.read_text()
    paper_text = f"Title: {paper.title}\n\nAbstract: {paper.abstract}\n\n{paper.body}"
    prompt = prompt_template.replace("{paper_text}", paper_text)

    tool_def = json.loads(_SCHEMA_PATH.read_text())

    response = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        tools=[tool_def],
        tool_choice={"type": "tool", "name": "extract_essence"},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return Essence(**tool_use.input)
