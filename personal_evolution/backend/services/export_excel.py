"""Export Excel des données et des indicateurs de PEI.

Le classeur contient les données brutes (une feuille par type de donnée) et des
indicateurs calculés par des FORMULES Excel qui pointent vers ces données : si
l'utilisateur corrige une valeur dans Excel, les indicateurs se mettent à jour.
Seules les analyses statistiques (tests, corrélations, recommandations) sont des
valeurs calculées par PEI au moment de l'export ; elles sont signalées comme telles.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

from .. import models as m
from ..domain import (DIMENSIONS, GOAL_STATUSES, HORIZONS, INTENTION_STATUSES, REFLECTION_KINDS,
                      dimension_label)
from . import analytics
from . import skills as skill_service

GREEN, YELLOW, RED = "006A4E", "FFCE00", "D21034"
FONT = "Arial"
F_BODY = Font(name=FONT, size=10)
F_HEAD = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_TITLE = Font(name=FONT, size=16, bold=True, color=GREEN)
F_SUB = Font(name=FONT, size=10, italic=True, color="5B6A63")
F_SECTION = Font(name=FONT, size=12, bold=True, color=GREEN)
F_BOLD = Font(name=FONT, size=10, bold=True)
FILL_HEAD = PatternFill("solid", fgColor=GREEN)
FILL_KPI = PatternFill("solid", fgColor="F4F6F2")
BORDER_HEAD = Border(bottom=Side(style="medium", color=YELLOW))
BORDER_ROW = Border(bottom=Side(style="thin", color="DFE6E0"))

FMT_DATE = "dd/mm/yyyy"
FMT_PCT = "0.0%"
FMT_DEC = "0.0"
FMT_INT = "0"

STATUS_LABEL = INTENTION_STATUSES  # prevu -> Prévu ...
DIM_LABELS = [v["label"] for v in DIMENSIONS.values()]
WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


@dataclass
class Col:
    key: str
    header: str
    width: int = 14
    fmt: str | None = None
    wrap: bool = False


class Table:
    """Feuille de données : en-têtes stylés, repérage des colonnes par clé pour écrire des formules."""

    def __init__(self, ws: Worksheet, cols: list[Col], header_row: int = 1):
        self.ws, self.cols, self.header_row = ws, cols, header_row
        self.letter = {c.key: get_column_letter(i + 1) for i, c in enumerate(cols)}
        self.n = 0
        for i, c in enumerate(cols, start=1):
            cell = ws.cell(row=header_row, column=i, value=c.header)
            cell.font, cell.fill, cell.border = F_HEAD, FILL_HEAD, BORDER_HEAD
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            ws.column_dimensions[get_column_letter(i)].width = c.width
        ws.row_dimensions[header_row].height = 30
        ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

    @property
    def first(self) -> int:
        return self.header_row + 1

    @property
    def last(self) -> int:
        return self.header_row + max(self.n, 1)

    def add(self, values: dict) -> int:
        r = self.first + self.n
        for i, c in enumerate(self.cols, start=1):
            v = values.get(c.key)
            if callable(v):
                v = v(r)
            cell = self.ws.cell(row=r, column=i, value=v)
            cell.font = F_BODY
            cell.border = BORDER_ROW
            if c.fmt:
                cell.number_format = c.fmt
            if c.wrap:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        self.n += 1
        return r

    def rng(self, key: str, absolute: bool = True) -> str:
        """Plage d'une colonne, qualifiée par le nom de la feuille."""
        col = self.letter[key]
        d = "$" if absolute else ""
        return f"'{self.ws.title}'!{d}{col}{d}{self.first}:{d}{col}{d}{self.last}"

    def finish(self) -> None:
        last_col = get_column_letter(len(self.cols))
        self.ws.auto_filter.ref = f"A{self.header_row}:{last_col}{self.header_row + max(self.n, 1)}"


def _title(ws: Worksheet, title: str, subtitle: str) -> None:
    ws["A1"] = title
    ws["A1"].font = F_TITLE
    ws["A2"] = subtitle
    ws["A2"].font = F_SUB


def _note(ws: Worksheet, row: int, text: str, col: int = 1) -> None:
    c = ws.cell(row=row, column=col, value=text)
    c.font = F_SUB


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def build_workbook(session: Session, start: date | None = None, end: date | None = None) -> Workbook:
    fr = analytics.load_frames(session, start, end)
    daily = analytics.daily_series(fr, start, end) if (start and end) else analytics.daily_series(fr)
    if daily.empty:
        today = pd.Timestamp(date.today())
        daily = analytics.daily_series(fr, today.date(), today.date())
    p_start, p_end = daily.index.min().date(), daily.index.max().date()

    wb = Workbook()
    ws_syn = wb.active
    ws_syn.title = "Synthese"
    ws_q = wb.create_sheet("Quotidien")
    ws_w = wb.create_sheet("Hebdomadaire")
    ws_mo = wb.create_sheet("Mensuel")
    ws_i = wb.create_sheet("Intentions")
    ws_a = wb.create_sheet("Activites")
    ws_r = wb.create_sheet("Reflexions")
    ws_cal = wb.create_sheet("Calibration")
    ws_ab = wb.create_sheet("Abandons")
    ws_g = wb.create_sheet("Objectifs")
    ws_s = wb.create_sheet("Competences")
    ws_e = wb.create_sheet("Evaluations")
    ws_an = wb.create_sheet("Analyses")
    ws_d = wb.create_sheet("Decisions")
    ws_x = wb.create_sheet("Experiences")
    ws_p = wb.create_sheet("Relations")
    ws_m = wb.create_sheet("Medias")

    # Intentions (données brutes)
    goals = {g.id: g.title for g in session.query(m.Goal).all()}
    ti = Table(ws_i, [
        Col("id", "N°", 7), Col("date", "Date", 12, FMT_DATE), Col("dim", "Dimension", 18), Col("cat", "Type d'activité", 20),
        Col("desc", "Intention", 42, wrap=True), Col("prio", "Priorité", 10), Col("est", "Durée prévue (min)", 12, FMT_INT),
        Col("status", "Statut", 13), Col("act", "Durée réelle (min)", 12, FMT_INT), Col("gap", "Écart (min)", 11, FMT_INT),
        Col("score", "Score de réalisation", 12, "0.0"), Col("result", "Résultat", 34, wrap=True),
        Col("reason", "Raison d'un écart", 26, wrap=True), Col("goal", "Objectif relié", 30, wrap=True),
    ])
    prio = {1: "Haute", 2: "Normale", 3: "Basse"}
    it = fr.intentions.sort_values(["date", "id"]) if not fr.intentions.empty else fr.intentions
    for row in it.itertuples():
        ti.add({
            "id": int(row.id), "date": row.date.date(), "dim": dimension_label(row.dimension), "cat": row.category,
            "desc": row.description, "prio": prio.get(int(row.priority), ""), "est": _clean(row.estimated_minutes),
            "status": STATUS_LABEL.get(row.status, row.status), "act": _clean(row.actual_minutes),
            "gap": lambda r: f'=IF(AND(ISNUMBER({ti.letter["est"]}{r}),ISNUMBER({ti.letter["act"]}{r})),'
                             f'{ti.letter["act"]}{r}-{ti.letter["est"]}{r},"")',
            "score": lambda r: (f'=IF({ti.letter["status"]}{r}="Réalisé",1,IF({ti.letter["status"]}{r}="Partiel",0.5,'
                                f'IF({ti.letter["status"]}{r}="Prévu","",0)))'),
            "result": _clean(row.result), "reason": _clean(row.reason),
            "goal": goals.get(int(row.goal_id)) if _clean(row.goal_id) else None,
        })
    ti.finish()
    ws_i.cell(row=1, column=ti.cols.index(next(c for c in ti.cols if c.key == "score")) + 1).comment = Comment(
        "Réalisé = 1, Partiel = 0,5, Non réalisé, Abandonné ou Reporté = 0, Prévu = non évalué (vide).", "PEI")

    # Activités (données brutes)
    skills = {s.id: s.name for s in session.query(m.Skill).all()}
    ta = Table(ws_a, [
        Col("id", "N°", 7), Col("date", "Date", 12, FMT_DATE), Col("dim", "Dimension", 18), Col("cat", "Type d'activité", 20),
        Col("desc", "Activité", 42, wrap=True), Col("min", "Durée (min)", 11, FMT_INT), Col("start", "Début", 8),
        Col("end", "Fin", 8), Col("result", "Résultat", 36, wrap=True), Col("planned", "Prévue", 9),
        Col("skill", "Compétence", 18),
    ])
    acts = {a.id: a for a in session.query(m.Activity).filter(m.Activity.id.in_(list(fr.activities["id"]))).all()} \
        if not fr.activities.empty else {}
    ac = fr.activities.sort_values(["date", "id"]) if not fr.activities.empty else fr.activities
    for row in ac.itertuples():
        a = acts.get(int(row.id))
        ta.add({
            "id": int(row.id), "date": row.date.date(), "dim": dimension_label(row.dimension), "cat": row.category,
            "desc": row.description, "min": int(row.minutes), "start": a.start_time if a else None,
            "end": a.end_time if a else None, "result": _clean(row.result),
            "planned": "Oui" if _clean(row.intention_id) else "Non",
            "skill": skills.get(int(row.skill_id)) if _clean(row.skill_id) else None,
        })
    ta.finish()

    # Réflexions
    tr = Table(ws_r, [Col("date", "Date", 12, FMT_DATE), Col("kind", "Type", 18), Col("dim", "Dimension", 18),
                      Col("content", "Contenu", 80, wrap=True)])
    rf = fr.reflections.sort_values("date") if not fr.reflections.empty else fr.reflections
    for row in rf.itertuples():
        tr.add({"date": row.date.date(), "kind": REFLECTION_KINDS.get(row.kind, row.kind),
                "dim": dimension_label(row.dimension) if _clean(row.dimension) else None, "content": row.content})
    tr.finish()

    # Quotidien : une ligne par jour, indicateurs par formules
    highlights = {}
    if not fr.days.empty:
        highlights = dict(zip(fr.days["date"], fr.days["highlight"]))
    qcols = [
        Col("date", "Date", 12, FMT_DATE), Col("wd", "Jour", 11), Col("logged", "Renseigné", 10),
        Col("n", "Intentions", 10, FMT_INT), Col("eval", "Évaluées", 10, FMT_INT), Col("done", "Réalisées", 10, FMT_INT),
        Col("rate", "Taux de réalisation", 12, FMT_PCT), Col("planned", "Temps prévu (min)", 12, FMT_INT),
        Col("actual", "Temps réalisé (min)", 12, FMT_INT),
    ] + [Col(f"d_{k}", f"{v['label']} (min)", 12, FMT_INT) for k, v in DIMENSIONS.items()] + [
        Col("sleep_hours", "Sommeil (h)", 10, FMT_DEC), Col("sleep_quality", "Qualité sommeil", 10, FMT_INT),
        Col("energy", "Énergie", 9, FMT_INT), Col("motivation", "Motivation", 10, FMT_INT), Col("mood", "Humeur", 9, FMT_INT),
        Col("stress", "Stress", 9, FMT_INT), Col("screen_minutes", "Écran (min)", 10, FMT_INT),
        Col("steps", "Pas", 10, "#,##0"), Col("water_liters", "Eau (l)", 9, FMT_DEC),
        Col("n_ref", "Réflexions", 10, FMT_INT), Col("highlight", "Moment marquant", 40, wrap=True),
    ]
    tq = Table(ws_q, qcols)
    I, A, R = ti, ta, tr

    def q_formulas(r: int) -> dict:
        d = f"$A{r}"
        out = {
            "wd": f'=INDEX({{"Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"}},WEEKDAY({d},2))',
            "n": f"=COUNTIFS({I.rng('date')},{d})",
            "eval": f'=COUNTIFS({I.rng("date")},{d},{I.rng("status")},"<>Prévu")',
            "done": f'=COUNTIFS({I.rng("date")},{d},{I.rng("status")},"Réalisé")+COUNTIFS({I.rng("date")},{d},{I.rng("status")},"Partiel")',
            "rate": f'=IF({tq.letter["eval"]}{r}=0,"",SUMIFS({I.rng("score")},{I.rng("date")},{d})/{tq.letter["eval"]}{r})',
            "planned": f"=SUMIFS({I.rng('est')},{I.rng('date')},{d})",
            "actual": f"=SUMIFS({A.rng('min')},{A.rng('date')},{d})",
            "n_ref": f"=COUNTIFS({R.rng('date')},{d})",
        }
        for k, v in DIMENSIONS.items():
            out[f"d_{k}"] = f'=SUMIFS({A.rng("min")},{A.rng("date")},{d},{A.rng("dim")},"{v["label"]}")'
        return out

    for ts, row in daily.iterrows():
        r = tq.first + tq.n
        vals = {"date": ts.date(), "logged": "Oui" if row["logged"] else "Non", **q_formulas(r)}
        for k in ["sleep_hours", "sleep_quality", "energy", "motivation", "mood", "stress", "screen_minutes", "steps",
                  "water_liters"]:
            vals[k] = _clean(row.get(k))
        vals["highlight"] = _clean(highlights.get(ts))
        tq.add(vals)
    tq.finish()
    Q = tq

    # Hebdomadaire et mensuel : agrégats par formules
    def period_table(ws: Worksheet, label_end: str, starts: list[date], end_formula) -> Table:
        t = Table(ws, [
            Col("start", "Début", 12, FMT_DATE), Col("end", label_end, 12, FMT_DATE),
            Col("logged", "Jours renseignés", 11, FMT_INT), Col("reg", "Régularité", 11, FMT_PCT),
            Col("n", "Intentions", 10, FMT_INT), Col("eval", "Évaluées", 10, FMT_INT), Col("done", "Réalisées", 10, FMT_INT),
            Col("rate", "Taux de réalisation", 12, FMT_PCT), Col("hours", "Heures suivies", 11, FMT_DEC),
        ] + [Col(f"h_{k}", f"{v['label']} (h)", 11, FMT_DEC) for k, v in DIMENSIONS.items()] + [
            Col("sleep", "Sommeil moyen (h)", 11, FMT_DEC), Col("energy", "Énergie moyenne", 11, "0.00"),
            Col("mood", "Humeur moyenne", 11, "0.00"), Col("gap", "Écart moyen d'estimation (min)", 14, FMT_DEC),
        ])
        for s in starts:
            r = t.first + t.n
            a, b = f"$A{r}", f"$B{r}"
            inq = f'{Q.rng("date")},">="&{a},{Q.rng("date")},"<="&{b}'
            ini = f'{I.rng("date")},">="&{a},{I.rng("date")},"<="&{b}'
            vals = {
                "start": s, "end": end_formula(r),
                "logged": f'=COUNTIFS({inq},{Q.rng("logged")},"Oui")',
                "reg": f'=IFERROR(C{r}/COUNTIFS({inq}),"")',
                "n": f"=SUMIFS({Q.rng('n')},{inq})", "eval": f"=SUMIFS({Q.rng('eval')},{inq})",
                "done": f"=SUMIFS({Q.rng('done')},{inq})",
                "rate": f'=IF({t.letter["eval"]}{r}=0,"",SUMIFS({I.rng("score")},{ini})/{t.letter["eval"]}{r})',
                "hours": f"=SUMIFS({Q.rng('actual')},{inq})/60",
                "sleep": f'=IFERROR(AVERAGEIFS({Q.rng("sleep_hours")},{inq}),"")',
                "energy": f'=IFERROR(AVERAGEIFS({Q.rng("energy")},{inq}),"")',
                "mood": f'=IFERROR(AVERAGEIFS({Q.rng("mood")},{inq}),"")',
                "gap": f'=IFERROR(AVERAGEIFS({I.rng("gap")},{ini}),"")',
            }
            for k in DIMENSIONS:
                vals[f"h_{k}"] = f"=SUMIFS({Q.rng('d_' + k)},{inq})/60"
            t.add(vals)
        t.finish()
        return t

    w0 = p_start - timedelta(days=p_start.weekday())
    weeks = [w0 + timedelta(days=7 * k) for k in range((p_end - w0).days // 7 + 1)]
    tw = period_table(ws_w, "Fin", weeks, lambda r: f"=A{r}+6")
    months, mcur = [], p_start.replace(day=1)
    while mcur <= p_end:
        months.append(mcur)
        mcur = (mcur.replace(day=28) + timedelta(days=4)).replace(day=1)
    period_table(ws_mo, "Fin", months, lambda r: f"=EOMONTH(A{r},0)")

    # Calibration du temps : formules par type d'activité
    tc = Table(ws_cal, [
        Col("cat", "Type d'activité", 24), Col("n", "Observations", 12, FMT_INT), Col("est", "Prévu moyen (min)", 13, FMT_DEC),
        Col("act", "Réel moyen (min)", 13, FMT_DEC), Col("gap", "Écart moyen (min)", 13, FMT_DEC),
        Col("ratio", "Réel / prévu", 11, "0.00"), Col("read", "Lecture", 26),
    ], header_row=4)
    _title(ws_cal, "Calibration du temps", "Temps prévu contre temps réellement utilisé, par type d'activité "
                                           "(intentions avec durée prévue et réelle).")
    cats = sorted(set(it["category"].dropna())) if not it.empty else []
    for cat in cats:
        tc.add({
            "cat": cat,
            "n": lambda r: f'=COUNTIFS({I.rng("cat")},$A{r},{I.rng("est")},">0",{I.rng("act")},">0")',
            "est": lambda r: f'=IFERROR(AVERAGEIFS({I.rng("est")},{I.rng("cat")},$A{r},{I.rng("est")},">0",{I.rng("act")},">0"),"")',
            "act": lambda r: f'=IFERROR(AVERAGEIFS({I.rng("act")},{I.rng("cat")},$A{r},{I.rng("est")},">0",{I.rng("act")},">0"),"")',
            "gap": lambda r: f'=IFERROR(D{r}-C{r},"")',
            "ratio": lambda r: f'=IFERROR(D{r}/C{r},"")',
            "read": lambda r: (f'=IF(B{r}<3,"Pas assez de données",IF(F{r}>1.1,"Sous estimation",'
                               f'IF(F{r}<0.9,"Surestimation","Estimation juste")))'),
        })
    tc.finish()
    _note(ws_cal, tc.last + 2, "Seuils : rapport réel / prévu supérieur à 1,1 = sous estimation, inférieur à 0,9 = "
                               "surestimation. Au moins 3 observations sont nécessaires.")

    # Abandons : formules par type d'activité, puis raisons citées
    _title(ws_ab, "Objectifs non réalisés", "Part des intentions évaluées qui n'ont pas été réalisées, par type d'activité.")
    tb = Table(ws_ab, [
        Col("cat", "Type d'activité", 24), Col("eval", "Évaluées", 10, FMT_INT), Col("nr", "Non réalisées", 12, FMT_INT),
        Col("ab", "Abandonnées", 12, FMT_INT), Col("rep", "Reportées", 10, FMT_INT), Col("rate", "Taux de non réalisation", 14, FMT_PCT),
    ], header_row=4)
    for cat in cats:
        tb.add({
            "cat": cat,
            "eval": lambda r: f'=COUNTIFS({I.rng("cat")},$A{r},{I.rng("status")},"<>Prévu")',
            "nr": lambda r: f'=COUNTIFS({I.rng("cat")},$A{r},{I.rng("status")},"Non réalisé")',
            "ab": lambda r: f'=COUNTIFS({I.rng("cat")},$A{r},{I.rng("status")},"Abandonné")',
            "rep": lambda r: f'=COUNTIFS({I.rng("cat")},$A{r},{I.rng("status")},"Reporté")',
            "rate": lambda r: f'=IF(B{r}=0,"",(C{r}+D{r})/B{r})',
        })
    tb.finish()
    reasons = sorted(set(it["reason"].dropna().str.strip())) if not it.empty else []
    start_row = tb.last + 3
    ws_ab.cell(row=start_row - 1, column=1, value="Raisons citées").font = F_SECTION
    tr2 = Table(ws_ab, [Col("reason", "Raison", 24), Col("count", "Nombre de fois", 10, FMT_INT)], header_row=start_row)
    ws_ab.freeze_panes = "A5"
    for reason in reasons:
        tr2.add({"reason": reason, "count": lambda r: f'=COUNTIFS({I.rng("reason")},$A{r})'})

    # Objectifs (valeurs calculées par PEI, sous objectifs inclus)
    _title(ws_g, "Objectifs", "Progression calculée par PEI au moment de l'export, en incluant les actions des sous objectifs.")
    tg = Table(ws_g, [
        Col("title", "Objectif", 40, wrap=True), Col("horizon", "Horizon", 13), Col("dim", "Dimension", 18),
        Col("status", "Statut", 11), Col("parent", "Objectif parent", 32, wrap=True), Col("target", "Échéance", 12, FMT_DATE),
        Col("n", "Actions reliées", 11, FMT_INT), Col("rate", "Taux de réalisation", 12, FMT_PCT),
        Col("hours", "Heures investies", 11, FMT_DEC), Col("last", "Dernière action", 12, FMT_DATE),
    ], header_row=4)
    for g in analytics.goals_progress(session):
        tg.add({"title": g["title"], "horizon": HORIZONS.get(g["horizon"], g["horizon"]),
                "dim": dimension_label(g["dimension"]) if g["dimension"] else None,
                "status": GOAL_STATUSES.get(g["status"], g["status"]),
                "parent": goals.get(g["parent_id"]) if g["parent_id"] else None,
                "target": date.fromisoformat(g["target_date"]) if g["target_date"] else None,
                "n": g["n_intentions"], "rate": g["completion_rate"], "hours": g["hours"],
                "last": date.fromisoformat(g["last_action"]) if g["last_action"] else None})
    tg.finish()

    # Compétences et évaluations
    te = Table(ws_e, [Col("skill", "Compétence", 22), Col("date", "Date", 12, FMT_DATE), Col("rating", "Auto évaluation (sur 5)", 13, "0.0"),
                      Col("score", "Score objectif (sur 100)", 13, FMT_INT), Col("etype", "Type de preuve", 14),
                      Col("evidence", "Preuve", 40, wrap=True), Col("comment", "Commentaire", 30, wrap=True)])
    skill_objs = session.query(m.Skill).order_by(m.Skill.name).all()
    for s in skill_objs:
        for p in s.progress:
            te.add({"skill": s.name, "date": p.date, "rating": p.self_rating, "score": p.objective_score,
                    "etype": p.evidence_type, "evidence": p.evidence, "comment": p.comment})
    te.finish()
    _title(ws_s, "Compétences", "Ressenti (dernière auto évaluation) et preuves observables (heures et séances sur la période).")
    tsk = Table(ws_s, [
        Col("name", "Compétence", 24), Col("target", "Niveau visé", 11, FMT_INT), Col("rating", "Dernière auto évaluation", 13, "0.0"),
        Col("first", "Première auto évaluation", 13, "0.0"), Col("change", "Évolution du ressenti", 12, "+0.0;-0.0;0"),
        Col("hours", "Heures de pratique", 12, FMT_DEC), Col("sessions", "Séances", 10, FMT_INT),
        Col("results", "Séances avec résultat", 12, FMT_INT), Col("evals", "Évaluations", 11, FMT_INT),
    ], header_row=4)
    for s in skill_objs:
        summ = skill_service.summary(session, s)
        tsk.add({
            "name": s.name, "target": s.target_level, "rating": summ["current_rating"], "first": summ["first_rating"],
            "change": lambda r: f'=IF(AND(ISNUMBER(C{r}),ISNUMBER(D{r})),C{r}-D{r},"")',
            "hours": lambda r: f"=SUMIFS({A.rng('min')},{A.rng('skill')},$A{r})/60",
            "sessions": lambda r: f"=COUNTIFS({A.rng('skill')},$A{r})",
            "results": lambda r: f'=COUNTIFS({A.rng("skill")},$A{r},{A.rng("result")},"<>")',
            "evals": lambda r: f"=COUNTIFS({te.rng('skill')},$A{r})",
        })
    tsk.finish()

    # Analyses statistiques (valeurs calculées par PEI)
    _title(ws_an, "Analyses statistiques", "Valeurs calculées par PEI au moment de l'export. "
                                           + analytics.CAUSALITY_NOTE)
    row = 4

    def block(title: str, method: str, cols: list[Col], rows: list[dict]) -> None:
        nonlocal row
        ws_an.cell(row=row, column=1, value=title).font = F_SECTION
        _note(ws_an, row + 1, method)
        t = Table(ws_an, cols, header_row=row + 2)
        for rr in rows:
            t.add(rr)
        if not rows:
            _note(ws_an, row + 3, "Pas assez de données pour cette analyse.")
        row = t.last + 3

    trends = analytics.trends(daily, fr=fr)
    block("Tendances des 3 dernières semaines", "Comparaison avec les 3 semaines précédentes, test de Mann Whitney (p).",
          [Col("label", "Indicateur", 34), Col("dir", "Sens", 10), Col("before", "Avant", 10, "0.0"),
           Col("recent", "Récent", 10, "0.0"), Col("p", "p", 10, "0.0000"), Col("msg", "Lecture", 70, wrap=True)],
          [{"label": t["label"], "dir": t["direction"], "before": t["before"], "recent": t["recent"],
            "p": t["p_value"], "msg": t["message"]} for t in trends])
    corr = analytics.correlations(daily)
    block("Associations entre indicateurs", "Corrélation de Spearman (rho), q = p valeur corrigée de Benjamini Hochberg.",
          [Col("x", "Variable 1", 34), Col("y", "Variable 2", 22), Col("rho", "rho", 10, "0.000"), Col("n", "Jours", 10, FMT_INT),
           Col("q", "q", 10, "0.0000"), Col("read", "Lecture", 30)],
          [{"x": p["x_label"], "y": p["y_label"], "rho": p["rho"], "n": p["n"], "q": p["q_value"],
            "read": f"{p['strength']}, {'nette' if p['significant'] else 'incertaine'}"} for p in corr["pairs"][:20]])
    block("Jours atypiques", "Écart à la médiane glissante sur 28 jours, mesuré en écarts robustes (MAD).",
          [Col("date", "Date", 34, FMT_DATE), Col("label", "Indicateur", 22), Col("value", "Valeur", 10, "0.0"),
           Col("exp", "Habituel", 10, "0.0"), Col("z", "Écart robuste", 10, "0.0"), Col("dir", "Sens", 30)],
          [{"date": date.fromisoformat(a["date"]), "label": a["label"], "value": a["value"], "exp": a["expected"],
            "z": a["z"], "dir": a["direction"]} for a in analytics.anomalies(daily)[:30]])
    eff = analytics.intention_count_effect(fr, daily)
    block("Nombre d'intentions et réalisation", "Taux de réalisation moyen selon le nombre d'intentions fixées le matin.",
          [Col("bucket", "Intentions fixées", 34), Col("rate", "Taux moyen", 22, FMT_PCT), Col("n", "Jours", 10, FMT_INT)],
          [{"bucket": b["bucket"], "rate": b["completion_rate"], "n": b["n_days"]} for b in (eff or {}).get("buckets", [])])
    block("Recommandations", "Générées à partir des analyses ci dessus, avec leur mise en garde.",
          [Col("title", "Recommandation", 34), Col("msg", "Message", 70, wrap=True), Col("caveat", "Mise en garde", 50, wrap=True)],
          [{"title": i["title"], "msg": i["message"], "caveat": i.get("caveat")} for i in analytics.insights(session, start, end)])
    ws_an.freeze_panes = None

    # Décisions, expériences, relations, médias
    td = Table(ws_d, [Col("date", "Date", 12, FMT_DATE), Col("title", "Décision", 34, wrap=True), Col("context", "Contexte", 30, wrap=True),
                      Col("reasons", "Raisons", 30, wrap=True), Col("alt", "Alternatives", 24, wrap=True), Col("choice", "Choix", 24, wrap=True),
                      Col("conf", "Confiance (sur 5)", 11, FMT_INT), Col("review", "Revue prévue", 12, FMT_DATE),
                      Col("outcome", "Résultat", 30, wrap=True), Col("rating", "Appréciation (sur 5)", 12, FMT_INT),
                      Col("lessons", "Leçon", 30, wrap=True)])
    for d in session.query(m.Decision).order_by(m.Decision.date).all():
        td.add({"date": d.date, "title": d.title, "context": d.context, "reasons": d.reasons, "alt": d.alternatives,
                "choice": d.choice, "conf": d.confidence, "review": d.review_date, "outcome": d.outcome,
                "rating": d.outcome_rating, "lessons": d.lessons})
    td.finish()
    tx = Table(ws_x, [Col("title", "Expérience", 28, wrap=True), Col("hyp", "Hypothèse", 40, wrap=True), Col("start", "Début", 12, FMT_DATE),
                      Col("end", "Fin", 12, FMT_DATE), Col("metric", "Indicateur", 20), Col("base", "Moyenne avant", 11, "0.00"),
                      Col("exp", "Moyenne pendant", 11, "0.00"), Col("p", "p", 9, "0.000"), Col("msg", "Lecture", 50, wrap=True)])
    for e in session.query(m.Experiment).order_by(m.Experiment.start_date).all():
        an = analytics.experiment_analysis(session, e)
        tx.add({"title": e.title, "hyp": e.hypothesis, "start": e.start_date, "end": e.end_date, "metric": an.get("label"),
                "base": an.get("baseline_mean"), "exp": an.get("experiment_mean"), "p": an.get("p_value"), "msg": an.get("message")})
    tx.finish()
    tp = Table(ws_p, [Col("name", "Personne", 22), Col("rel", "Relation", 14), Col("every", "Contact souhaité (jours)", 13, FMT_INT),
                      Col("n", "Échanges", 10, FMT_INT), Col("last", "Dernier échange", 13, FMT_DATE),
                      Col("since", "Jours depuis", 11, FMT_INT), Col("todo", "À relancer", 11)])
    for p in session.query(m.Person).order_by(m.Person.name).all():
        last = max((i.date for i in p.interactions), default=None)
        tp.add({"name": p.name, "rel": p.relation, "every": p.contact_every_days, "n": len(p.interactions), "last": last,
                "since": lambda r: f'=IF(ISNUMBER(E{r}),TODAY()-E{r},"")',
                "todo": lambda r: f'=IF(AND(ISNUMBER(C{r}),ISNUMBER(F{r})),IF(F{r}>C{r},"Oui","Non"),"")'})
    tp.finish()
    tmd = Table(ws_m, [Col("date", "Date", 12, FMT_DATE), Col("type", "Type", 10), Col("name", "Fichier", 30), Col("caption", "Légende", 30, wrap=True),
                       Col("size", "Taille (Ko)", 11, "#,##0"), Col("status", "Transcription", 13),
                       Col("text", "Texte transcrit", 60, wrap=True), Col("sha", "Empreinte SHA 256", 22)])
    mq = session.query(m.Media).outerjoin(m.Day)
    if start:
        mq = mq.filter(m.Day.date >= start)
    if end:
        mq = mq.filter(m.Day.date <= end)
    for md in mq.order_by(m.Media.created_at).all():
        tmd.add({"date": md.day.date if md.day else md.created_at.date(), "type": md.type, "name": md.original_name,
                 "caption": md.caption, "size": round((md.size_bytes or 0) / 1024, 1),
                 "status": md.transcription_status, "text": md.transcription, "sha": md.sha256})
    tmd.finish()

    # Synthèse : indicateurs clés par formules
    ws = ws_syn
    _title(ws, "Personal Evolution Intelligence", f"Export du {datetime.now():%d/%m/%Y à %H:%M}, période du "
                                                  f"{p_start:%d/%m/%Y} au {p_end:%d/%m/%Y}")
    ws.column_dimensions["A"].width = 44
    for col in "BCDEF":
        ws.column_dimensions[col].width = 16
    ws["A4"] = "Indicateurs clés"
    ws["A4"].font = F_SECTION
    kpis = [
        ("Jours de la période", f"=COUNTA({Q.rng('date')})", FMT_INT),
        ("Jours renseignés", f'=COUNTIFS({Q.rng("logged")},"Oui")', FMT_INT),
        ("Régularité", "=IFERROR(B6/B5,0)", FMT_PCT),
        ("Intentions fixées", f"=COUNTA({I.rng('id')})", FMT_INT),
        ("Intentions évaluées", f'=COUNTIFS({I.rng("status")},"<>Prévu",{I.rng("id")},"<>")', FMT_INT),
        ("Intentions réalisées (totalement ou en partie)",
         f'=COUNTIFS({I.rng("status")},"Réalisé")+COUNTIFS({I.rng("status")},"Partiel")', FMT_INT),
        ("Taux de réalisation", f'=IFERROR(SUM({I.rng("score")})/B9,"")', FMT_PCT),
        ("Temps total suivi (heures)", f"=SUM({A.rng('min')})/60", FMT_DEC),
        ("Temps moyen suivi par jour renseigné (minutes)", f"=IFERROR(SUM({A.rng('min')})/B6,\"\")", FMT_DEC),
        ("Écart moyen entre temps prévu et temps réel (minutes)", f'=IFERROR(AVERAGE({I.rng("gap")}),"")', FMT_DEC),
        ("Sommeil moyen (heures)", f'=IFERROR(AVERAGE({Q.rng("sleep_hours")}),"")', FMT_DEC),
        ("Énergie moyenne (sur 5)", f'=IFERROR(AVERAGE({Q.rng("energy")}),"")', "0.00"),
        ("Humeur moyenne (sur 5)", f'=IFERROR(AVERAGE({Q.rng("mood")}),"")', "0.00"),
        ("Réflexions écrites", f"=COUNTA({R.rng('content')})", FMT_INT),
        ("Plus grand nombre d'heures en une semaine", f"=MAX({tw.rng('hours')})", FMT_DEC),
    ]
    for k, (label, formula, fmt) in enumerate(kpis):
        r = 5 + k
        ws.cell(row=r, column=1, value=label).font = F_BODY
        c = ws.cell(row=r, column=2, value=formula)
        c.font, c.number_format, c.fill = F_BOLD, fmt, FILL_KPI
        ws.cell(row=r, column=1).border = ws.cell(row=r, column=2).border = BORDER_ROW
    ws.cell(row=11, column=3, value="Réalisé = 1, Partiel = 0,5, autres statuts = 0").font = F_SUB

    r0 = 5 + len(kpis) + 2
    ws.cell(row=r0, column=1, value="Par dimension de vie").font = F_SECTION
    td_ = Table(ws, [Col("dim", "Dimension", 44), Col("hours", "Heures", 16, FMT_DEC), Col("n", "Intentions", 16, FMT_INT),
                     Col("rate", "Taux de réalisation", 16, FMT_PCT), Col("share", "Part du temps", 16, FMT_PCT)],
                header_row=r0 + 1)
    for lbl in DIM_LABELS:
        td_.add({
            "dim": lbl,
            "hours": lambda r: f"=SUMIFS({A.rng('min')},{A.rng('dim')},$A{r})/60",
            "n": lambda r: f"=COUNTIFS({I.rng('dim')},$A{r})",
            "rate": lambda r: (f'=IFERROR(SUMIFS({I.rng("score")},{I.rng("dim")},$A{r})/'
                               f'COUNTIFS({I.rng("dim")},$A{r},{I.rng("status")},"<>Prévu"),"")'),
            "share": lambda r: f'=IFERROR(B{r}/$B$12,"")',
        })
    ws.freeze_panes = None

    # Graphiques
    bar = BarChart()
    bar.type = "bar"
    bar.title = "Heures par dimension"
    bar.style = 10
    bar.y_axis.title = "heures"
    bar.add_data(Reference(ws, min_col=2, min_row=td_.header_row, max_row=td_.last), titles_from_data=True)
    bar.set_categories(Reference(ws, min_col=1, min_row=td_.first, max_row=td_.last))
    bar.legend = None
    bar.series[0].graphicalProperties.solidFill = GREEN
    bar.height, bar.width = 8, 15
    ws.add_chart(bar, "G4")

    line = LineChart()
    line.title = "Taux de réalisation par semaine"
    line.style = 12
    line.y_axis.number_format = "0%"
    line.y_axis.scaling.min, line.y_axis.scaling.max = 0, 1
    line.add_data(Reference(ws_w, min_col=8, min_row=tw.header_row, max_row=tw.last), titles_from_data=True)
    line.set_categories(Reference(ws_w, min_col=1, min_row=tw.first, max_row=tw.last))
    line.legend = None
    line.series[0].graphicalProperties.line.solidFill = RED
    line.series[0].graphicalProperties.line.width = 28000
    line.height, line.width = 8, 15
    ws.add_chart(line, "G21")

    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    guide_row = td_.last + 3
    ws.cell(row=guide_row, column=1, value="Contenu du classeur").font = F_SECTION
    guide = [
        ("Quotidien", "Une ligne par jour : indicateurs déclarés et totaux calculés par formules."),
        ("Hebdomadaire, Mensuel", "Agrégats par semaine et par mois (formules)."),
        ("Intentions, Activites, Reflexions", "Données brutes de la période. Modifiables : les indicateurs se recalculent."),
        ("Calibration, Abandons", "Temps prévu contre temps réel, objectifs non réalisés et raisons (formules)."),
        ("Objectifs, Competences, Evaluations", "Progression des objectifs et des compétences."),
        ("Analyses", "Tendances, associations, jours atypiques, recommandations (valeurs calculées par PEI)."),
        ("Decisions, Experiences, Relations, Medias", "Journal des décisions, expériences, relations et fichiers."),
    ]
    for k, (sheet, txt) in enumerate(guide, start=1):
        ws.cell(row=guide_row + k, column=1, value=sheet).font = F_BOLD
        ws.cell(row=guide_row + k, column=2, value=txt).font = F_BODY

    for sheet in wb.worksheets:
        sheet.sheet_view.showGridLines = sheet.title not in ("Synthese",)
    ws_syn.sheet_properties.tabColor = GREEN
    for sh in (ws_q, ws_w, ws_mo):
        sh.sheet_properties.tabColor = YELLOW
    ws_an.sheet_properties.tabColor = RED
    return wb


def export_bytes(session: Session, start: date | None = None, end: date | None = None) -> bytes:
    buf = io.BytesIO()
    build_workbook(session, start, end).save(buf)
    return buf.getvalue()


def filename(start: date | None, end: date | None) -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    if start or end:
        return f"PEI_export_{(start or date.min):%Y%m%d}_{(end or date.today()):%Y%m%d}.xlsx"
    return f"PEI_export_complet_{stamp}.xlsx"
