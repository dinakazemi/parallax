import os
import anthropic
from src.models import PaperContent, ScienceBrief, EmotionalTone, SpatialScale, TemporalDynamic, PhysicalProcess

_MODEL = "claude-opus-4-7"

_SYSTEM = """\
You are a science writer with the philosophical depth of Carl Sagan and the narrative instincts \
of Oliver Sacks. You read scientific papers not to summarize methods, but to find their soul — \
the hidden truth about reality that the authors uncovered.

Your job is to extract:
- The core phenomenon (what is actually happening in nature, not how it was measured)
- What is genuinely counterintuitive or mind-bending about it
- The deeper philosophical or existential implication (what does this say about reality, \
  consciousness, time, life, the universe?)
- The emotional register: does this inspire awe, dread, melancholy, wonder, the uncanny?
- Any visual metaphors or analogies the authors themselves reach for in the text

You must NOT describe the experiment, equipment, statistical methods, or lab procedures. \
Focus entirely on the phenomenon and its meaning.\
"""

_TOOL = {
    "name": "create_science_brief",
    "description": "Output a structured science brief capturing the soul of the paper.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plain_summary": {
                "type": "string",
                "description": "A plain-language explanation of what this paper is about and why it matters. Written for a curious non-expert — no jargon, no methods, no statistics. 3-5 sentences.",
            },
            "core_phenomenon": {
                "type": "string",
                "description": "What is actually happening in nature (not how it was measured). 2-4 sentences.",
            },
            "counterintuitive_element": {
                "type": "string",
                "description": "What defies ordinary intuition or common sense. 1-3 sentences.",
            },
            "philosophical_implication": {
                "type": "string",
                "description": "What this means for our understanding of reality, time, life, or the universe. 2-4 sentences.",
            },
            "emotional_tones": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "awe",
                        "dread",
                        "wonder",
                        "uncanny",
                        "melancholy",
                        "euphoria",
                        "existential",
                        "sublime",
                    ],
                },
                "description": "The dominant emotional registers evoked by this phenomenon. Pick 2-4.",
            },
            "visual_metaphors_in_paper": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Metaphors or analogies the authors themselves use in the text.",
            },
            "one_line_essence": {
                "type": "string",
                "description": "The absolute soul of this paper in one evocative sentence — not a summary, a feeling.",
            },
            "spatial_scale": {
                "type": "string",
                "enum": ["cosmic", "planetary", "geological", "ecological", "human", "cellular", "molecular", "quantum"],
                "description": "The dominant physical scale of the phenomenon.",
            },
            "temporal_dynamic": {
                "type": "string",
                "enum": ["instantaneous", "fast_rhythmic", "slow_gradual", "geological_epochal", "eternal_static"],
                "description": "The characteristic timescale at which the phenomenon operates.",
            },
            "physical_process": {
                "type": "string",
                "enum": ["collapse_convergence", "expansion_emergence", "oscillation_wave", "flow_drift", "transformation_phase", "entanglement_correlation", "boundary_threshold", "cascade_chain"],
                "description": "The dominant physical process or dynamic that characterises the phenomenon.",
            },
        },
        "required": [
            "plain_summary",
            "core_phenomenon",
            "counterintuitive_element",
            "philosophical_implication",
            "emotional_tones",
            "visual_metaphors_in_paper",
            "one_line_essence",
            "spatial_scale",
            "temporal_dynamic",
            "physical_process",
        ],
    },
}


def extract_science_brief(paper: PaperContent) -> ScienceBrief:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_content = f"""Title: {paper.title}

Abstract:
{paper.abstract}

Paper body:
{paper.body}"""

    response = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "create_science_brief"},
        messages=[{"role": "user", "content": user_content}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    data = tool_use.input

    return ScienceBrief(
        plain_summary=data["plain_summary"],
        core_phenomenon=data["core_phenomenon"],
        counterintuitive_element=data["counterintuitive_element"],
        philosophical_implication=data["philosophical_implication"],
        emotional_tones=[EmotionalTone(t) for t in data["emotional_tones"]],
        visual_metaphors_in_paper=data.get("visual_metaphors_in_paper", []),
        one_line_essence=data["one_line_essence"],
        spatial_scale=SpatialScale(data["spatial_scale"]),
        temporal_dynamic=TemporalDynamic(data["temporal_dynamic"]),
        physical_process=PhysicalProcess(data["physical_process"]),
    )
