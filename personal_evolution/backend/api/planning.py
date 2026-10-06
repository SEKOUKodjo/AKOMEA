"""Objectifs hiérarchiques, compétences, décisions, expériences et relations."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ai.ml import predict

from .. import models as m
from ..schemas import (
    DecisionIn,
    DecisionOut,
    ExperimentIn,
    ExperimentOut,
    GoalIn,
    GoalOut,
    GoalUpdate,
    InteractionIn,
    InteractionOut,
    PersonIn,
    PersonOut,
    SkillIn,
    SkillOut,
    SkillProgressIn,
    SkillProgressOut,
)
from ..services import analytics
from ..services import skills as skill_service
from .deps import get_session, not_found

router = APIRouter()


def _get(session: Session, model, obj_id: int, label: str):
    obj = session.get(model, obj_id)
    if obj is None:
        raise not_found(label)
    return obj


def _update(session: Session, obj, data: dict):
    for k, v in data.items():
        setattr(obj, k, v)
    session.commit()
    session.refresh(obj)
    return obj


def _delete(session: Session, obj):
    session.delete(obj)
    session.commit()
    return {"ok": True}


# Objectifs

@router.get("/goals", response_model=list[GoalOut], tags=["objectifs"])
def list_goals(status: str | None = None, horizon: str | None = None, session: Session = Depends(get_session)):
    q = session.query(m.Goal)
    if status:
        q = q.filter(m.Goal.status == status)
    if horizon:
        q = q.filter(m.Goal.horizon == horizon)
    return q.order_by(m.Goal.horizon, m.Goal.id).all()


@router.get("/goals/progress", tags=["objectifs"])
def goals_progress(session: Session = Depends(get_session)):
    return analytics.goals_progress(session)


@router.post("/goals", response_model=GoalOut, tags=["objectifs"])
def create_goal(body: GoalIn, session: Session = Depends(get_session)):
    goal = m.Goal(**body.model_dump())
    goal.start_date = goal.start_date or date.today()
    if goal.status == "atteint":
        goal.completed_at = date.today()
    session.add(goal)
    session.commit()
    return goal


@router.patch("/goals/{goal_id}", response_model=GoalOut, tags=["objectifs"])
def update_goal(goal_id: int, body: GoalUpdate, session: Session = Depends(get_session)):
    goal = _get(session, m.Goal, goal_id, "Objectif")
    data = body.model_dump(exclude_unset=True)
    if data.get("status") == "atteint" and goal.status != "atteint":
        goal.completed_at = date.today()
    return _update(session, goal, data)


@router.delete("/goals/{goal_id}", tags=["objectifs"])
def delete_goal(goal_id: int, session: Session = Depends(get_session)):
    return _delete(session, _get(session, m.Goal, goal_id, "Objectif"))


# Compétences

@router.get("/skills", tags=["competences"])
def list_skills(session: Session = Depends(get_session)):
    out = []
    for s in session.query(m.Skill).order_by(m.Skill.name).all():
        summ = skill_service.summary(session, s)
        summ["projection"] = predict.skill_projection(summ["timeline"])
        out.append(summ)
    return out


@router.post("/skills", response_model=SkillOut, tags=["competences"])
def create_skill(body: SkillIn, session: Session = Depends(get_session)):
    skill = m.Skill(**body.model_dump())
    session.add(skill)
    session.commit()
    skill_service.relink_all(session)
    return skill


@router.patch("/skills/{skill_id}", response_model=SkillOut, tags=["competences"])
def update_skill(skill_id: int, body: SkillIn, session: Session = Depends(get_session)):
    skill = _update(session, _get(session, m.Skill, skill_id, "Compétence"), body.model_dump(exclude_unset=True))
    skill_service.relink_all(session)
    return skill


@router.delete("/skills/{skill_id}", tags=["competences"])
def delete_skill(skill_id: int, session: Session = Depends(get_session)):
    return _delete(session, _get(session, m.Skill, skill_id, "Compétence"))


@router.post("/skills/{skill_id}/progress", response_model=SkillProgressOut, tags=["competences"])
def add_progress(skill_id: int, body: SkillProgressIn, session: Session = Depends(get_session)):
    _get(session, m.Skill, skill_id, "Compétence")
    data = body.model_dump()
    data["date"] = data["date"] or date.today()
    prog = m.SkillProgress(skill_id=skill_id, **data)
    session.add(prog)
    session.commit()
    return prog


# Décisions

@router.get("/decisions", response_model=list[DecisionOut], tags=["decisions"])
def list_decisions(session: Session = Depends(get_session)):
    return session.query(m.Decision).order_by(m.Decision.date.desc()).all()


@router.get("/decisions/to-review", response_model=list[DecisionOut], tags=["decisions"])
def decisions_to_review(session: Session = Depends(get_session)):
    """Décisions dont la date de revue est passée et dont le résultat n'est pas encore noté."""
    return (session.query(m.Decision).filter(m.Decision.review_date <= date.today(), m.Decision.outcome.is_(None))
            .order_by(m.Decision.review_date).all())


@router.post("/decisions", response_model=DecisionOut, tags=["decisions"])
def create_decision(body: DecisionIn, session: Session = Depends(get_session)):
    data = body.model_dump()
    data["date"] = data["date"] or date.today()
    dec = m.Decision(**data)
    session.add(dec)
    session.commit()
    return dec


@router.patch("/decisions/{decision_id}", response_model=DecisionOut, tags=["decisions"])
def update_decision(decision_id: int, body: DecisionIn, session: Session = Depends(get_session)):
    return _update(session, _get(session, m.Decision, decision_id, "Décision"), body.model_dump(exclude_unset=True))


@router.delete("/decisions/{decision_id}", tags=["decisions"])
def delete_decision(decision_id: int, session: Session = Depends(get_session)):
    return _delete(session, _get(session, m.Decision, decision_id, "Décision"))


# Expériences personnelles

@router.get("/experiments", tags=["experiences"])
def list_experiments(session: Session = Depends(get_session)):
    out = []
    for e in session.query(m.Experiment).order_by(m.Experiment.start_date.desc()).all():
        data = ExperimentOut.model_validate(e).model_dump(mode="json")
        data["analysis"] = analytics.experiment_analysis(session, e)
        out.append(data)
    return out


@router.get("/experiments/metrics", tags=["experiences"])
def experiment_metrics():
    return [{"key": k, "label": v} for k, v in analytics.METRIC_LABELS.items()]


@router.post("/experiments", response_model=ExperimentOut, tags=["experiences"])
def create_experiment(body: ExperimentIn, session: Session = Depends(get_session)):
    data = body.model_dump()
    data["start_date"] = data["start_date"] or date.today()
    exp = m.Experiment(**data)
    session.add(exp)
    session.commit()
    return exp


@router.patch("/experiments/{exp_id}", response_model=ExperimentOut, tags=["experiences"])
def update_experiment(exp_id: int, body: ExperimentIn, session: Session = Depends(get_session)):
    return _update(session, _get(session, m.Experiment, exp_id, "Expérience"), body.model_dump(exclude_unset=True))


@router.delete("/experiments/{exp_id}", tags=["experiences"])
def delete_experiment(exp_id: int, session: Session = Depends(get_session)):
    return _delete(session, _get(session, m.Experiment, exp_id, "Expérience"))


# Relations

@router.get("/people", tags=["relations"])
def list_people(session: Session = Depends(get_session)):
    out = []
    for p in session.query(m.Person).order_by(m.Person.name).all():
        last = max((i.date for i in p.interactions), default=None)
        out.append({**PersonOut.model_validate(p).model_dump(mode="json"),
                    "n_interactions": len(p.interactions), "last_interaction": str(last) if last else None,
                    "days_since": (date.today() - last).days if last else None})
    return out


@router.post("/people", response_model=PersonOut, tags=["relations"])
def create_person(body: PersonIn, session: Session = Depends(get_session)):
    p = m.Person(**body.model_dump())
    session.add(p)
    session.commit()
    return p


@router.delete("/people/{person_id}", tags=["relations"])
def delete_person(person_id: int, session: Session = Depends(get_session)):
    return _delete(session, _get(session, m.Person, person_id, "Personne"))


@router.post("/interactions", response_model=InteractionOut, tags=["relations"])
def create_interaction(body: InteractionIn, session: Session = Depends(get_session)):
    _get(session, m.Person, body.person_id, "Personne")
    data = body.model_dump()
    data["date"] = data["date"] or date.today()
    it = m.Interaction(**data)
    session.add(it)
    session.commit()
    return it


@router.get("/people/{person_id}/interactions", response_model=list[InteractionOut], tags=["relations"])
def person_interactions(person_id: int, session: Session = Depends(get_session)):
    return _get(session, m.Person, person_id, "Personne").interactions
