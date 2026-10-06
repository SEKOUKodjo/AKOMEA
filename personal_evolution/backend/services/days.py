"""Cycle quotidien : intention du matin, bilan du soir, provenance."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ai.nlp import extract

from .. import models as m
from ..domain import CLOSED_STATUSES, INTENTION_STATUSES
from ..schemas import DayMetrics, EveningIn, MorningIn


def get_or_create(session: Session, day: date | None = None) -> m.Day:
    day = day or date.today()
    obj = session.query(m.Day).filter_by(date=day).first()
    if obj is None:
        obj = m.Day(date=day)
        session.add(obj)
        session.flush()
    return obj


def apply_metrics(day: m.Day, metrics: DayMetrics | None) -> None:
    if metrics is None:
        return
    for key, value in metrics.model_dump(exclude_unset=True).items():
        setattr(day, key, value)


def _intention_dicts(day: m.Day) -> list[dict]:
    return [
        {"id": i.id, "description": i.description, "category": i.category, "dimension": i.dimension,
         "estimated_minutes": i.estimated_minutes}
        for i in day.intentions
    ]


def record_source(session: Session, day: m.Day, text: str, moment: str, media_id: int | None) -> m.Source:
    """Conserve le texte brut. Si une transcription existe déjà pour ce média, on la réutilise."""
    if media_id:
        src = session.query(m.Source).filter_by(media_id=media_id).first()
        if src is not None:
            src.day_id = src.day_id or day.id
            src.moment = src.moment or moment
            if not src.raw_text:
                src.raw_text = text
            return src
    src = m.Source(day_id=day.id, kind="audio" if media_id else "texte", moment=moment, raw_text=text, media_id=media_id)
    session.add(src)
    session.flush()
    return src


def parse(session: Session, text: str, moment: str, day_date: date | None, media_id: int | None = None) -> dict:
    """Analyse un texte et enregistre la proposition (jamais appliquée sans validation)."""
    day = get_or_create(session, day_date)
    source = record_source(session, day, text, moment, media_id)
    if moment == "matin":
        result = extract.extract_intentions(text)
    else:
        result = extract.extract_review(text, _intention_dicts(day))
    proposed = result.to_dict()
    ext = m.Extraction(source_id=source.id, engine=result.engine, engine_version=result.version, proposed=proposed)
    session.add(ext)
    session.commit()
    return {"extraction_id": ext.id, "source_id": source.id, "date": str(day.date), **proposed}


def _close_extraction(session: Session, extraction_id: int | None, validated: dict) -> m.Extraction | None:
    """Marque la proposition comme validée telle quelle ou corrigée par l'utilisateur."""
    if not extraction_id:
        return None
    ext = session.get(m.Extraction, extraction_id)
    if ext is None:
        return None
    proposed_keys = [
        (i.get("description"), i.get("dimension"), i.get("minutes")) for i in ext.proposed.get("items", [])
    ]
    validated_keys = [
        (i.get("description"), i.get("dimension"), i.get("minutes")) for i in validated.get("items", [])
    ]
    ext.validated = validated
    ext.status = "valide" if proposed_keys == validated_keys else "corrige"
    ext.validated_at = m.now()
    return ext


def save_morning(session: Session, data: MorningIn) -> m.Day:
    day = get_or_create(session, data.date)
    apply_metrics(day, data.metrics)
    ext = _close_extraction(
        session, data.extraction_id,
        {"items": [{"description": i.description, "dimension": i.dimension, "minutes": i.estimated_minutes,
                    "category": i.category, "priority": i.priority} for i in data.intentions]},
    )
    source_id = ext.source_id if ext else None
    if source_id is None and data.raw_text:
        source_id = record_source(session, day, data.raw_text, "matin", None).id
    if source_id is None and data.intentions:
        src = m.Source(day_id=day.id, kind="formulaire", moment="matin")
        session.add(src)
        session.flush()
        source_id = src.id
    if data.replace:
        for it in list(day.intentions):
            if it.status == "prevu" and not it.activities:
                session.delete(it)
        session.flush()
    start = len(day.intentions)
    for pos, item in enumerate(data.intentions):
        session.add(m.Intention(
            day_id=day.id, goal_id=item.goal_id, dimension=item.dimension, category=item.category,
            description=item.description.strip(), priority=item.priority, estimated_minutes=item.estimated_minutes,
            position=start + pos, source_id=source_id,
        ))
    day.morning_done_at = day.morning_done_at or m.now()
    session.commit()
    session.refresh(day)
    return day


def save_evening(session: Session, data: EveningIn) -> m.Day:
    day = get_or_create(session, data.date)
    apply_metrics(day, data.metrics)
    ext = _close_extraction(
        session, data.extraction_id,
        {"items": [{"description": a.description, "dimension": a.dimension, "minutes": a.duration_minutes}
                   for a in data.activities],
         "reviews": [r.model_dump() for r in data.reviews]},
    )
    source_id = ext.source_id if ext else None
    if source_id is None and data.raw_text:
        source_id = record_source(session, day, data.raw_text, "soir", None).id

    for rv in data.reviews:
        it = session.get(m.Intention, rv.intention_id)
        if it is None or it.day_id != day.id:
            continue
        if rv.status not in INTENTION_STATUSES:
            raise ValueError(f"Statut inconnu : {rv.status}")
        it.status = rv.status
        it.actual_minutes = rv.actual_minutes
        it.result = rv.result or it.result
        it.reason = rv.reason or it.reason
        it.reviewed_at = m.now()
        # Une action réalisée sans activité détaillée devient une activité, pour le suivi du temps.
        if rv.status in ("realise", "partiel") and not it.activities:
            session.add(m.Activity(
                day_id=day.id, intention_id=it.id, dimension=it.dimension, category=it.category,
                description=it.description, duration_minutes=rv.actual_minutes, result=rv.result,
                planned=True, source_id=source_id,
            ))

    for act in data.activities:
        add_activity(session, act, day=day, source_id=source_id, commit=False)

    for ref in data.reflections:
        session.add(m.Reflection(day_id=day.id, dimension=ref.dimension, kind=ref.kind, content=ref.content,
                                 reference=ref.reference, tags=ref.tags, source_type=ref.source_type,
                                 source_id=source_id))
    day.evening_done_at = m.now()
    session.commit()
    session.refresh(day)
    return day


def add_activity(session: Session, data, *, day: m.Day | None = None, source_id: int | None = None,
                 commit: bool = True) -> m.Activity:
    from . import skills as skill_service

    day = day or get_or_create(session, data.date)
    minutes = data.duration_minutes
    if minutes is None and data.start_time and data.end_time:
        h1, m1 = map(int, data.start_time.split(":"))
        h2, m2 = map(int, data.end_time.split(":"))
        minutes = (h2 * 60 + m2 - h1 * 60 - m1) % (24 * 60)
    intention = session.get(m.Intention, data.intention_id) if data.intention_id else None
    act = m.Activity(
        day_id=day.id, intention_id=intention.id if intention else None, skill_id=data.skill_id,
        dimension=data.dimension or (intention.dimension if intention else None),
        category=data.category or (intention.category if intention else None),
        description=data.description.strip(), start_time=data.start_time, end_time=data.end_time,
        duration_minutes=minutes, result=data.result, planned=intention is not None, source_id=source_id,
    )
    if act.skill_id is None:
        act.skill_id = skill_service.match_skill_id(session, act.category, act.description)
    session.add(act)
    if intention is not None:
        session.flush()
        total = sum(a.duration_minutes or 0 for a in intention.activities)
        intention.actual_minutes = total or intention.actual_minutes
        if intention.status == "prevu":
            est = intention.estimated_minutes
            intention.status = "partiel" if est and total and total < 0.75 * est else "realise"
        if data.result:
            intention.result = data.result
    if commit:
        session.commit()
        session.refresh(act)
    return act


def day_detail(session: Session, day: m.Day) -> dict:
    from ..schemas import ActivityOut, DayOut, IntentionOut, MediaOut, ReflectionOut

    intentions = sorted(day.intentions, key=lambda i: (i.position, i.id))
    planned = sum(i.estimated_minutes or 0 for i in intentions)
    actual = sum(a.duration_minutes or 0 for a in day.activities)
    closed = [i for i in intentions if i.status in CLOSED_STATUSES]
    done = [i for i in intentions if i.status in ("realise", "partiel")]
    return {
        "day": DayOut.model_validate(day).model_dump(mode="json"),
        "intentions": [IntentionOut.model_validate(i).model_dump(mode="json") for i in intentions],
        "activities": [ActivityOut.model_validate(a).model_dump(mode="json") for a in day.activities],
        "reflections": [ReflectionOut.model_validate(r).model_dump(mode="json") for r in day.reflections],
        "media": [MediaOut.model_validate(x).model_dump(mode="json") for x in day.media],
        "summary": {
            "n_intentions": len(intentions),
            "n_done": len(done),
            "n_reviewed": len(closed),
            "completion_rate": round(len(done) / len(intentions), 3) if intentions else None,
            "planned_minutes": planned,
            "actual_minutes": actual,
        },
    }
