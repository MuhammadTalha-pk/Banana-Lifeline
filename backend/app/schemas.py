from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Language = Literal['en', 'ur']


class SourceRef(BaseModel):
    title: str
    source: str
    page: int | None = None
    score: float | None = None


class DiagnosisResponse(BaseModel):
    request_id: str
    status: Literal['completed', 'abstained']
    label: str
    display_name: str
    confidence: float = Field(ge=0, le=1)
    severity: Literal['low', 'medium', 'high', 'unknown']
    description: str | None = None
    treatment: list[str] = Field(default_factory=list)
    prevention: list[str] = Field(default_factory=list)
    additional_advice: list[str] = Field(default_factory=list)
    expert_recommended: bool = False
    model_scope: str = 'banana_leaf_only'
    sources: list[SourceRef] = Field(default_factory=list)
    warning: str | None = None


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=5000)
    language: Language = 'en'
    related_scan_id: str | None = None
    image_url: str | None = None
    audio_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    farm_name: str | None = None
    plot_sector: str | None = None
    row: str | None = None
    plant_number: str | None = None
    note: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    answer: str
    sources: list[SourceRef]
    confidence: float | None = None


class TranscriptionResponse(BaseModel):
    transcript: str
    language: Language


class HealthResponse(BaseModel):
    ok: bool
    vision_ready: bool
    rag_ready: bool
    generation_ready: bool
    speech_enabled: bool
    details: dict[str, str | bool | None]
