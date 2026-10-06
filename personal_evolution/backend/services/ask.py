"""Questions en langage naturel sur la mémoire personnelle.

Le moteur reconnaît quelques familles de questions et répond à partir des
données, en citant toujours les éléments sources. À défaut, recherche plein texte.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ai.nlp.extract import fold

from .. import models as m
from ..domain import REFLECTION_KINDS, dimension_label
from . import analytics, memory

MONTHS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre",
          "novembre", "decembre"]


def parse_period(q: str, today: date | None = None) -> tuple[date | None, date | None, str]:
    today = today or date.today()
    f = fold(q)
    if "aujourd" in f:
        return today, today, "aujourd'hui"
    if re.search(r"\bhier\b", f):
        d = today - timedelta(days=1)
        return d, d, "hier"
    mt = re.search(r"(\d+)\s+derni(?:er|ere)s?\s+(jours|semaines|mois|ans|annees)", f)
    if mt:
        n, unit = int(mt.group(1)), mt.group(2)
        days = n * {"jours": 1, "semaines": 7, "mois": 30, "ans": 365, "annees": 365}[unit]
        return today - timedelta(days=days - 1), today, f"les {n} derniers {unit}"
    if "semaine derniere" in f:
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=6), "la semaine dernière"
    if "cette semaine" in f:
        return today - timedelta(days=today.weekday()), today, "cette semaine"
    if "mois dernier" in f:
        first = today.replace(day=1)
        prev_end = first - timedelta(days=1)
        return prev_end.replace(day=1), prev_end, "le mois dernier"
    if "ce mois" in f:
        return today.replace(day=1), today, "ce mois ci"
    if re.search(r"annee derniere|l.an dernier|l.an passe", f):
        y = today.year - 1
        return date(y, 1, 1), date(y, 12, 31), f"l'année {y}"
    if re.search(r"cette annee|cet an", f):
        return date(today.year, 1, 1), today, "cette année"
    for i, name in enumerate(MONTHS, start=1):
        if re.search(rf"\b(?:en |de |d.|au mois de )?{name}\b", f):
            year = today.year if i <= today.month else today.year - 1
            end = (date(year + (i == 12), (i % 12) + 1, 1) - timedelta(days=1))
            return date(year, i, 1), end, f"{name} {year}"
    mt = re.search(r"\b(20\d\d)\b", f)
    if mt:
        y = int(mt.group(1))
        return date(y, 1, 1), date(y, 12, 31), str(y)
    return None, None, "toute la période"


def ask(session: Session, question: str) -> dict:
    f = fold(question)
    start, end, period = parse_period(question)
    base = {"question": question, "period": period, "start": str(start) if start else None,
            "end": str(end) if end else None}

    if re.search(r"marque|retenir|memorable|important|souvenir", f):
        q = session.query(m.Reflection).join(m.Day)
        if start:
            q = q.filter(m.Day.date >= start, m.Day.date <= end)
        refs = q.filter(m.Reflection.kind.in_(["evenement", "reussite", "apprentissage", "passage", "gratitude"])) \
            .order_by(m.Day.date.desc()).limit(25).all()
        dq = session.query(m.Day).filter(m.Day.highlight.isnot(None), m.Day.highlight != "")
        if start:
            dq = dq.filter(m.Day.date >= start, m.Day.date <= end)
        days = dq.order_by(m.Day.date.desc()).limit(25).all()
        items = [{"date": str(d.date), "kind": "journee", "kind_label": "Moment marquant", "text": d.highlight, "ref_id": d.id}
                 for d in days]
        items += [{"date": str(r.day.date), "kind": "reflexion", "kind_label": REFLECTION_KINDS.get(r.kind, r.kind),
                   "text": r.content, "ref_id": r.id} for r in refs]
        items.sort(key=lambda x: x["date"], reverse=True)
        answer = (f"{len(items)} éléments marquants retrouvés pour {period}." if items
                  else f"Aucun élément marquant enregistré pour {period}.")
        return {**base, "intent": "marquant", "answer": answer, "items": items}

    if re.search(r"projets?.*(termine|fini|acheve|atteint|realise)|(termine|fini|atteint).*(projets?|objectifs?)", f):
        q = session.query(m.Goal).filter(m.Goal.status == "atteint")
        if start:
            q = q.filter(m.Goal.completed_at >= start, m.Goal.completed_at <= end)
        goals = q.order_by(m.Goal.completed_at.desc()).all()
        items = [{"date": str(g.completed_at) if g.completed_at else None, "kind": "objectif", "kind_label": "Objectif atteint",
                  "text": g.title, "ref_id": g.id} for g in goals]
        aq = session.query(m.Activity).join(m.Day).filter(m.Activity.result.isnot(None),
                                                          m.Activity.category.in_(["Projet", "Travail", "Portfolio"]))
        if start:
            aq = aq.filter(m.Day.date >= start, m.Day.date <= end)
        items += [{"date": str(a.day.date), "kind": "activite", "kind_label": "Résultat de projet",
                   "text": f"{a.description} : {a.result}", "ref_id": a.id} for a in aq.order_by(m.Day.date.desc()).limit(20)]
        answer = (f"{len(goals)} objectifs atteints pour {period}." if goals
                  else f"Aucun objectif marqué comme atteint pour {period}.")
        return {**base, "intent": "projets_termines", "answer": answer, "items": items}

    if re.search(r"(sujet|matiere|theme|domaine|competence|activite)s?.*(plus|le plus)|plus (etudie|travaille|pratique)|temps.*(occupe|consacre)", f):
        fr = analytics.load_frames(session, start, end)
        ac = fr.activities
        if re.search(r"etudi|sujet|apprend|matiere", f):
            ac = ac[ac["dimension"] == "etudes"]
        if ac.empty:
            return {**base, "intent": "temps", "answer": f"Aucune activité enregistrée pour {period}.", "items": []}
        g = ac.groupby(["category", "dimension"], dropna=False)["minutes"].agg(["sum", "count"]).reset_index()
        g = g.sort_values("sum", ascending=False).head(10)
        items = [{"kind": "statistique", "kind_label": dimension_label(r.dimension),
                  "text": f"{r.category} : {r['sum'] / 60:.1f} h en {int(r['count'])} séances", "date": None}
                 for _, r in g.iterrows()]
        top = g.iloc[0]
        return {**base, "intent": "temps", "items": items,
                "answer": f"Pour {period}, le sujet qui t'a le plus occupé est {top['category']} ({top['sum'] / 60:.1f} heures)."}

    if re.search(r"difficult|obstacle|bloqu|probleme|reviennent|raison", f):
        fr = analytics.load_frames(session, start, end)
        ab = analytics.abandons(fr)
        refs = fr.reflections[fr.reflections["kind"] == "difficulte"] if not fr.reflections.empty else fr.reflections
        items = [{"kind": "raison", "kind_label": "Raison citée", "text": f"{r['reason']} ({r['count']} fois)", "date": None}
                 for r in ab["reasons"]]
        items += [{"kind": "reflexion", "kind_label": "Difficulté", "text": r.content, "date": str(r.date.date()), "ref_id": r.id}
                  for r in refs.sort_values("date", ascending=False).head(15).itertuples()]
        top = ab["reasons"][0]["reason"] if ab["reasons"] else None
        answer = (f"La difficulté la plus fréquente pour {period} : « {top} »." if top
                  else f"{len(items)} difficultés notées pour {period}." if items
                  else f"Aucune difficulté enregistrée pour {period}.")
        return {**base, "intent": "difficultes", "answer": answer, "items": items}

    if re.search(r"abandon|pas realise|laisse tomber|echou", f):
        fr = analytics.load_frames(session, start, end)
        ab = analytics.abandons(fr)
        items = [{"kind": "statistique", "kind_label": c["dimension_label"],
                  "text": f"{c['category']} : {c['abandoned']} abandons sur {c['n']}", "date": None}
                 for c in ab["categories"][:10]]
        answer = (f"L'objectif le plus souvent abandonné pour {period} est {ab['categories'][0]['category']}."
                  if ab["categories"] else f"Pas assez de bilans pour {period}.")
        return {**base, "intent": "abandons", "answer": answer, "items": items}

    if re.search(r"evolu|progress|comment (ai.je|j.ai)|bilan", f):
        s = analytics.summary(session, start, end)
        if s.get("empty"):
            return {**base, "intent": "bilan", "answer": f"Aucune donnée pour {period}.", "items": []}
        rate = f"{round(s['completion_rate'] * 100)} %" if s["completion_rate"] is not None else "non calculé"
        items = [{"kind": "statistique", "kind_label": d["label"], "text": f"{d['hours']} h, {d['n_intentions']} intentions",
                  "date": None} for d in s["dimensions"] if d["minutes"] or d["n_intentions"]]
        return {**base, "intent": "bilan", "items": items,
                "answer": (f"Pour {period} : {s['n_logged_days']} jours renseignés sur {s['n_days']}, taux de réalisation {rate}, "
                           f"{s['total_hours']} heures d'activités suivies.")}

    results = memory.search(session, question, start=start, end=end, limit=30)
    items = [{"date": r["date"], "kind": r["kind"], "kind_label": r["kind_label"], "text": f"{r['title']} : {r['snippet']}",
              "ref_id": r["ref_id"]} for r in results]
    return {**base, "intent": "recherche", "items": items,
            "answer": f"{len(items)} éléments trouvés dans ta mémoire." if items else "Rien trouvé pour cette recherche."}
