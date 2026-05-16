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
    "gen4_image": "Runway Gen-4 Image — highest quality, photorealistic cinematic stills",
}

VIDEO_MODELS: dict[str, str] = {
    "gen4_turbo": "Runway Gen-4 Turbo — best quality, 5 or 10 second clips",
    "gen3a_turbo": "Runway Gen-3 Alpha Turbo — faster, more affordable",
}
