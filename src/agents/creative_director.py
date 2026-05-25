import base64
import os
import json
from pathlib import Path
import anthropic
from src.models import ScienceBrief, CinematicConcept, ImageResult

_MODEL = "claude-opus-4-7"

# ── Shared safety block (interpolated into both system prompts) ───────────────

_SAFETY_BLOCK = """\
── SAFETY FILTER COMPLIANCE ──
Prompts you generate will be passed to third-party APIs with content moderation.

1. Describe visible action and physical state, not lethal outcomes or intent. \
Render what a camera would see, not what is happening internally to a character.

2. Avoid trigger categories: death/dying, suffocation/asphyxiation, blood/gore, \
weapons used on people, self-harm, sexual content, real public figures by name, \
branded IP, drugs, and graphic injury. Also avoid clinical/medical distress terms \
(cardiac arrest, overdose, strangulation, drowning).

3. Substitute with cinematic equivalents that preserve the shot:
   - "dying"       → "collapsing slowly", "going still", "eyes fluttering closed"
   - "suffocating" → "gasping", "clutching throat", "straining for breath"
   - "dead body"   → "motionless figure", "still form"
   - "fighting"    → "struggling", "locked in motion"
   - "blood"       → "dark liquid", "crimson stain" (or omit)
   - "scared" / "terrified" → "wide-eyed", "trembling", "breath held"

4. Lead with camera, composition, lighting, motion, and style. A prompt heavy on \
"low-angle dolly-in, rim-lit, shallow depth of field, slow-motion" rarely gets flagged.

5. If the requested scene is fundamentally non-compliant, return the prompt anyway \
but prepend "[LIKELY_FLAGGED]" so the pipeline can route it.

6. Self-check before output: read your prompt and ask "would a conservative moderation \
classifier flag any single word here?" If yes, rewrite using rule 3.\
"""

# ── Pass 1: image concept ─────────────────────────────────────────────────────

_SYSTEM = f"""\
You are a visionary film director and visual artist — your influences are atmospheric \
restraint, meditative depth, structural ambition, and surrealist painters. You have been \
handed a brief about a scientific phenomenon and must conceive a single cinematic image \
that captures its essence.

── CINEMATIC TRANSLATION GRAMMAR ──
Apply these mappings mechanically from the science brief:

SPATIAL SCALE → composition and framing
  cosmic/planetary      → extreme wide, subject dwarfed by negative space, horizon at 1/3
  geological/ecological → wide establishing with environmental depth
  human                 → medium shot with environmental context visible
  cellular/molecular    → extreme close-up, shallow depth of field, macro lens aesthetic
  quantum               → abstract geometry, impossible scales, impossible angles

EMOTIONAL TONE → colour temperature and contrast
  awe/sublime  → desaturated with one extreme accent, vast negative space
  dread        → high contrast, advancing shadows, cool-to-cold palette
  wonder       → soft diffused light, unexpected warmth in cold environments
  uncanny      → familiar geometry with wrong lighting, slightly off colour temperature
  melancholy   → low saturation, diffuse overcast, muted earth tones
  euphoria     → warm rim lighting, luminous atmosphere, golden tones
  existential  → infinite depth, human scale against cosmic scale

── IMAGE PROMPT RULES ──
1. NEVER show labs, scientists, equipment, graphs, or anything documentary.
2. Do NOT illustrate the experiment — translate the FEELING of the phenomenon into a visual metaphor.
3. The image should make a viewer FEEL the phenomenon, not understand it.
4. The image should feel like it belongs in Arrival, Annihilation, Solaris, Interstellar, or 2001.
5. image_prompt is a cinematographer's shot description: composition + lighting + lens style + \
colour palette + mood + quality tags ("photorealistic, cinematic, anamorphic lens, film grain, 8K"). \
CRITICAL: no real people's names — translate style references into purely technical/aesthetic terms.
6. film_references is for internal concept notes only — those names must never appear in image_prompt.
7. negative_prompt must prevent literal science imagery and low quality.

{_SAFETY_BLOCK}"""

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
            "image_prompt": {
                "type": "string",
                "description": (
                    "The complete, optimized prompt for the image model. Shot description + lighting + "
                    "color + mood + quality tags. Must contain zero real people's names — translate all "
                    "style references into descriptive visual language. "
                    "Apply SAFETY FILTER COMPLIANCE rules from the system prompt."
                ),
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
            "image_prompt",
            "negative_prompt",
        ],
    },
}


# ── Pass 2: motion prompt ─────────────────────────────────────────────────────

_MOTION_SYSTEM = f"""\
You are animating a single cinematic still into a short video clip. You will be given \
an image prompt (describing the frame at time-0) and a full science brief. Your task is \
to design camera movement and scene motion that extend the image — not replace or \
reinterpret it.

── MOTION RULES ──
1. PRESERVE the composition, lighting, colour palette, and subject from the image prompt. \
   The image prompt describes frame-0. Your motion describes how it evolves from there.
2. Use the full science brief to reason about why this motion serves the phenomenon — the \
   counterintuitive element and philosophical implication often point to non-obvious choices. \
   Let the physical process guide your camera verb:
   - collapse / convergence     → dolly-in, light narrowing
   - expansion / emergence      → dolly-out, light spreading outward
   - oscillation / wave         → slow rhythmic pan or tilt matching the period
   - flow / drift               → truck-left or truck-right following the direction
   - transformation / phase     → static, subject morphing, light quality shifting
   - entanglement / correlation → static, mirrored subject motion, two points in dialogue
   - boundary / threshold       → static, camera held at the edge, neither in nor out
   - cascade / chain            → tilt-up or tilt-down following the chain direction
   Let the temporal dynamic guide your speed:
   - instantaneous      → "rapid"; freeze at peak, motion blur on moving elements
   - fast_rhythmic      → "rapid" or "moderate"; pulse synced to the phenomenon's rhythm
   - slow_gradual       → "slow"; barely-there drift
   - geological_epochal → "imperceptibly slow" or "static"; time itself is the motion
   - eternal_static     → "static"; locked-off, absolute stillness

── MOTION PROMPT STRUCTURE ──
Compose the motion_prompt as four labeled sections in this order. \
Each section answers one specific question. Do not mix concerns across sections.

[CAMERA]: What does the camera do in 3D space? Use only these verbs:
  "static" (locked-off, no movement)
  "dolly-in" (camera moves toward subject)
  "dolly-out" (camera moves away from subject)
  "truck-left" / "truck-right" (camera slides sideways)
  "pedestal-up" / "pedestal-down" (camera rises/lowers vertically)
  "orbit-left" / "orbit-right" (camera circles subject)
  "tilt-up" / "tilt-down" (camera rotates vertically, stationary)
  "pan-left" / "pan-right" (camera rotates horizontally, stationary)
  Include speed: "imperceptibly slow", "slow", "moderate", "rapid".
  Never use "push", "pull", "move outward", "move inward" — these are \
  ambiguous. Use the verbs above only.

[SUBJECT]: What does the subject do in world-space? Describe intrinsic motion: \
  expansion, contraction, rotation, flow, morphing, particle drift. \
  State direction in world coordinates, not frame coordinates.

[FRAME RESULT]: What does this look like in the final frame? State the net visible \
  outcome explicitly: "By the end of the shot, [subject] occupies [more/less/the same \
  amount of] the frame, and [other visible changes]."

[LIGHT & ATMOSPHERE]: How does light evolve? Colour temperature shifts, brightness \
  changes, particle behaviour, atmospheric haze.

End with: "Cinematic, film grain."

{_SAFETY_BLOCK}"""

_MOTION_TOOL = {
    "name": "create_motion_prompt",
    "description": "Design camera movement and scene animation to bring the cinematic still to life.",
    "input_schema": {
        "type": "object",
        "properties": {
            "motion_prompt": {
                "type": "string",
                "description": (
                    "Camera movement and scene motion for the image-to-video model, written as four "
                    "labeled sections in order: [CAMERA], [SUBJECT], [FRAME RESULT], [LIGHT & ATMOSPHERE]. "
                    "Follow the MOTION PROMPT STRUCTURE from the system prompt exactly — use only the "
                    "approved camera verbs, state subject motion in world-space, and resolve net frame "
                    "outcome in [FRAME RESULT]. Animate the exact scene in the image prompt; do not "
                    "invent a different scene. End with: Cinematic, film grain. "
                    "Apply SAFETY FILTER COMPLIANCE: avoid trigger words, substitute cinematic "
                    "equivalents, prepend [LIKELY_FLAGGED] only if fundamentally non-compliant."
                ),
            },
        },
        "required": ["motion_prompt"],
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

Essence of the paper: {brief.one_line_essence}

Spatial scale: {brief.spatial_scale.value}
Temporal dynamic: {brief.temporal_dynamic.value}
Physical process: {brief.physical_process.value}"""

    # Pass 1: image concept
    r1 = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "create_cinematic_concept"},
        messages=[{"role": "user", "content": brief_text}],
    )
    data = next(b for b in r1.content if b.type == "tool_use").input
    concept = CinematicConcept(
        logline=data["logline"],
        scene_description=data["scene_description"],
        mood_keywords=data["mood_keywords"],
        color_palette=data["color_palette"],
        lighting_style=data["lighting_style"],
        film_references=data["film_references"],
        image_prompt=data["image_prompt"],
        negative_prompt=data["negative_prompt"],
        motion_prompt="",
    )

    # Pass 2: motion prompt — receives the image prompt + full science brief as explicit input
    motion_input = f"""\
Image prompt (frame-0 of the shot):
{concept.image_prompt}

Scene description:
{concept.scene_description}

--- Full science brief ---
Core phenomenon: {brief.core_phenomenon}
What's counterintuitive: {brief.counterintuitive_element}
Philosophical implication: {brief.philosophical_implication}
Emotional tones: {", ".join(t.value for t in brief.emotional_tones)}
Visual metaphors in the paper: {json.dumps(brief.visual_metaphors_in_paper)}
Essence: {brief.one_line_essence}
Spatial scale: {brief.spatial_scale.value}
Temporal dynamic: {brief.temporal_dynamic.value}
Physical process: {brief.physical_process.value}

Animate this specific image to embody the phenomenon above."""

    r2 = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=_MOTION_SYSTEM,
        tools=[_MOTION_TOOL],
        tool_choice={"type": "tool", "name": "create_motion_prompt"},
        messages=[{"role": "user", "content": motion_input}],
    )
    motion_data = next(b for b in r2.content if b.type == "tool_use").input
    return concept.model_copy(update={"motion_prompt": motion_data["motion_prompt"]})
