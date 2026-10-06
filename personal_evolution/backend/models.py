"""Modèle de données de PEI.

Principe central : Intention -> Action -> Résultat, avec une provenance
traçable (Source -> Extraction -> données structurées).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


class Base(DeclarativeBase):
    pass


class Day(Base):
    """Une journée et ses indicateurs déclarés."""

    __tablename__ = "days"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    sleep_quality: Mapped[int | None] = mapped_column(Integer)
    energy: Mapped[int | None] = mapped_column(Integer)
    motivation: Mapped[int | None] = mapped_column(Integer)
    mood: Mapped[int | None] = mapped_column(Integer)
    stress: Mapped[int | None] = mapped_column(Integer)
    fatigue: Mapped[int | None] = mapped_column(Integer)
    screen_minutes: Mapped[int | None] = mapped_column(Integer)
    sedentary_minutes: Mapped[int | None] = mapped_column(Integer)
    water_liters: Mapped[float | None] = mapped_column(Float)
    steps: Mapped[int | None] = mapped_column(Integer)
    professional_contribution: Mapped[str | None] = mapped_column(Text)
    highlight: Mapped[str | None] = mapped_column(Text)
    general_comment: Mapped[str | None] = mapped_column(Text)
    morning_done_at: Mapped[datetime | None] = mapped_column(DateTime)
    evening_done_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

    intentions: Mapped[list[Intention]] = relationship(back_populates="day", cascade="all, delete-orphan")
    activities: Mapped[list[Activity]] = relationship(back_populates="day", cascade="all, delete-orphan")
    reflections: Mapped[list[Reflection]] = relationship(back_populates="day", cascade="all, delete-orphan")
    media: Mapped[list[Media]] = relationship(back_populates="day")


class Goal(Base):
    """Objectif hiérarchique : vision > long terme > annuel > mensuel > hebdomadaire."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    dimension: Mapped[str | None] = mapped_column(String(40), index=True)
    horizon: Mapped[str] = mapped_column(String(30), default="mensuel")
    status: Mapped[str] = mapped_column(String(30), default="actif")
    start_date: Mapped[date | None] = mapped_column(Date)
    target_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[date | None] = mapped_column(Date)
    metric: Mapped[str | None] = mapped_column(String(200))
    target_value: Mapped[float | None] = mapped_column(Float)
    abandon_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    parent: Mapped[Goal | None] = relationship(remote_side="Goal.id", back_populates="children")
    children: Mapped[list[Goal]] = relationship(back_populates="parent")
    intentions: Mapped[list[Intention]] = relationship(back_populates="goal")


class Source(Base):
    """Donnée brute d'origine (texte saisi, audio, formulaire). Jamais modifiée."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int | None] = mapped_column(ForeignKey("days.id", ondelete="SET NULL"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # texte, audio, formulaire, image, video
    moment: Mapped[str | None] = mapped_column(String(20))  # matin, journee, soir
    raw_text: Mapped[str | None] = mapped_column(Text)
    media_id: Mapped[int | None] = mapped_column(ForeignKey("media.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    extractions: Mapped[list[Extraction]] = relationship(back_populates="source", cascade="all, delete-orphan")


class Extraction(Base):
    """Proposition produite par l'IA, puis validée ou corrigée par l'utilisateur."""

    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    engine: Mapped[str] = mapped_column(String(80))
    engine_version: Mapped[str] = mapped_column(String(20))
    proposed: Mapped[dict] = mapped_column(JSON)
    validated: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="propose")  # propose, valide, corrige, rejete
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime)

    source: Mapped[Source] = relationship(back_populates="extractions")


class Intention(Base):
    """Ce que je voulais faire aujourd'hui."""

    __tablename__ = "intentions"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id", ondelete="CASCADE"), index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"), index=True)
    dimension: Mapped[str | None] = mapped_column(String(40), index=True)
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1 haute, 2 normale, 3 basse
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="prevu")
    actual_minutes: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)  # raison d'un abandon ou d'un écart
    position: Mapped[int] = mapped_column(Integer, default=0)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)

    day: Mapped[Day] = relationship(back_populates="intentions")
    goal: Mapped[Goal | None] = relationship(back_populates="intentions")
    activities: Mapped[list[Activity]] = relationship(back_populates="intention")


class Activity(Base):
    """Ce que j'ai réellement fait, et ce que cela a produit."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id", ondelete="CASCADE"), index=True)
    intention_id: Mapped[int | None] = mapped_column(ForeignKey("intentions.id", ondelete="SET NULL"), index=True)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), index=True)
    dimension: Mapped[str | None] = mapped_column(String(40), index=True)
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text)
    start_time: Mapped[str | None] = mapped_column(String(5))  # HH:MM
    end_time: Mapped[str | None] = mapped_column(String(5))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[str | None] = mapped_column(Text)
    planned: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    day: Mapped[Day] = relationship(back_populates="activities")
    intention: Mapped[Intention | None] = relationship(back_populates="activities")
    skill: Mapped[Skill | None] = relationship(back_populates="activities")


class Media(Base):
    """Métadonnées d'un fichier. Le fichier lui même reste dans storage/."""

    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int | None] = mapped_column(ForeignKey("days.id", ondelete="SET NULL"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    moment: Mapped[str | None] = mapped_column(String(20))
    dimension: Mapped[str | None] = mapped_column(String(40))
    file_path: Mapped[str] = mapped_column(String(500))  # relatif à storage/
    original_name: Mapped[str | None] = mapped_column(String(300))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    caption: Mapped[str | None] = mapped_column(Text)
    transcription: Mapped[str | None] = mapped_column(Text)
    transcription_status: Mapped[str | None] = mapped_column(String(20))  # en_attente, en_cours, termine, indisponible, erreur
    transcription_engine: Mapped[str | None] = mapped_column(String(80))
    transcription_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    day: Mapped[Day | None] = relationship(back_populates="media")


class Reflection(Base):
    __tablename__ = "reflections"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id", ondelete="CASCADE"), index=True)
    dimension: Mapped[str | None] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="reflexion")
    content: Mapped[str] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(String(200))  # passage biblique, livre, lien
    tags: Mapped[str | None] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(20), default="texte")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    day: Mapped[Day] = relationship(back_populates="reflections")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str | None] = mapped_column(String(120))
    dimension: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    target_level: Mapped[int | None] = mapped_column(Integer)
    keywords: Mapped[str | None] = mapped_column(String(300))  # pour relier les activités
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    progress: Mapped[list[SkillProgress]] = relationship(back_populates="skill", cascade="all, delete-orphan", order_by="SkillProgress.date")
    activities: Mapped[list[Activity]] = relationship(back_populates="skill")


class SkillProgress(Base):
    __tablename__ = "skill_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date)
    self_rating: Mapped[float | None] = mapped_column(Float)  # 1 à 5
    objective_score: Mapped[float | None] = mapped_column(Float)  # 0 à 100 (test, exercice)
    evidence_type: Mapped[str | None] = mapped_column(String(40))  # exercice, projet, test, formation, production
    evidence: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    skill: Mapped[Skill] = relationship(back_populates="progress")


class Decision(Base):
    """Journal des décisions : décision, justification, puis résultat."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(300))
    dimension: Mapped[str | None] = mapped_column(String(40))
    context: Mapped[str | None] = mapped_column(Text)
    reasons: Mapped[str | None] = mapped_column(Text)
    alternatives: Mapped[str | None] = mapped_column(Text)
    choice: Mapped[str | None] = mapped_column(Text)
    expected_outcome: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int | None] = mapped_column(Integer)  # 1 à 5 au moment de décider
    review_date: Mapped[date | None] = mapped_column(Date)
    outcome: Mapped[str | None] = mapped_column(Text)
    outcome_rating: Mapped[int | None] = mapped_column(Integer)  # 1 à 5 a posteriori
    lessons: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Experiment(Base):
    """Expérience personnelle : une hypothèse testée sur une période."""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    hypothesis: Mapped[str] = mapped_column(Text)
    intervention: Mapped[str | None] = mapped_column(Text)
    metric: Mapped[str] = mapped_column(String(60))  # colonne de la série quotidienne
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="en_cours")
    conclusion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    relation: Mapped[str | None] = mapped_column(String(60))  # famille, ami, collègue, mentor
    notes: Mapped[str | None] = mapped_column(Text)
    contact_every_days: Mapped[int | None] = mapped_column(Integer)  # relation à entretenir
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    interactions: Mapped[list[Interaction]] = relationship(back_populates="person", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(30), default="conversation")  # appel, visite, rencontre, message
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    person: Mapped[Person] = relationship(back_populates="interactions")


class Prediction(Base):
    """Trace des prédictions émises, pour pouvoir les comparer à la réalité."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[str] = mapped_column(String(60))  # completion, duree
    subject_type: Mapped[str | None] = mapped_column(String(40))
    subject_id: Mapped[int | None] = mapped_column(Integer)
    value: Mapped[float] = mapped_column(Float)
    lower: Mapped[float | None] = mapped_column(Float)
    upper: Mapped[float | None] = mapped_column(Float)
    model: Mapped[str] = mapped_column(String(80))
    n_training: Mapped[int | None] = mapped_column(Integer)
    features: Mapped[dict | None] = mapped_column(JSON)
    actual: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    __table_args__ = (UniqueConstraint("target", "subject_type", "subject_id", name="uq_prediction_subject"),)
