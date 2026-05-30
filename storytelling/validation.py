"""
Lightweight content validators for each pipeline stage.

Pydantic handles type correctness. These validators catch quality problems
that survive parsing: empty required fields, residual formatting artifacts,
and structural inconsistencies between stages.

Each validator returns a list of issue strings. An empty list means clean.
Issues are warnings, not exceptions — the pipeline logs them and continues.
Stage 4 is the hard quality gate.
"""
from __future__ import annotations

import re

from storytelling.models import Concept, CritiqueResult, Essence

_BULLET_PREFIX = re.compile(r"^-\s")
_HAS_NEWLINE = re.compile(r"\n")
_HAS_XML_TAG = re.compile(r"</?parameter", re.IGNORECASE)


def _check_list_items(field: str, items: list[str]) -> list[str]:
    """Return artifact issues found in any item of a list field."""
    issues = []
    for i, item in enumerate(items):
        if _BULLET_PREFIX.match(item):
            issues.append(f"{field}[{i}]: residual bullet prefix — '- ' not stripped: {item[:60]!r}")
        if _HAS_NEWLINE.search(item):
            issues.append(f"{field}[{i}]: embedded newline not expanded: {item[:60]!r}")
        if _HAS_XML_TAG.search(item):
            issues.append(f"{field}[{i}]: XML parameter tag not stripped: {item[:60]!r}")
    return issues


def validate_essence(e: Essence) -> list[str]:
    issues: list[str] = []

    for field in ("visual_elements", "metaphor_surface", "inviolable_truths", "honest_difficulty"):
        issues.extend(_check_list_items(f"Essence.{field}", getattr(e, field)))

    if not e.inviolable_truths:
        issues.append(
            "Essence.inviolable_truths: empty — every paper has at least one inviolable truth; "
            "Stage 4 scientific_integrity check will have nothing to work with"
        )
    if not e.visual_elements:
        issues.append("Essence.visual_elements: empty")

    return issues


def validate_concept(c: Concept, essence: Essence | None = None) -> list[str]:
    issues: list[str] = []

    for field in ("what_this_film_is_not", "liberties_taken", "inviolable_truths_check"):
        issues.extend(_check_list_items(f"Concept.{field}", getattr(c, field)))

    if essence and essence.inviolable_truths and not c.inviolable_truths_check:
        issues.append(
            f"Concept.inviolable_truths_check: empty, but essence has "
            f"{len(essence.inviolable_truths)} inviolable truth(s) — "
            "Stage 4 scientific_integrity check will rely on essence data only"
        )
    elif (
        essence
        and essence.inviolable_truths
        and c.inviolable_truths_check
        and len(c.inviolable_truths_check) != len(essence.inviolable_truths)
    ):
        issues.append(
            f"Concept.inviolable_truths_check: {len(c.inviolable_truths_check)} item(s) "
            f"but essence has {len(essence.inviolable_truths)} inviolable truth(s) — counts should match"
        )

    if len(c.what_this_film_is_not) < 2:
        issues.append(
            f"Concept.what_this_film_is_not: only {len(c.what_this_film_is_not)} item(s); "
            "prompt requires 2-3 — model may not have pushed past obvious ideas"
        )

    return issues


def validate_critique(cr: CritiqueResult) -> list[str]:
    issues: list[str] = []

    if cr.verdict == "REVISE" and not cr.revised_pitch:
        issues.append("CritiqueResult: verdict=REVISE but revised_pitch is empty — using original pitch")
    if cr.verdict == "RECONSIDER" and not cr.reconsider_direction:
        issues.append("CritiqueResult: verdict=RECONSIDER but reconsider_direction is empty — cannot retry Stage 2")

    return issues
