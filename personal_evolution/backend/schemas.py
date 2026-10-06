"""Schémas d'échange de l'API (Pydantic)."""
from __future__ import annotations

from datetime import date as Date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DayMetrics(BaseModel):
    sleep_hours: float | None = Field(None, ge=0, le=24)
    sleep_quality: int | None = Field(None, ge=1, le=5)
    energy: int | None = Field(None, ge=1, le=5)
    motivation: int | None = Field(None, ge=1, le=5)
    mood: int | None = Field(None, ge=1, le=5)
    stress: int | None = Field(None, ge=1, le=5)
    fatigue: int | None = Field(None, ge=1, le=5)
    screen_minutes: int | None = Field(None, ge=0, le=1440)
    sedentary_minutes: int | None = Field(None, ge=0, le=1440)
    water_liters: float | None = Field(None, ge=0, le=15)
    steps: int | None = Field(None, ge=0)
    professional_contribution: str | None = None
    highlight: str | None = None
    general_comment: str | None = None


class DayOut(ORM, DayMetrics):
    id: int
    date: Date
    morning_done_at: datetime | None = None
    evening_done_at: datetime | None = None


class ParseRequest(BaseModel):
    text: str
    date: Date | None = None
    media_id: int | None = None  # si le texte provient d'une transcription


class IntentionIn(BaseModel):
    description: str = Field(min_length=1)
    dimension: str | None = None
    category: str | None = None
    priority: int = Field(2, ge=1, le=3)
    estimated_minutes: int | None = Field(None, ge=0, le=1440)
    goal_id: int | None = None


class IntentionUpdate(BaseModel):
    description: str | None = None
    dimension: str | None = None
    category: str | None = None
    priority: int | None = Field(None, ge=1, le=3)
    estimated_minutes: int | None = Field(None, ge=0, le=1440)
    goal_id: int | None = None
    status: str | None = None
    actual_minutes: int | None = Field(None, ge=0, le=1440)
    result: str | None = None
    reason: str | None = None


class IntentionOut(ORM):
    id: int
    day_id: int
    goal_id: int | None
    dimension: str | None
    category: str | None
    description: str
    priority: int
    estimated_minutes: int | None
    status: str
    actual_minutes: int | None
    result: str | None
    reason: str | None
    source_id: int | None


class MorningIn(BaseModel):
    date: Date | None = None
    intentions: list[IntentionIn] = []
    metrics: DayMetrics | None = None
    extraction_id: int | None = None
    raw_text: str | None = None
    replace: bool = False  # remplace les intentions encore "prévues" du jour


class ReviewIn(BaseModel):
    intention_id: int
    status: str
    actual_minutes: int | None = Field(None, ge=0, le=1440)
    result: str | None = None
    reason: str | None = None


class ActivityIn(BaseModel):
    description: str = Field(min_length=1)
    date: Date | None = None
    dimension: str | None = None
    category: str | None = None
    intention_id: int | None = None
    skill_id: int | None = None
    start_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    duration_minutes: int | None = Field(None, ge=0, le=1440)
    result: str | None = None


class ActivityOut(ORM):
    id: int
    day_id: int
    intention_id: int | None
    skill_id: int | None
    dimension: str | None
    category: str | None
    description: str
    start_time: str | None
    end_time: str | None
    duration_minutes: int | None
    result: str | None
    planned: bool
    source_id: int | None


class ReflectionIn(BaseModel):
    content: str = Field(min_length=1)
    date: Date | None = None
    dimension: str | None = None
    kind: str = "reflexion"
    reference: str | None = None
    tags: str | None = None
    source_type: str = "texte"


class ReflectionOut(ORM):
    id: int
    day_id: int
    dimension: str | None
    kind: str
    content: str
    reference: str | None
    tags: str | None
    source_type: str
    created_at: datetime


class EveningIn(BaseModel):
    date: Date | None = None
    reviews: list[ReviewIn] = []
    activities: list[ActivityIn] = []
    reflections: list[ReflectionIn] = []
    metrics: DayMetrics | None = None
    extraction_id: int | None = None
    raw_text: str | None = None


class MediaOut(ORM):
    id: int
    day_id: int | None
    type: str
    moment: str | None
    dimension: str | None
    file_path: str
    original_name: str | None
    mime_type: str | None
    size_bytes: int | None
    sha256: str | None
    caption: str | None
    transcription: str | None
    transcription_status: str | None
    transcription_engine: str | None
    transcription_error: str | None
    created_at: datetime


class MediaUpdate(BaseModel):
    caption: str | None = None
    dimension: str | None = None
    transcription: str | None = None  # correction manuelle, l'audio reste intact


class GoalIn(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    dimension: str | None = None
    horizon: str = "mensuel"
    status: str = "actif"
    parent_id: int | None = None
    start_date: Date | None = None
    target_date: Date | None = None
    metric: str | None = None
    target_value: float | None = None
    abandon_reason: str | None = None


class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    dimension: str | None = None
    horizon: str | None = None
    status: str | None = None
    parent_id: int | None = None
    start_date: Date | None = None
    target_date: Date | None = None
    metric: str | None = None
    target_value: float | None = None
    abandon_reason: str | None = None


class GoalOut(ORM):
    id: int
    parent_id: int | None
    title: str
    description: str | None
    dimension: str | None
    horizon: str
    status: str
    start_date: Date | None
    target_date: Date | None
    completed_at: Date | None
    metric: str | None
    target_value: float | None
    abandon_reason: str | None


class SkillIn(BaseModel):
    name: str = Field(min_length=1)
    category: str | None = None
    dimension: str | None = "etudes"
    description: str | None = None
    target_level: int | None = Field(None, ge=1, le=5)
    keywords: str | None = None


class SkillOut(ORM):
    id: int
    name: str
    category: str | None
    dimension: str | None
    description: str | None
    target_level: int | None
    keywords: str | None


class SkillProgressIn(BaseModel):
    date: Date | None = None
    self_rating: float | None = Field(None, ge=0, le=5)
    objective_score: float | None = Field(None, ge=0, le=100)
    evidence_type: str | None = None
    evidence: str | None = None
    comment: str | None = None


class SkillProgressOut(ORM, SkillProgressIn):
    id: int
    skill_id: int
    date: Date


class DecisionIn(BaseModel):
    title: str = Field(min_length=1)
    date: Date | None = None
    dimension: str | None = None
    context: str | None = None
    reasons: str | None = None
    alternatives: str | None = None
    choice: str | None = None
    expected_outcome: str | None = None
    confidence: int | None = Field(None, ge=1, le=5)
    review_date: Date | None = None
    outcome: str | None = None
    outcome_rating: int | None = Field(None, ge=1, le=5)
    lessons: str | None = None


class DecisionOut(ORM, DecisionIn):
    id: int
    date: Date


class ExperimentIn(BaseModel):
    title: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    intervention: str | None = None
    metric: str = "completion_rate"
    start_date: Date | None = None
    end_date: Date | None = None
    status: str = "en_cours"
    conclusion: str | None = None


class ExperimentOut(ORM, ExperimentIn):
    id: int
    start_date: Date


class PersonIn(BaseModel):
    name: str = Field(min_length=1)
    relation: str | None = None
    notes: str | None = None
    contact_every_days: int | None = Field(None, ge=1)


class PersonOut(ORM, PersonIn):
    id: int


class InteractionIn(BaseModel):
    person_id: int
    date: Date | None = None
    kind: str = "conversation"
    note: str | None = None


class InteractionOut(ORM):
    id: int
    person_id: int
    date: Date
    kind: str
    note: str | None


class ScenarioIn(BaseModel):
    category: str | None = None
    dimension: str | None = None
    minutes_per_day: int = Field(gt=0, le=1440)
    days: int = Field(gt=0, le=3650)
    days_per_week: int = Field(7, ge=1, le=7)


class PredictIn(BaseModel):
    description: str | None = None
    dimension: str | None = None
    category: str | None = None
    estimated_minutes: int | None = None
    priority: int = 2
    n_intentions: int | None = None
    date: Date | None = None


class Payload(BaseModel):
    data: dict[str, Any]
