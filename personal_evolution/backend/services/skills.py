"""Suivi des compétences : auto évaluation et preuves observables."""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from ai.nlp.extract import fold

from .. import models as m


def _keywords(skill: m.Skill) -> list[str]:
    words = [skill.name] + [k for k in re.split(r"[,;]", skill.keywords or "") if k.strip()]
    return [fold(w.strip()) for w in words if w.strip()]


def match_skill_id(session: Session, category: str | None, description: str | None) -> int | None:
    """Relie automatiquement une activité à une compétence via son nom ou ses mots clés."""
    text = fold(f"{category or ''} {description or ''}")
    if not text.strip():
        return None
    best, best_len = None, 0
    for skill in session.query(m.Skill).all():
        for kw in _keywords(skill):
            if kw and re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text) and len(kw) > best_len:
                best, best_len = skill.id, len(kw)
    return best


def summary(session: Session, skill: m.Skill) -> dict:
    """Combine le ressenti (auto évaluation) et les preuves (heures, exercices, projets)."""
    acts = skill.activities
    minutes = sum(a.duration_minutes or 0 for a in acts)
    progress = list(skill.progress)
    ratings = [p for p in progress if p.self_rating is not None]
    scores = [p for p in progress if p.objective_score is not None]
    evidence: dict[str, int] = {}
    for p in progress:
        if p.evidence_type:
            evidence[p.evidence_type] = evidence.get(p.evidence_type, 0) + 1
    by_month: dict[str, int] = {}
    for a in acts:
        key = a.day.date.strftime("%Y-%m")
        by_month[key] = by_month.get(key, 0) + (a.duration_minutes or 0)
    first, last = (ratings[0].self_rating, ratings[-1].self_rating) if ratings else (None, None)
    return {
        "id": skill.id,
        "name": skill.name,
        "category": skill.category,
        "dimension": skill.dimension,
        "target_level": skill.target_level,
        "hours": round(minutes / 60, 1),
        "n_activities": len(acts),
        "n_sessions_with_result": sum(1 for a in acts if a.result),
        "current_rating": last,
        "first_rating": first,
        "rating_change": (last - first) if ratings else None,
        "latest_objective_score": scores[-1].objective_score if scores else None,
        "evidence": evidence,
        "hours_by_month": [{"month": k, "hours": round(v / 60, 1)} for k, v in sorted(by_month.items())],
        "timeline": [
            {"date": str(p.date), "self_rating": p.self_rating, "objective_score": p.objective_score,
             "evidence_type": p.evidence_type, "evidence": p.evidence, "comment": p.comment}
            for p in progress
        ],
    }


def relink_all(session: Session) -> int:
    """Rattache aux compétences les activités qui ne le sont pas encore."""
    n = 0
    for act in session.query(m.Activity).filter(m.Activity.skill_id.is_(None)).all():
        sid = match_skill_id(session, act.category, act.description)
        if sid:
            act.skill_id = sid
            n += 1
    session.commit()
    return n
