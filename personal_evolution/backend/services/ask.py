"""Questions en langage naturel sur la mémoire personnelle, en français ou en anglais.

Le moteur reconnaît quelques familles de questions et répond à partir des
données, en citant toujours les éléments sources. À défaut, recherche plein texte.
La réponse est rédigée dans la langue de l'interface, quelle que soit la langue
de la question.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ai.nlp.extract import fold

from .. import models as m
from ..domain import REFLECTION_KINDS, dimension_label, label
from ..i18n import get_lang, num, tr
from . import analytics, memory

MONTHS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre",
             "novembre", "decembre"]
MONTHS_EN = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
             "november", "december"]
MONTH_LABELS = {"fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
                       "novembre", "décembre"],
                "en": [m_.capitalize() for m_ in MONTHS_EN]}
PROJECT_CATEGORIES = ["Projet", "Travail", "Portfolio", "Project", "Work"]


def parse_period(q: str, today: date | None = None) -> tuple[date | None, date | None, str]:
    """Reconnaît la période d'une question, en français ou en anglais."""
    today = today or date.today()
    f = fold(q)
    if "aujourd" in f or re.search(r"\btoday\b", f):
        return today, today, tr("aujourd'hui")
    if re.search(r"\bhier\b|\byesterday\b", f):
        d = today - timedelta(days=1)
        return d, d, tr("hier")
    mt = (re.search(r"(\d+)\s+derni(?:er|ere)s?\s+(jours|semaines|mois|ans|annees)", f)
          or re.search(r"(?:last|past)\s+(\d+)\s+(days?|weeks?|months?|years?)", f))
    if mt:
        n, unit = int(mt.group(1)), mt.group(2)
        unit = {"day": "jours", "days": "jours", "week": "semaines", "weeks": "semaines", "month": "mois",
                "months": "mois", "year": "ans", "years": "ans", "annees": "ans"}.get(unit, unit)
        days = n * {"jours": 1, "semaines": 7, "mois": 30, "ans": 365}[unit]
        text = {"jours": "les {n} derniers jours", "semaines": "les {n} dernières semaines",
                "mois": "les {n} derniers mois", "ans": "les {n} dernières années"}[unit]
        return today - timedelta(days=days - 1), today, tr(text, n=n)
    if "semaine derniere" in f or "last week" in f:
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=6), tr("la semaine dernière")
    if "cette semaine" in f or "this week" in f:
        return today - timedelta(days=today.weekday()), today, tr("cette semaine")
    if "mois dernier" in f or "last month" in f:
        first = today.replace(day=1)
        prev_end = first - timedelta(days=1)
        return prev_end.replace(day=1), prev_end, tr("le mois dernier")
    if "ce mois" in f or "this month" in f:
        return today.replace(day=1), today, tr("ce mois ci")
    if re.search(r"annee derniere|l.an dernier|l.an passe|last year", f):
        y = today.year - 1
        return date(y, 1, 1), date(y, 12, 31), tr("l'année {y}", y=y)
    if re.search(r"cette annee|cet an|this year", f):
        return date(today.year, 1, 1), today, tr("cette année")
    for months in (MONTHS_FR, MONTHS_EN):
        for i, name in enumerate(months, start=1):
            if name == "may" and not re.search(r"\b(?:in|of|during) may\b", f):
                continue  # « may » est aussi un verbe anglais
            if re.search(rf"\b{name}\b", f):
                year = today.year if i <= today.month else today.year - 1
                end = date(year + (i == 12), (i % 12) + 1, 1) - timedelta(days=1)
                return date(year, i, 1), end, f"{MONTH_LABELS[get_lang()][i - 1]} {year}"
    mt = re.search(r"\b(20\d\d)\b", f)
    if mt:
        y = int(mt.group(1))
        return date(y, 1, 1), date(y, 12, 31), str(y)
    return None, None, tr("toute la période")


INTENTS = [
    ("marquant", r"marque|retenir|memorable|important|souvenir|stood out|stand out|remember|highlight|struck"),
    ("projets_termines", r"projets?.*(termine|fini|acheve|atteint|realise)|(termine|fini|atteint).*(projets?|objectifs?)"
                         r"|(projects?|goals?).*(finish|complet|achiev|done|reach)|(finish|complet|achiev).*(projects?|goals?)"),
    ("temps", r"(sujet|matiere|theme|domaine|competence|activite)s?.*(plus|le plus)|plus (etudie|travaille|pratique)"
              r"|temps.*(occupe|consacre)|(topic|subject|skill|activit)\w*.*most|most (studied|worked|practi)"
              r"|stud(y|ied) (the )?most|time.*spen[dt]|spen[dt].*time"),
    ("difficultes", r"difficult|obstacle|bloqu|probleme|reviennent|raison|struggl|stuck|problem|keep coming|recurr|reason"),
    ("abandons", r"abandon|pas realise|laisse tomber|echou|gave up|give up|didn.?t do|did not do|fail"),
    ("bilan", r"evolu|progress|comment (ai.je|j.ai)|bilan|how (did|have) i|review|summary|overview"),
]


def detect_intent(question: str) -> str:
    f = fold(question)
    for name, pattern in INTENTS:
        if re.search(pattern, f):
            return name
    return "recherche"


def ask(session: Session, question: str) -> dict:
    f = fold(question)
    start, end, period = parse_period(question)
    base = {"question": question, "period": period, "start": str(start) if start else None,
            "end": str(end) if end else None}
    intent = detect_intent(question)

    if intent == "marquant":
        q = session.query(m.Reflection).join(m.Day)
        if start:
            q = q.filter(m.Day.date >= start, m.Day.date <= end)
        refs = q.filter(m.Reflection.kind.in_(["evenement", "reussite", "apprentissage", "passage", "gratitude"])) \
            .order_by(m.Day.date.desc()).limit(25).all()
        dq = session.query(m.Day).filter(m.Day.highlight.isnot(None), m.Day.highlight != "")
        if start:
            dq = dq.filter(m.Day.date >= start, m.Day.date <= end)
        days = dq.order_by(m.Day.date.desc()).limit(25).all()
        items = [{"date": str(d.date), "kind": "journee", "kind_label": tr("Moment marquant"), "text": d.highlight,
                  "ref_id": d.id} for d in days]
        items += [{"date": str(r.day.date), "kind": "reflexion", "kind_label": label(REFLECTION_KINDS, r.kind),
                   "text": r.content, "ref_id": r.id} for r in refs]
        items.sort(key=lambda x: x["date"], reverse=True)
        answer = (tr("{n} éléments marquants retrouvés pour {period}.", n=len(items), period=period) if items
                  else tr("Aucun élément marquant enregistré pour {period}.", period=period))
        return {**base, "intent": intent, "answer": answer, "items": items}

    if intent == "projets_termines":
        q = session.query(m.Goal).filter(m.Goal.status == "atteint")
        if start:
            q = q.filter(m.Goal.completed_at >= start, m.Goal.completed_at <= end)
        goals = q.order_by(m.Goal.completed_at.desc()).all()
        items = [{"date": str(g.completed_at) if g.completed_at else None, "kind": "objectif",
                  "kind_label": tr("Objectif atteint"), "text": g.title, "ref_id": g.id} for g in goals]
        aq = session.query(m.Activity).join(m.Day).filter(m.Activity.result.isnot(None),
                                                          m.Activity.category.in_(PROJECT_CATEGORIES))
        if start:
            aq = aq.filter(m.Day.date >= start, m.Day.date <= end)
        items += [{"date": str(a.day.date), "kind": "activite", "kind_label": tr("Résultat de projet"),
                   "text": f"{a.description} : {a.result}", "ref_id": a.id} for a in aq.order_by(m.Day.date.desc()).limit(20)]
        answer = (tr("{n} objectifs atteints pour {period}.", n=len(goals), period=period) if goals
                  else tr("Aucun objectif marqué comme atteint pour {period}.", period=period))
        return {**base, "intent": intent, "answer": answer, "items": items}

    if intent == "temps":
        fr = analytics.load_frames(session, start, end)
        ac = fr.activities
        if re.search(r"etudi|sujet|apprend|matiere|stud|topic|subject|learn", f):
            ac = ac[ac["dimension"] == "etudes"]
        if ac.empty:
            return {**base, "intent": intent, "answer": tr("Aucune activité enregistrée pour {period}.", period=period),
                    "items": []}
        g = ac.groupby(["category", "dimension"], dropna=False)["minutes"].agg(["sum", "count"]).reset_index()
        g = g.sort_values("sum", ascending=False).head(10)
        items = [{"kind": "statistique", "kind_label": dimension_label(r.dimension),
                  "text": tr("{cat} : {h} h en {n} séances", cat=r.category, h=num(r["sum"] / 60), n=int(r["count"])),
                  "date": None} for _, r in g.iterrows()]
        top = g.iloc[0]
        return {**base, "intent": intent, "items": items,
                "answer": tr("Pour {period}, le sujet qui t'a le plus occupé est {cat} ({h} heures).", period=period,
                             cat=top["category"], h=num(top["sum"] / 60))}

    if intent == "difficultes":
        fr = analytics.load_frames(session, start, end)
        ab = analytics.abandons(fr)
        refs = fr.reflections[fr.reflections["kind"] == "difficulte"] if not fr.reflections.empty else fr.reflections
        items = [{"kind": "raison", "kind_label": tr("Raison citée"),
                  "text": tr("{reason} ({n} fois)", reason=r["reason"], n=r["count"]), "date": None} for r in ab["reasons"]]
        items += [{"kind": "reflexion", "kind_label": tr("Difficulté"), "text": r.content, "date": str(r.date.date()),
                   "ref_id": r.id} for r in refs.sort_values("date", ascending=False).head(15).itertuples()]
        top = ab["reasons"][0]["reason"] if ab["reasons"] else None
        answer = (tr("La difficulté la plus fréquente pour {period} : « {top} ».", period=period, top=top) if top
                  else tr("{n} difficultés notées pour {period}.", n=len(items), period=period) if items
                  else tr("Aucune difficulté enregistrée pour {period}.", period=period))
        return {**base, "intent": intent, "answer": answer, "items": items}

    if intent == "abandons":
        fr = analytics.load_frames(session, start, end)
        ab = analytics.abandons(fr)
        items = [{"kind": "statistique", "kind_label": c["dimension_label"],
                  "text": tr("{cat} : {k} abandons sur {n}", cat=c["category"], k=c["abandoned"], n=c["n"]), "date": None}
                 for c in ab["categories"][:10]]
        answer = (tr("L'objectif le plus souvent abandonné pour {period} est {cat}.", period=period,
                     cat=ab["categories"][0]["category"])
                  if ab["categories"] else tr("Pas assez de bilans pour {period}.", period=period))
        return {**base, "intent": intent, "answer": answer, "items": items}

    if intent == "bilan":
        s = analytics.summary(session, start, end)
        if s.get("empty"):
            return {**base, "intent": intent, "answer": tr("Aucune donnée pour {period}.", period=period), "items": []}
        rate = f"{round(s['completion_rate'] * 100)} %" if s["completion_rate"] is not None else tr("non calculé")
        items = [{"kind": "statistique", "kind_label": d["label"],
                  "text": tr("{h} h, {n} intentions", h=num(d["hours"]), n=d["n_intentions"]), "date": None}
                 for d in s["dimensions"] if d["minutes"] or d["n_intentions"]]
        return {**base, "intent": intent, "items": items,
                "answer": tr("Pour {period} : {logged} jours renseignés sur {days}, taux de réalisation {rate}, "
                             "{hours} heures d'activités suivies.", period=period, logged=s["n_logged_days"],
                             days=s["n_days"], rate=rate, hours=num(s["total_hours"]))}

    results = memory.search(session, question, start=start, end=end, limit=30)
    items = [{"date": r["date"], "kind": r["kind"], "kind_label": r["kind_label"], "text": f"{r['title']} : {r['snippet']}",
              "ref_id": r["ref_id"]} for r in results]
    return {**base, "intent": "recherche", "items": items,
            "answer": (tr("{n} éléments trouvés dans ta mémoire.", n=len(items)) if items
                       else tr("Rien trouvé pour cette recherche."))}
