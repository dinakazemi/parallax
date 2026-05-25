from pydantic import BaseModel
from typing import Optional
from enum import Enum


class EmotionalTone(str, Enum):
    AWE = "awe"
    DREAD = "dread"
    WONDER = "wonder"
    UNCANNY = "uncanny"
    MELANCHOLY = "melancholy"
    EUPHORIA = "euphoria"
    EXISTENTIAL = "existential"
    SUBLIME = "sublime"


class SpatialScale(str, Enum):
    COSMIC = "cosmic"  # galaxies, universe-scale
    PLANETARY = "planetary"  # planets, atmospheres
    GEOLOGICAL = "geological"  # landscapes, tectonic
    ECOLOGICAL = "ecological"  # ecosystems, organisms
    HUMAN = "human"  # body-scale
    CELLULAR = "cellular"  # cells, tissue
    MOLECULAR = "molecular"  # molecules, proteins
    QUANTUM = "quantum"  # atoms, subatomic


class TemporalDynamic(str, Enum):
    INSTANTANEOUS = "instantaneous"  # faster than perception
    FAST_RHYTHMIC = "fast_rhythmic"  # heartbeat, neural firing
    SLOW_GRADUAL = "slow_gradual"  # seasons, growth
    GEOLOGICAL_EPOCHAL = "geological_epochal"  # millions of years
    ETERNAL_STATIC = "eternal_static"  # constants, equilibria


class PhysicalProcess(str, Enum):
    COLLAPSE_CONVERGENCE = "collapse_convergence"
    EXPANSION_EMERGENCE = "expansion_emergence"
    OSCILLATION_WAVE = "oscillation_wave"
    FLOW_DRIFT = "flow_drift"
    TRANSFORMATION_PHASE = "transformation_phase"
    ENTANGLEMENT_CORRELATION = "entanglement_correlation"
    BOUNDARY_THRESHOLD = "boundary_threshold"
    CASCADE_CHAIN = "cascade_chain"


class PaperContent(BaseModel):
    title: str
    abstract: str
    body: str
    source: str  # file path or arxiv ID


class ScienceBrief(BaseModel):
    plain_summary: str  # accessible, jargon-free explanation for a curious non-expert
    core_phenomenon: str
    counterintuitive_element: str
    philosophical_implication: str
    emotional_tones: list[EmotionalTone]
    visual_metaphors_in_paper: list[str]  # metaphors the authors themselves used
    one_line_essence: str  # the soul of the paper in one sentence
    spatial_scale: SpatialScale
    temporal_dynamic: TemporalDynamic
    physical_process: PhysicalProcess


class CinematicConcept(BaseModel):
    logline: str
    scene_description: str  # written like a screenplay direction
    mood_keywords: list[str]
    color_palette: list[str]
    lighting_style: str
    film_references: list[str]
    image_prompt: str
    negative_prompt: str
    motion_prompt: str  # final generation prompt for Runway image-to-video


class ImageResult(BaseModel):
    index: int
    url: str
    local_path: str
    model_used: str


class VideoResult(BaseModel):
    url: str
    local_path: str
    source_image_index: int
    model_used: str
    duration: int  # seconds


class PipelineResult(BaseModel):
    paper_title: str
    paper_source: str
    science_brief: ScienceBrief
    cinematic_concept: CinematicConcept
    generated_images: list[ImageResult]
    selected_images: list[ImageResult]
    videos: list[VideoResult]


# Available Runway models exposed to the user
IMAGE_MODELS: dict[str, str] = {
    "gemini_image3_pro": "Nano Banana Pro (gemini_image3_pro) — up to 4K, 5500-char prompts, 14 reference images",
    "gen4_image": "Runway Gen-4 Image — photorealistic cinematic stills",
}

VIDEO_MODELS: dict[str, str] = {
    "veo3.1": "Veo 3.1 — highest quality image-to-video",
    "gen4_turbo": "Runway Gen-4 Turbo — cinematic image-to-video",
    "gen4.5": "Runway Gen-4.5 — image-to-video",
}
