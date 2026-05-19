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


class PaperContent(BaseModel):
    title: str
    abstract: str
    body: str
    source: str  # file path or arxiv ID


class ScienceBrief(BaseModel):
    core_phenomenon: str
    counterintuitive_element: str
    philosophical_implication: str
    emotional_tones: list[EmotionalTone]
    visual_metaphors_in_paper: list[str]  # metaphors the authors themselves used
    one_line_essence: str  # the soul of the paper in one sentence


class CinematicConcept(BaseModel):
    logline: str
    scene_description: str  # written like a screenplay direction
    mood_keywords: list[str]
    color_palette: list[str]
    lighting_style: str
    film_references: list[str]
    runway_prompt: str  # final generation prompt for Runway Gen-4 Image
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
