import os
import json
import anthropic
from src.models import ScienceBrief, CinematicConcept

_MODEL = "claude-opus-4-7"

_SYSTEM = """\
You are a visionary film director and visual artist. Your influences: Denis Villeneuve's \
atmospheric restraint, Andrei Tarkovsky's meditative depth, Christopher Nolan's structural \
ambition, and the surrealist painters. You have been handed a brief about a scientific \
phenomenon and must conceive a single cinematic image that captures its essence.

STRICT RULES:
1. NEVER show labs, scientists, equipment, graphs, or anything that looks like a documentary.
2. Do NOT illustrate the experiment — translate the FEELING of the phenomenon into a visual metaphor.
3. Your image should make a viewer FEEL the phenomenon, not understand it.
4. Think in archetypes: vast scale, lone figures, mirrors, thresholds, light dissolving into dark.
5. The image should feel like it belongs in a film like Arrival, Annihilation, Solaris, \
   Interstellar, or 2001 — not a science explainer.
6. For the runway_prompt: write it as a cinematographer's shot description. Include composition, \
   lighting, lens style, color palette, and mood. End with quality tags: \
   "photorealistic, cinematic, anamorphic lens, film grain, 8K". \
   CRITICAL: Do NOT name any real people, directors, photographers, or artists in the \
   runway_prompt — describe the visual style in purely technical and aesthetic terms instead \
   (e.g. instead of a director's name, write "slow meditative wide shots with extreme depth of field"). \
   CRITICAL: The runway_prompt must be 1000 characters or fewer — Runway's API will reject longer prompts. \
   Be concise and precise: cut filler, keep only the most evocative visual detail.
7. The film_references field is for internal concept notes only — those names must never \
   appear in runway_prompt.
8. Negative prompt should prevent literal science imagery and low quality.\
"""

_TOOL = {
    "name": "create_cinematic_concept",
    "description": "Design a single cinematic image concept that captures the essence of a scientific phenomenon.",
    "input_schema": {
        "type": "object",
        "properties": {
            "logline": {
                "type": "string",
                "description": "One-line cinematic description of the image. Evocative, not explanatory.",
            },
            "scene_description": {
                "type": "string",
                "description": "The scene written like a screenplay direction. 3-5 sentences. Rich with sensory detail.",
            },
            "mood_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "4-6 mood and atmosphere keywords.",
            },
            "color_palette": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 specific colors or color relationships.",
            },
            "lighting_style": {
                "type": "string",
                "description": "Specific lighting description.",
            },
            "film_references": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 films or photographers whose visual language this evokes.",
            },
            "runway_prompt": {
                "type": "string",
                "description": "The complete, optimized prompt for Runway Gen-4 Image. Shot description + lighting + color + mood + quality tags. Must contain zero real people's names — translate all style references into descriptive visual language. Hard limit: 1000 characters maximum.",
            },
            "negative_prompt": {
                "type": "string",
                "description": "What to exclude: lab equipment, scientists, diagrams, text overlays, cartoonish, low quality, etc.",
            },
        },
        "required": [
            "logline",
            "scene_description",
            "mood_keywords",
            "color_palette",
            "lighting_style",
            "film_references",
            "runway_prompt",
            "negative_prompt",
        ],
    },
}


def generate_cinematic_concept(brief: ScienceBrief) -> CinematicConcept:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    brief_text = f"""\
Core phenomenon: {brief.core_phenomenon}

What's counterintuitive: {brief.counterintuitive_element}

Philosophical implication: {brief.philosophical_implication}

Emotional tones: {", ".join(t.value for t in brief.emotional_tones)}

Visual metaphors already in the paper: {json.dumps(brief.visual_metaphors_in_paper)}

Essence of the paper: {brief.one_line_essence}"""

    response = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "create_cinematic_concept"},
        messages=[{"role": "user", "content": brief_text}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    data = tool_use.input

    return CinematicConcept(
        logline=data["logline"],
        scene_description=data["scene_description"],
        mood_keywords=data["mood_keywords"],
        color_palette=data["color_palette"],
        lighting_style=data["lighting_style"],
        film_references=data["film_references"],
        runway_prompt=data["runway_prompt"],
        negative_prompt=data["negative_prompt"],
    )
