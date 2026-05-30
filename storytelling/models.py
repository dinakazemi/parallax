from __future__ import annotations

import re
from typing import Literal, Optional
from pydantic import BaseModel, field_validator

# PaperContent is the entry point from the existing ingestion pipeline
from src.models import PaperContent

_XML_TAG_RE = re.compile(r"</?parameter[^>]*>", re.IGNORECASE)
_NEWLINE_BULLET_RE = re.compile(r"\n\s*-\s+")  # \n followed by optional space, dash, required space


def _clean(s: str) -> str:
    """Strip XML parameter tags that some model versions leak into tool outputs."""
    return _XML_TAG_RE.sub("", s).strip()


def _strip_bullet_prefix(s: str) -> str:
    """Strip a leading markdown bullet '- ' if present."""
    return re.sub(r"^-\s+", "", s.strip())


def _expand(raw: str) -> list[str]:
    """Expand a newline-delimited string into a list of items.

    Stage 1 returns visual_elements, metaphor_surface, inviolable_truths, and
    honest_difficulty as newline-separated strings rather than JSON arrays, so
    this is the primary expansion path for those fields.
    """
    s = _clean(raw)
    if _NEWLINE_BULLET_RE.search(s):
        parts = _NEWLINE_BULLET_RE.split(s)
    elif "\n" in s:
        parts = s.split("\n")
    else:
        return [_strip_bullet_prefix(s)] if s else []
    return [stripped for p in parts if (stripped := _strip_bullet_prefix(_clean(p)))]


def _coerce_str_to_list(v: object) -> list[str]:
    """Normalise list fields that Stage 1 returns as newline-delimited strings."""
    if isinstance(v, str):
        return _expand(v)
    # Already a list (e.g. emotional_register, or a cached value) — expand each item.
    result: list[str] = []
    for raw in v:  # type: ignore[union-attr]
        result.extend(_expand(str(raw)))
    return result


class Essence(BaseModel):
    """Stage 1 output: dramatizable raw material extracted from the paper."""
    summary: str
    phenomenon: str
    surprise: str                   # empty string if genuinely nothing surprises
    stakes: str
    visual_elements: list[str]
    metaphor_surface: list[str]     # 3-5 everyday things the phenomenon rhymes with
    emotional_register: list[str]   # primary + optional secondary
    inviolable_truths: list[str]    # 3-6 claims a film cannot contradict
    honest_difficulty: list[str]    # flags e.g. ["no_visual_phenomenon", "highly_abstract"]

    @field_validator(
        "visual_elements", "metaphor_surface", "inviolable_truths",
        "honest_difficulty", "emotional_register",
        mode="before",
    )
    @classmethod
    def coerce_list_fields(cls, v: object) -> object:
        return _coerce_str_to_list(v)


class VoiceDecision(BaseModel):
    mode: Literal["wordless", "narration", "dialogue", "mixed"]
    rationale: str


class Concept(BaseModel):
    """Stage 2 output: one committed story direction.

    The tool returns flat `voice_mode` / `voice_rationale` fields (nested objects
    are unreliable in forced tool use). They are combined into `voice_decision`
    by from_tool_output().
    """
    logline: str
    subject: str                    # POV entity (animal, object, person, place, concept)
    central_image: str              # the one frame a viewer remembers a week later
    structure: str                  # invented narrative shape + justification
    voice_decision: VoiceDecision
    tone: str                       # emotional register → filmmaking sensibility + references
    what_this_film_is_not: list[str]          # 2-3 deliberate rejections of obvious versions
    liberties_taken: list[str] = []           # declared creative departures from the science
    inviolable_truths_check: list[str] = []   # one line per essence truth confirming no contradiction

    @field_validator("what_this_film_is_not", "liberties_taken", "inviolable_truths_check", mode="before")
    @classmethod
    def coerce_list_fields(cls, v: object) -> object:
        return _coerce_str_to_list(v)

    @classmethod
    def from_tool_output(cls, data: dict) -> "Concept":
        """Construct from the flat tool output (voice_mode + voice_rationale)."""
        voice_mode = data.pop("voice_mode", "wordless")
        voice_rationale = data.pop("voice_rationale", "")
        data["voice_decision"] = VoiceDecision(mode=voice_mode, rationale=voice_rationale)
        return cls(**data)


class RubricVerdict(BaseModel):
    specificity: str
    emotional_turn: str
    earned_ending: str
    showing_vs_explaining: str
    visual_rhyme: str
    genericness_check: str
    scientific_integrity: str


class CritiqueResult(BaseModel):
    """Stage 4 output: structured verdict + optional rewrite."""
    rubric: RubricVerdict
    verdict: Literal["PASS", "REVISE", "RECONSIDER"]
    revision_note: Optional[str] = None          # set when verdict=REVISE
    reconsider_direction: Optional[str] = None   # set when verdict=RECONSIDER
    revised_pitch: Optional[str] = None          # full markdown; set when verdict=REVISE


class PipelineRun(BaseModel):
    """Complete run state — written to disk as JSON after each run."""
    paper: PaperContent
    essence: Essence
    concept: Optional[Concept] = None
    pitch: str = ""                     # markdown from Stage 3
    critique: Optional[CritiqueResult] = None
    final_pitch: str = ""               # revised_pitch if REVISE, else pitch
    pipeline_status: Literal["completed", "max_retries_reached"] = "completed"
    retry_count: int = 0
