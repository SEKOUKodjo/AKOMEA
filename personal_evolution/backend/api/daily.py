"""Matin, soir, journées, intentions, activités et réflexions."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models as m
from ..domain import INTENTION_STATUSES
from ..schemas import (
    ActivityIn,
    ActivityOut,
    DayMetrics,
    EveningIn,
    IntentionIn,
    IntentionOut,
    IntentionUpdate,
    MorningIn,
    ParseRequest,
    ReflectionIn,
    ReflectionOut,
)
from ..services import days as day_service
from .deps import get_session, not_found

router = APIRouter(tags=["quotidien"])


@router.post("/morning/parse")
def morning_parse(body: ParseRequest, session: Session = Depends(get_session)):
    """Analyse le texte (ou la transcription) du matin. Rien n'est enregistré comme intention avant validation."""
    return day_service.parse(session, body.text, "matin", body.date, body.media_id)


@router.post("/morning")
def morning(body: MorningIn, session: Session = Depends(get_session)):
    day = day_service.save_morning(session, body)
    return day_service.day_detail(session, day)


@router.post("/evening/parse")
def evening_parse(body: ParseRequest, session: Session = Depends(get_session)):
    return day_service.parse(session, body.text, "soir", body.date, body.media_id)


@router.post("/evening")
def evening(body: EveningIn, session: Session = Depends(get_session)):
    try:
        day = day_service.save_evening(session, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return day_service.day_detail(session, day)


@router.get("/days")
def list_days(start: date | None = None, end: date | None = None, limit: int = Query(60, le=1000),
              session: Session = Depends(get_session)):
    q = session.query(m.Day)
    if start:
        q = q.filter(m.Day.date >= start)
    if end:
        q = q.filter(m.Day.date <= end)
    out = []
    for d in q.order_by(m.Day.date.desc()).limit(limit).all():
        detail = day_service.day_detail(session, d)
        out.append({"date": str(d.date), "summary": detail["summary"], "mood": d.mood, "energy": d.energy,
                    "highlight": d.highlight, "morning_done": d.morning_done_at is not None,
                    "evening_done": d.evening_done_at is not None})
    return out


@router.get("/days/{day}")
def get_day(day: date, session: Session = Depends(get_session)):
    obj = session.query(m.Day).filter_by(date=day).first()
    if obj is None:
        return {"day": {"id": None, "date": str(day)}, "intentions": [], "activities": [], "reflections": [],
                "media": [], "summary": {"n_intentions": 0, "n_done": 0, "n_reviewed": 0, "completion_rate": None,
                                         "planned_minutes": 0, "actual_minutes": 0}}
    return day_service.day_detail(session, obj)


@router.patch("/days/{day}")
def update_day(day: date, body: DayMetrics, session: Session = Depends(get_session)):
    obj = day_service.get_or_create(session, day)
    day_service.apply_metrics(obj, body)
    session.commit()
    return day_service.day_detail(session, obj)


@router.post("/intentions", response_model=IntentionOut)
def add_intention(body: IntentionIn, day: date | None = None, session: Session = Depends(get_session)):
    d = day_service.get_or_create(session, day)
    it = m.Intention(day_id=d.id, position=len(d.intentions), **body.model_dump())
    session.add(it)
    session.commit()
    return it


@router.patch("/intentions/{intention_id}", response_model=IntentionOut)
def update_intention(intention_id: int, body: IntentionUpdate, session: Session = Depends(get_session)):
    it = session.get(m.Intention, intention_id)
    if it is None:
        raise not_found("Intention")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in INTENTION_STATUSES:
        raise HTTPException(400, "Statut inconnu")
    for k, v in data.items():
        setattr(it, k, v)
    if "status" in data and data["status"] != "prevu":
        it.reviewed_at = m.now()
    session.commit()
    return it


@router.delete("/intentions/{intention_id}")
def delete_intention(intention_id: int, session: Session = Depends(get_session)):
    it = session.get(m.Intention, intention_id)
    if it is None:
        raise not_found("Intention")
    session.delete(it)
    session.commit()
    return {"ok": True}


@router.get("/activities", response_model=list[ActivityOut])
def list_activities(start: date | None = None, end: date | None = None, dimension: str | None = None,
                    category: str | None = None, limit: int = Query(200, le=5000),
                    session: Session = Depends(get_session)):
    q = session.query(m.Activity).join(m.Day)
    if start:
        q = q.filter(m.Day.date >= start)
    if end:
        q = q.filter(m.Day.date <= end)
    if dimension:
        q = q.filter(m.Activity.dimension == dimension)
    if category:
        q = q.filter(m.Activity.category == category)
    return q.order_by(m.Day.date.desc(), m.Activity.id.desc()).limit(limit).all()


@router.post("/activities", response_model=ActivityOut)
def add_activity(body: ActivityIn, session: Session = Depends(get_session)):
    return day_service.add_activity(session, body)


@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: int, session: Session = Depends(get_session)):
    act = session.get(m.Activity, activity_id)
    if act is None:
        raise not_found("Activité")
    session.delete(act)
    session.commit()
    return {"ok": True}


@router.get("/reflections", response_model=list[ReflectionOut])
def list_reflections(kind: str | None = None, dimension: str | None = None, limit: int = Query(100, le=2000),
                     session: Session = Depends(get_session)):
    q = session.query(m.Reflection).join(m.Day)
    if kind:
        q = q.filter(m.Reflection.kind == kind)
    if dimension:
        q = q.filter(m.Reflection.dimension == dimension)
    return q.order_by(m.Day.date.desc(), m.Reflection.id.desc()).limit(limit).all()


@router.post("/reflections", response_model=ReflectionOut)
def add_reflection(body: ReflectionIn, session: Session = Depends(get_session)):
    d = day_service.get_or_create(session, body.date)
    ref = m.Reflection(day_id=d.id, **body.model_dump(exclude={"date"}))
    session.add(ref)
    session.commit()
    return ref


@router.delete("/reflections/{reflection_id}")
def delete_reflection(reflection_id: int, session: Session = Depends(get_session)):
    ref = session.get(m.Reflection, reflection_id)
    if ref is None:
        raise not_found("Réflexion")
    session.delete(ref)
    session.commit()
    return {"ok": True}


@router.get("/sources/{source_id}")
def get_source(source_id: int, session: Session = Depends(get_session)):
    """Remonte à la donnée brute d'origine et à l'historique des extractions."""
    src = session.get(m.Source, source_id)
    if src is None:
        raise not_found("Source")
    return {
        "id": src.id, "kind": src.kind, "moment": src.moment, "raw_text": src.raw_text, "media_id": src.media_id,
        "created_at": src.created_at.isoformat(),
        "extractions": [{"id": e.id, "engine": e.engine, "version": e.engine_version, "status": e.status,
                         "proposed": e.proposed, "validated": e.validated,
                         "validated_at": e.validated_at.isoformat() if e.validated_at else None}
                        for e in src.extractions],
    }
