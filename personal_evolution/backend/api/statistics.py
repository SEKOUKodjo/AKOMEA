"""Statistiques, tendances, prédictions, scénarios, mémoire et système."""
from __future__ import annotations

import platform
import socket
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ai.ml import predict
from ai.transcription import whisper_local

from .. import models as m
from ..config import settings
from ..domain import DIMENSIONS, HORIZONS, INTENTION_STATUSES, REFLECTION_KINDS
from ..schemas import PredictIn, ScenarioIn
from ..services import analytics, ask, backup, memory
from .deps import get_session

router = APIRouter()


def _period(days: int | None, start: date | None, end: date | None) -> tuple[date | None, date | None]:
    if days and not start:
        end = end or date.today()
        start = end - timedelta(days=days - 1)
    return start, end


@router.get("/statistics/summary", tags=["statistiques"])
def stats_summary(days: int | None = None, start: date | None = None, end: date | None = None,
                  session: Session = Depends(get_session)):
    return analytics.summary(session, *_period(days, start, end))


@router.get("/statistics/daily", tags=["statistiques"])
def stats_daily(days: int | None = 90, start: date | None = None, end: date | None = None,
                session: Session = Depends(get_session)):
    start, end = _period(days, start, end)
    daily = analytics.daily_series(analytics.load_frames(session, start, end), start, end)
    df = daily.reset_index()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return {"labels": analytics.METRIC_LABELS, "rows": df.astype(object).where(df.notna(), None).to_dict("records")}


@router.get("/statistics/weekly", tags=["statistiques"])
def stats_weekly(days: int | None = 365, session: Session = Depends(get_session)):
    start, end = _period(days, None, None)
    w = analytics.weekly(analytics.daily_series(analytics.load_frames(session, start, end), start, end)).reset_index()
    if w.empty:
        return []
    w["date"] = w["date"].dt.strftime("%Y-%m-%d")
    return w.round(3).astype(object).where(w.notna(), None).to_dict("records")


@router.get("/statistics/calibration", tags=["statistiques"])
def stats_calibration(days: int | None = None, session: Session = Depends(get_session)):
    return analytics.calibration(analytics.load_frames(session, *_period(days, None, None)))


@router.get("/statistics/abandons", tags=["statistiques"])
def stats_abandons(days: int | None = None, session: Session = Depends(get_session)):
    return analytics.abandons(analytics.load_frames(session, *_period(days, None, None)))


@router.get("/statistics/trends", tags=["statistiques"])
def stats_trends(window_days: int = Query(21, ge=7, le=180), session: Session = Depends(get_session)):
    fr = analytics.load_frames(session)
    return analytics.trends(analytics.daily_series(fr), window_days, fr=fr)


@router.get("/statistics/anomalies", tags=["statistiques"])
def stats_anomalies(session: Session = Depends(get_session)):
    return analytics.anomalies(analytics.daily_series(analytics.load_frames(session)))


@router.get("/statistics/correlations", tags=["statistiques"])
def stats_correlations(days: int | None = None, session: Session = Depends(get_session)):
    start, end = _period(days, None, None)
    return analytics.correlations(analytics.daily_series(analytics.load_frames(session, start, end), start, end))


@router.get("/statistics/weekdays", tags=["statistiques"])
def stats_weekdays(session: Session = Depends(get_session)):
    return analytics.weekday_profile(analytics.daily_series(analytics.load_frames(session)))


@router.get("/statistics/compare", tags=["statistiques"])
def stats_compare(a_start: date, a_end: date, b_start: date, b_end: date, session: Session = Depends(get_session)):
    return analytics.compare_periods(session, (a_start, a_end), (b_start, b_end))


@router.get("/insights", tags=["recommandations"])
def insights(days: int | None = None, session: Session = Depends(get_session)):
    return analytics.insights(session, *_period(days, None, None))


@router.post("/predict/completion", tags=["prediction"])
def predict_completion(body: PredictIn, session: Session = Depends(get_session)):
    fr = analytics.load_frames(session)
    model = predict.fit_completion(fr.intentions, fr.days)
    return predict.predict_completion(model, body.model_dump())


@router.post("/predict/duration", tags=["prediction"])
def predict_duration(body: PredictIn, session: Session = Depends(get_session)):
    if not body.estimated_minutes:
        raise HTTPException(400, "estimated_minutes est requis")
    fr = analytics.load_frames(session)
    return predict.predict_duration(fr.intentions, body.category, body.dimension, body.estimated_minutes)


@router.get("/predict/day/{day}", tags=["prediction"])
def predict_day(day: date, session: Session = Depends(get_session)):
    """Probabilité de réalisation et durée probable pour chaque intention d'une journée."""
    d = session.query(m.Day).filter_by(date=day).first()
    if d is None:
        return []
    fr = analytics.load_frames(session, end=day - timedelta(days=1))
    model = predict.fit_completion(fr.intentions, fr.days)
    out = []
    for it in d.intentions:
        item = {"description": it.description, "dimension": it.dimension, "category": it.category,
                "estimated_minutes": it.estimated_minutes, "priority": it.priority,
                "n_intentions": len(d.intentions), "date": day}
        comp = predict.predict_completion(model, item)
        dur = (predict.predict_duration(fr.intentions, it.category, it.dimension, it.estimated_minutes)
               if it.estimated_minutes else None)
        existing = session.query(m.Prediction).filter_by(target="completion", subject_type="intention",
                                                          subject_id=it.id).first()
        if existing is None:
            session.add(m.Prediction(target="completion", subject_type="intention", subject_id=it.id,
                                     value=comp["probability"], lower=comp["interval"][0], upper=comp["interval"][1],
                                     model=comp["model"], n_training=comp["n_training"]))
        out.append({"intention_id": it.id, "description": it.description, "completion": comp, "duration": dur})
    session.commit()
    return out


@router.post("/simulate", tags=["prediction"])
def simulate(body: ScenarioIn, session: Session = Depends(get_session)):
    fr = analytics.load_frames(session)
    return predict.simulate_scenario(fr.intentions, fr.activities, category=body.category, dimension=body.dimension,
                                     minutes_per_day=body.minutes_per_day, days=body.days,
                                     days_per_week=body.days_per_week)


@router.get("/memory/search", tags=["memoire"])
def memory_search(q: str, kind: list[str] | None = Query(None), start: date | None = None, end: date | None = None,
                  dimension: str | None = None, limit: int = Query(30, le=200), session: Session = Depends(get_session)):
    return memory.search(session, q, kinds=kind, start=start, end=end, dimension=dimension, limit=limit)


@router.get("/memory/ask", tags=["memoire"])
def memory_ask(q: str, session: Session = Depends(get_session)):
    return ask.ask(session, q)


@router.post("/memory/rebuild", tags=["memoire"])
def memory_rebuild(session: Session = Depends(get_session)):
    return {"indexed": memory.rebuild(session)}


@router.get("/categories", tags=["referentiel"])
def categories(session: Session = Depends(get_session)):
    """Catégories déjà utilisées, pour l'autocomplétion."""
    rows = session.query(m.Intention.category, m.Intention.dimension).distinct().all()
    rows += session.query(m.Activity.category, m.Activity.dimension).distinct().all()
    seen = {}
    for cat, dim in rows:
        if cat:
            seen.setdefault(cat, dim)
    return [{"category": c, "dimension": d} for c, d in sorted(seen.items())]


@router.get("/meta", tags=["referentiel"])
def meta():
    return {
        "dimensions": [{"key": k, **v} for k, v in DIMENSIONS.items()],
        "horizons": [{"key": k, "label": v} for k, v in HORIZONS.items()],
        "statuses": [{"key": k, "label": v} for k, v in INTENTION_STATUSES.items()],
        "reflection_kinds": [{"key": k, "label": v} for k, v in REFLECTION_KINDS.items()],
        "metrics": [{"key": k, "label": v} for k, v in analytics.METRIC_LABELS.items()],
    }


def local_ips() -> list[str]:
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # aucune donnée envoyée, sert à connaître l'interface locale
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


@router.get("/system/info", tags=["systeme"])
def system_info(session: Session = Depends(get_session)):
    counts = {name: session.query(model).count() for name, model in
              [("jours", m.Day), ("intentions", m.Intention), ("activites", m.Activity), ("reflexions", m.Reflection),
               ("medias", m.Media), ("objectifs", m.Goal), ("competences", m.Skill), ("decisions", m.Decision)]}
    db_size = settings.database_path.stat().st_size if settings.database_path.exists() else 0
    return {
        "application": "Personal Evolution Intelligence", "version": "1.0.0",
        "database": str(settings.database_path), "database_mb": round(db_size / 1e6, 2),
        "storage": str(settings.storage_dir), "counts": counts, "local_ips": local_ips(),
        "transcription_engine": whisper_local.available_engine(), "pin_enabled": bool(settings.pin),
        "dashboard_port": settings.dashboard_port, "python": platform.python_version(),
    }


@router.post("/system/backup", tags=["systeme"])
def system_backup(include_media: bool = True):
    path = backup.create_backup(include_media=include_media)
    backup.prune(keep=30)
    return {"file": path.name, "size_mb": round(path.stat().st_size / 1e6, 2)}


@router.get("/system/backups", tags=["systeme"])
def system_backups():
    return backup.list_backups()


@router.get("/system/backups/{name}", tags=["systeme"])
def download_backup(name: str):
    path = settings.backup_dir / name
    if "/" in name or ".." in name or not path.exists():
        raise HTTPException(404, "Sauvegarde introuvable")
    return FileResponse(path, filename=name, media_type="application/zip")
