from pathlib import Path
from typing import Literal

import anthropic

from storytelling.models import Concept, CritiqueResult, Essence, RubricVerdict

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stage4_critique.txt"
_MODEL = "claude-sonnet-4-6"

_CRITIQUE_TOOL = {
    "name": "critique_pitch",
    "description": "Evaluate the pitch against seven criteria and deliver a verdict.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rubric": {
                "type": "object",
                "description": "One-sentence verdict for each criterion.",
                "properties": {
                    "specificity": {"type": "string"},
                    "emotional_turn": {"type": "string"},
                    "earned_ending": {"type": "string"},
                    "showing_vs_explaining": {"type": "string"},
                    "visual_rhyme": {"type": "string"},
                    "genericness_check": {"type": "string"},
                    "scientific_integrity": {"type": "string"},
                },
                "required": [
                    "specificity", "emotional_turn", "earned_ending",
                    "showing_vs_explaining", "visual_rhyme", "genericness_check",
                    "scientific_integrity",
                ],
            },
            "verdict": {
                "type": "string",
                "enum": ["PASS", "REVISE", "RECONSIDER"],
            },
            "revision_note": {
                "type": "string",
                "description": "Set only when verdict=REVISE. 2-3 sentences on what changed and why.",
            },
            "reconsider_direction": {
                "type": "string",
                "description": "Set only when verdict=RECONSIDER. Specific direction for Stage 2.",
            },
            "revised_pitch": {
                "type": "string",
                "description": "Full rewritten pitch markdown. Set only when verdict=REVISE.",
            },
        },
        "required": ["rubric", "verdict"],
    },
}


def critique_and_revise(pitch: str, concept: Concept, essence: Essence) -> CritiqueResult:
    client = anthropic.Anthropic()

    prompt_template = _PROMPT_PATH.read_text()
    prompt = (
        prompt_template
        .replace("{pitch}", pitch)
        .replace("{concept_json}", concept.model_dump_json(indent=2))
        .replace("{essence_json}", essence.model_dump_json(indent=2))
    )

    response = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        tools=[_CRITIQUE_TOOL],
        tool_choice={"type": "tool", "name": "critique_pitch"},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    data = tool_use.input
    data["rubric"] = RubricVerdict(**data["rubric"])
    return CritiqueResult(**data)
