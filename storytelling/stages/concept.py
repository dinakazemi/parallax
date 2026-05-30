import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import anthropic

from storytelling.models import Concept, Essence

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "stage2_concept.txt"
_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "concept_schema.json"
_MODEL = "claude-opus-4-7"
_MAX_VALIDATION_RETRIES = 2


# ---------------------------------------------------------------------------
# Validation types
# ---------------------------------------------------------------------------

@dataclass
class ValidationSuccess:
    pass


@dataclass
class ValidationFailure:
    reason: str
    retry_with_feedback: bool = True


def validate_concept_against_essence(
    concept: Concept, essence: Essence
) -> Union[ValidationSuccess, ValidationFailure]:
    essence_truths = essence.inviolable_truths
    concept_check = concept.inviolable_truths_check

    if essence_truths and not concept_check:
        return ValidationFailure(
            reason=(
                "inviolable_truths_check is empty but essence lists inviolable_truths. "
                "The rigor self-check did not fire."
            ),
            retry_with_feedback=True,
        )

    if essence_truths and len(concept_check) < len(essence_truths):
        return ValidationFailure(
            reason=(
                f"inviolable_truths_check has {len(concept_check)} item(s) but essence "
                f"lists {len(essence_truths)}. At least one truth was not addressed."
            ),
            retry_with_feedback=True,
        )

    return ValidationSuccess()


# ---------------------------------------------------------------------------
# Stage runner
# ---------------------------------------------------------------------------

def _call_model(
    client: anthropic.Anthropic,
    tool_def: dict,
    prompt: str,
    feedback: Optional[str] = None,
) -> Concept:
    messages: list[dict] = [{"role": "user", "content": prompt}]
    if feedback:
        # Append the feedback as a follow-up turn so the model sees its own
        # prior output and the specific failure reason before regenerating.
        messages.append({
            "role": "assistant",
            "content": (
                "[Previous output was rejected by the orchestrator for the "
                f"following reason: {feedback}. Please regenerate, addressing "
                "the issue described above. The inviolable_truths_check field "
                "must be fully populated before you return your output.]"
            ),
        })
        messages.append({"role": "user", "content": "Please try again."})

    response = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        tools=[tool_def],
        tool_choice={"type": "tool", "name": "develop_concept"},
        messages=messages,
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return Concept.from_tool_output(dict(tool_use.input))


def develop_concept(essence: Essence, critic_notes: Optional[str] = None) -> Concept:
    client = anthropic.Anthropic()

    prompt_template = _PROMPT_PATH.read_text()
    critic_direction = (
        f"## CRITIC'S DIRECTION\n\n{critic_notes}"
        if critic_notes
        else ""
    )
    prompt = prompt_template.replace(
        "{essence_json}", essence.model_dump_json(indent=2)
    ).replace("{critic_direction}", critic_direction)

    tool_def = json.loads(_SCHEMA_PATH.read_text())

    concept = _call_model(client, tool_def, prompt)

    for attempt in range(_MAX_VALIDATION_RETRIES):
        result = validate_concept_against_essence(concept, essence)
        if isinstance(result, ValidationSuccess):
            break
        if not result.retry_with_feedback:
            break
        concept = _call_model(client, tool_def, prompt, feedback=result.reason)
    # Return whatever we have after retries — validation.py in the pipeline
    # will surface any remaining issues as warnings.

    return concept
