"""Analyses statistiques longitudinales.

Toutes les fonctions partent des mêmes tables (Pandas) afin que l'API, le
tableau de bord Shiny et les modèles prédictifs voient exactement les mêmes
chiffres. Les associations sont présentées comme telles : une corrélation
n'établit pas une causalité.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy.orm import Session

from .. import models as m
from ..domain import DIMENSIONS, dimension_label

CAUSALITY_NOTE = "Association statistique observée dans tes données, ce qui ne prouve pas une relation de cause à effet."

STATUS_SCORE = {"realise": 1.0, "partiel": 0.5, "non_realise": 0.0, "abandonne": 0.0, "reporte": 0.0}

METRIC_LABELS = {
    "completion_rate": "Taux de réalisation",
    "n_intentions": "Nombre d'intentions",
    "n_done": "Intentions réalisées",
    "planned_minutes": "Temps prévu (min)",
    "actual_minutes": "Temps réalisé (min)",
    "sleep_hours": "Sommeil (h)",
    "sleep_quality": "Qualité du sommeil",
    "energy": "Énergie",
    "motivation": "Motivation",
    "mood": "Humeur",
    "stress": "Stress",
    "fatigue": "Fatigue",
    "screen_minutes": "Temps d'écran (min)",
    "sedentary_minutes": "Temps sédentaire (min)",
    "water_liters": "Hydratation (l)",
    "steps": "Pas",
    "n_reflections": "Réflexions écrites",
}
for _k, _v in DIMENSIONS.items():
    METRIC_LABELS[f"min_{_k}"] = f"Minutes {_v['label']}"

DAY_COLUMNS = ["sleep_hours", "sleep_quality", "energy", "motivation", "mood", "stress", "fatigue",
               "screen_minutes", "sedentary_minutes", "water_liters", "steps"]


@dataclass
class Frames:
    days: pd.DataFrame
    intentions: pd.DataFrame
    activities: pd.DataFrame
    reflections: pd.DataFrame


def load_frames(session: Session, start: date | None = None, end: date | None = None) -> Frames:
    q_days = session.query(m.Day)
    if start:
        q_days = q_days.filter(m.Day.date >= start)
    if end:
        q_days = q_days.filter(m.Day.date <= end)
    days = q_days.all()
    ids = {d.id: d.date for d in days}

    days_df = pd.DataFrame([{"day_id": d.id, "date": pd.Timestamp(d.date), **{c: getattr(d, c) for c in DAY_COLUMNS},
                             "highlight": d.highlight} for d in days],
                           columns=["day_id", "date", *DAY_COLUMNS, "highlight"])

    def _in_range(model):
        return session.query(model).filter(model.day_id.in_(list(ids))).all() if ids else []

    ints = _in_range(m.Intention)
    int_df = pd.DataFrame([{
        "id": i.id, "day_id": i.day_id, "date": pd.Timestamp(ids[i.day_id]), "dimension": i.dimension,
        "category": i.category or "Autre", "description": i.description, "priority": i.priority,
        "estimated_minutes": i.estimated_minutes, "actual_minutes": i.actual_minutes, "status": i.status,
        "goal_id": i.goal_id, "reason": i.reason, "result": i.result,
    } for i in ints], columns=["id", "day_id", "date", "dimension", "category", "description", "priority",
                               "estimated_minutes", "actual_minutes", "status", "goal_id", "reason", "result"])
    if not int_df.empty:
        int_df["score"] = int_df["status"].map(STATUS_SCORE)
        int_df["closed"] = int_df["status"] != "prevu"
        counts = int_df.groupby("day_id")["id"].transform("count")
        int_df["n_same_day"] = counts
    else:
        int_df["score"] = pd.Series(dtype=float)
        int_df["closed"] = pd.Series(dtype=bool)
        int_df["n_same_day"] = pd.Series(dtype=int)

    acts = _in_range(m.Activity)
    act_df = pd.DataFrame([{
        "id": a.id, "day_id": a.day_id, "date": pd.Timestamp(ids[a.day_id]), "dimension": a.dimension,
        "category": a.category or "Autre", "description": a.description, "minutes": a.duration_minutes or 0,
        "intention_id": a.intention_id, "skill_id": a.skill_id, "result": a.result,
    } for a in acts], columns=["id", "day_id", "date", "dimension", "category", "description", "minutes",
                               "intention_id", "skill_id", "result"])

    refs = _in_range(m.Reflection)
    ref_df = pd.DataFrame([{"id": r.id, "date": pd.Timestamp(ids[r.day_id]), "kind": r.kind, "dimension": r.dimension,
                            "content": r.content} for r in refs], columns=["id", "date", "kind", "dimension", "content"])
    return Frames(days_df, int_df, act_df, ref_df)


def daily_series(fr: Frames, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    """Une ligne par jour calendaire, y compris les jours sans saisie (logged = False)."""
    dates = list(fr.days["date"]) + list(fr.intentions["date"]) + list(fr.activities["date"])
    if not dates and not (start and end):
        return pd.DataFrame(columns=["date", *METRIC_LABELS, "logged", "weekday"]).set_index("date")
    lo = pd.Timestamp(start) if start else min(dates)
    hi = pd.Timestamp(end) if end else max(dates)
    idx = pd.date_range(lo, hi, freq="D", name="date")
    df = pd.DataFrame(index=idx)

    if not fr.days.empty:
        df = df.join(fr.days.set_index("date")[DAY_COLUMNS].apply(pd.to_numeric, errors="coerce"))
    else:
        for c in DAY_COLUMNS:
            df[c] = np.nan

    it = fr.intentions
    if not it.empty:
        g = it.groupby("date")
        df["n_intentions"] = g["id"].count()
        df["n_closed"] = g["closed"].sum()
        df["n_done"] = g["status"].apply(lambda s: int(s.isin(["realise", "partiel"]).sum()))
        df["score_sum"] = g["score"].sum(min_count=1)
        df["planned_minutes"] = g["estimated_minutes"].sum(min_count=1)
    for c in ("n_intentions", "n_closed", "n_done"):
        df[c] = df.get(c, pd.Series(0, index=idx)).fillna(0).astype(int)
    df["planned_minutes"] = df.get("planned_minutes", pd.Series(np.nan, index=idx))
    score = df.get("score_sum", pd.Series(np.nan, index=idx))
    df["completion_rate"] = np.where(df["n_closed"] > 0, score / df["n_closed"].replace(0, np.nan), np.nan)
    df = df.drop(columns=["score_sum"], errors="ignore")

    ac = fr.activities
    df["actual_minutes"] = ac.groupby("date")["minutes"].sum() if not ac.empty else 0
    df["actual_minutes"] = df["actual_minutes"].fillna(0)
    for dim in DIMENSIONS:
        col = f"min_{dim}"
        if not ac.empty:
            df[col] = ac[ac["dimension"] == dim].groupby("date")["minutes"].sum()
        df[col] = df.get(col, pd.Series(0, index=idx)).fillna(0)

    rf = fr.reflections
    df["n_reflections"] = rf.groupby("date")["id"].count() if not rf.empty else 0
    df["n_reflections"] = df["n_reflections"].fillna(0).astype(int)

    logged_dates = set(fr.days["date"]) | set(it["date"]) | set(ac["date"])
    df["logged"] = df.index.isin(list(logged_dates))
    df["weekday"] = df.index.dayofweek
    return df


def _round(x, nd=2):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return None
    if isinstance(x, (np.floating, float)):
        return round(float(x), nd)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def streaks(logged: pd.Series) -> tuple[int, int]:
    """(série en cours, plus longue série) de jours consécutifs renseignés."""
    longest = current = 0
    for v in logged.values:
        current = current + 1 if v else 0
        longest = max(longest, current)
    return current, longest


def summary(session: Session, start: date | None = None, end: date | None = None) -> dict:
    fr = load_frames(session, start, end)
    daily = daily_series(fr, start, end)
    it, ac = fr.intentions, fr.activities
    if daily.empty:
        return {"empty": True, "n_days": 0}
    closed = it[it["closed"]] if not it.empty else it
    current, longest = streaks(daily["logged"])
    by_dim = []
    for dim, meta in DIMENSIONS.items():
        mins = int(ac.loc[ac["dimension"] == dim, "minutes"].sum()) if not ac.empty else 0
        ints = it[it["dimension"] == dim] if not it.empty else it
        cl = ints[ints["closed"]] if not ints.empty else ints
        by_dim.append({
            "dimension": dim, "label": meta["label"], "icon": meta["icon"], "minutes": mins,
            "hours": round(mins / 60, 1), "n_intentions": int(len(ints)),
            "completion_rate": _round(cl["score"].mean()) if len(cl) else None,
            "n_activities": int((ac["dimension"] == dim).sum()) if not ac.empty else 0,
        })
    top = []
    if not ac.empty:
        cat = ac.groupby(["category", "dimension"], dropna=False)["minutes"].agg(["sum", "count"]).reset_index()
        cat = cat.sort_values("sum", ascending=False).head(10)
        top = [{"category": r.category, "dimension": r.dimension, "dimension_label": dimension_label(r.dimension),
                "minutes": int(r["sum"]), "hours": round(r["sum"] / 60, 1), "sessions": int(r["count"])}
               for _, r in cat.iterrows()]
    highlights = []
    if not fr.reflections.empty:
        ev = fr.reflections[fr.reflections["kind"].isin(["evenement", "reussite", "apprentissage"])]
        highlights = [{"date": str(r.date.date()), "kind": r.kind, "content": r.content}
                      for r in ev.sort_values("date", ascending=False).head(8).itertuples()]
    est = closed.dropna(subset=["estimated_minutes", "actual_minutes"]) if len(closed) else closed
    return {
        "empty": False,
        "start": str(daily.index.min().date()),
        "end": str(daily.index.max().date()),
        "n_days": int(len(daily)),
        "n_logged_days": int(daily["logged"].sum()),
        "regularity": _round(daily["logged"].mean()),
        "current_streak": current,
        "longest_streak": longest,
        "n_intentions": int(len(it)),
        "n_reviewed": int(len(closed)),
        "n_done": int(closed["status"].isin(["realise", "partiel"]).sum()) if len(closed) else 0,
        "n_abandoned": int(closed["status"].isin(["abandonne", "non_realise"]).sum()) if len(closed) else 0,
        "completion_rate": _round(closed["score"].mean()) if len(closed) else None,
        "total_minutes": int(ac["minutes"].sum()) if not ac.empty else 0,
        "total_hours": round(float(ac["minutes"].sum()) / 60, 1) if not ac.empty else 0,
        "planned_minutes_reviewed": int(est["estimated_minutes"].sum()) if len(est) else 0,
        "actual_minutes_reviewed": int(est["actual_minutes"].sum()) if len(est) else 0,
        "avg_mood": _round(daily["mood"].mean()),
        "avg_energy": _round(daily["energy"].mean()),
        "avg_motivation": _round(daily["motivation"].mean()),
        "avg_sleep": _round(daily["sleep_hours"].mean()),
        "dimensions": by_dim,
        "top_categories": top,
        "highlights": highlights,
    }


def weekly(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return daily
    sums = [c for c in daily.columns if c.startswith("min_")] + ["actual_minutes", "planned_minutes", "n_intentions",
                                                                 "n_done", "n_closed", "n_reflections"]
    means = ["completion_rate", "mood", "energy", "motivation", "sleep_hours", "stress", "screen_minutes", "steps"]
    agg = {c: "sum" for c in sums if c in daily}
    agg.update({c: "mean" for c in means if c in daily})
    agg["logged"] = "mean"
    return daily.resample("W-MON", label="left", closed="left").agg(agg)


def calibration(fr: Frames) -> dict:
    """Temps estimé contre temps réellement utilisé, par type de tâche."""
    it = fr.intentions
    if it.empty:
        return {"n": 0, "categories": [], "overall": None}
    d = it.dropna(subset=["estimated_minutes", "actual_minutes"])
    d = d[(d["estimated_minutes"] > 0) & (d["actual_minutes"] > 0)].copy()
    if d.empty:
        return {"n": 0, "categories": [], "overall": None}
    d["error"] = d["actual_minutes"] - d["estimated_minutes"]
    d["ratio"] = d["actual_minutes"] / d["estimated_minutes"]

    def describe(g: pd.DataFrame) -> dict:
        ratio = float(g["ratio"].median())
        n = int(len(g))
        if n >= 3 and ratio > 1.1:
            bias = "sous estimation"
            msg = f"Tu prévois généralement moins de temps que nécessaire (environ {round((ratio - 1) * 100)} % de plus en réalité)."
        elif n >= 3 and ratio < 0.9:
            bias = "surestimation"
            msg = f"Tu prévois généralement plus de temps que nécessaire (environ {round((1 - ratio) * 100)} % de moins en réalité)."
        else:
            bias = "juste" if n >= 3 else "insuffisant"
            msg = "Tes estimations sont plutôt justes." if n >= 3 else "Pas encore assez d'observations."
        lo, hi = (np.percentile(g["ratio"], [25, 75]) if n >= 4 else (np.nan, np.nan))
        return {"n": n, "mean_estimated": _round(g["estimated_minutes"].mean(), 1),
                "mean_actual": _round(g["actual_minutes"].mean(), 1), "mean_error": _round(g["error"].mean(), 1),
                "median_ratio": _round(ratio), "ratio_q1": _round(lo), "ratio_q3": _round(hi),
                "mae": _round(g["error"].abs().mean(), 1), "bias": bias, "message": msg}

    cats = []
    for (cat, dim), g in d.groupby(["category", "dimension"], dropna=False):
        cats.append({"category": cat, "dimension": dim, "dimension_label": dimension_label(dim), **describe(g)})
    cats.sort(key=lambda c: -c["n"])
    return {"n": int(len(d)), "overall": describe(d), "categories": cats,
            "points": d[["date", "category", "estimated_minutes", "actual_minutes"]]
            .assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d")).to_dict("records")}


def abandons(fr: Frames) -> dict:
    it = fr.intentions
    if it.empty:
        return {"categories": [], "reasons": []}
    cl = it[it["closed"]]
    if cl.empty:
        return {"categories": [], "reasons": []}
    g = cl.groupby(["category", "dimension"], dropna=False).agg(
        n=("id", "count"), abandoned=("status", lambda s: int(s.isin(["abandonne", "non_realise"]).sum())),
        reported=("status", lambda s: int((s == "reporte").sum())), score=("score", "mean")).reset_index()
    g["abandon_rate"] = g["abandoned"] / g["n"]
    g = g[g["n"] >= 2].sort_values(["abandon_rate", "n"], ascending=[False, False])
    reasons = (cl.loc[cl["status"].isin(["abandonne", "non_realise", "reporte"]), "reason"].dropna()
               .str.strip().str.lower().str.rstrip("."))
    reasons = reasons[reasons != ""].value_counts().head(10)
    return {
        "categories": [{"category": r.category, "dimension": r.dimension, "dimension_label": dimension_label(r.dimension),
                        "n": int(r.n), "abandoned": int(r.abandoned), "reported": int(r.reported),
                        "abandon_rate": _round(r.abandon_rate), "completion_rate": _round(r.score)}
                       for r in g.itertuples()],
        "reasons": [{"reason": k, "count": int(v)} for k, v in reasons.items()],
    }


def category_minutes(fr: Frames, daily: pd.DataFrame, top: int = 8) -> pd.DataFrame:
    """Minutes quotidiennes des catégories d'activités les plus pratiquées (colonnes cat:Nom)."""
    ac = fr.activities
    out = pd.DataFrame(index=daily.index)
    if ac.empty:
        return out
    for cat in ac.groupby("category")["minutes"].sum().sort_values(ascending=False).head(top).index:
        out[f"cat:{cat}"] = ac[ac["category"] == cat].groupby("date")["minutes"].sum()
    return out.reindex(daily.index).fillna(0)


def trends(daily: pd.DataFrame, window_days: int = 21, fr: Frames | None = None) -> list[dict]:
    """Compare la période récente à la précédente et teste la pente sur la période récente."""
    if daily.empty or len(daily) < window_days * 2:
        return []
    if fr is not None:
        daily = daily.join(category_minutes(fr, daily))
    recent = daily.iloc[-window_days:]
    before = daily.iloc[-2 * window_days:-window_days]
    out = []
    metrics = ["completion_rate", "actual_minutes", "mood", "energy", "motivation", "sleep_hours", "screen_minutes",
               "n_intentions"] + [c for c in daily.columns if c.startswith(("min_", "cat:"))]
    weeks = window_days // 7
    for col in metrics:
        a, b = before[col].dropna(), recent[col].dropna()
        if len(a) < 5 or len(b) < 5:
            continue
        ma, mb = float(a.mean()), float(b.mean())
        if col.startswith(("min_", "cat:")) and max(ma, mb) < 10:
            continue
        rel = (mb - ma) / abs(ma) if ma else (1.0 if mb else 0.0)
        try:
            p = float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)
        except ValueError:
            continue
        y = recent[col]
        mask = y.notna()
        slope, pslope = np.nan, np.nan
        if mask.sum() >= 5 and y[mask].nunique() > 1:
            lr = stats.linregress(np.arange(len(y))[mask.values], y[mask].values)
            slope, pslope = lr.slope, lr.pvalue
        if abs(rel) < 0.15 or p > 0.1:
            continue
        label = f"Le temps consacré à {col[4:]}" if col.startswith("cat:") else METRIC_LABELS.get(col, col)
        direction = "hausse" if mb > ma else "baisse"
        unit = " %" if col == "completion_rate" else ""
        fa, fb = (ma * 100, mb * 100) if col == "completion_rate" else (ma, mb)
        out.append({
            "metric": col, "label": label, "direction": direction, "before": _round(fa, 1), "recent": _round(fb, 1),
            "relative_change": _round(rel, 3), "p_value": _round(p, 4), "slope_per_day": _round(slope, 3),
            "slope_p_value": _round(pslope, 4), "window_days": window_days,
            "message": (f"Au cours des {weeks} dernières semaines, {label[0].lower() + label[1:]} est en {direction} "
                        f"(moyenne {_round(fb, 1):g}{unit} contre {_round(fa, 1):g}{unit} sur les {weeks} semaines précédentes)."),
        })
    out.sort(key=lambda t: t["p_value"])
    return out


def anomalies(daily: pd.DataFrame, window: int = 28, threshold: float = 3.0) -> list[dict]:
    """Jours atypiques : écart robuste (médiane et MAD glissantes) supérieur au seuil."""
    if daily.empty or len(daily) < 14:
        return []
    out = []
    metrics = ["actual_minutes", "completion_rate", "mood", "energy", "sleep_hours", "screen_minutes"]
    for col in metrics:
        s = daily[col].astype(float)
        if s.notna().sum() < 14:
            continue
        med = s.rolling(window, min_periods=10).median().shift(1)
        mad = (s - med).abs().rolling(window, min_periods=10).median().shift(1)
        scale = 1.4826 * mad.replace(0, np.nan)
        floor = max(float(s.std(skipna=True) or 0) * 0.75, 1e-6)
        z = (s - med) / scale.fillna(floor).clip(lower=floor)
        for ts, val in z[z.abs() >= threshold].items():
            out.append({"date": str(ts.date()), "metric": col, "label": METRIC_LABELS.get(col, col),
                        "value": _round(s[ts], 2), "expected": _round(med[ts], 2), "z": _round(val, 2),
                        "direction": "haut" if val > 0 else "bas"})
    out.sort(key=lambda a: a["date"], reverse=True)
    return out


def _bh(pvals: list[float]) -> list[float]:
    """Correction de Benjamini Hochberg pour les tests multiples."""
    n = len(pvals)
    if n == 0:
        return []
    order = np.argsort(pvals)
    adj = np.empty(n)
    prev = 1.0
    for rank, idx in reversed(list(enumerate(order, start=1))):
        prev = min(prev, pvals[idx] * n / rank)
        adj[idx] = prev
    return adj.tolist()


def correlations(daily: pd.DataFrame, min_n: int = 14) -> dict:
    """Associations (Spearman) entre comportements déclarés et résultats de la journée."""
    if daily.empty:
        return {"pairs": [], "note": CAUSALITY_NOTE}
    drivers = ["sleep_hours", "sleep_quality", "energy", "motivation", "stress", "screen_minutes",
               "n_intentions", "steps", "min_spirituel", "min_physique"]
    outcomes = ["completion_rate", "actual_minutes", "mood", "min_etudes", "min_professionnel"]
    # Paires mécaniquement liées (plus d'objectifs implique plus de minutes) : exclues.
    trivial = {("n_intentions", "actual_minutes"), ("n_intentions", "min_etudes"), ("n_intentions", "min_professionnel")}
    rows = []
    d = daily[daily["logged"]]
    for x in drivers:
        for y in outcomes:
            if x == y or x not in d or y not in d or (x, y) in trivial:
                continue
            sub = d[[x, y]].dropna()
            if len(sub) < min_n or sub[x].nunique() < 3 or sub[y].nunique() < 3:
                continue
            rho, p = stats.spearmanr(sub[x], sub[y])
            if np.isnan(rho):
                continue
            rows.append({"x": x, "y": y, "x_label": METRIC_LABELS.get(x, x), "y_label": METRIC_LABELS.get(y, y),
                         "rho": float(rho), "p_value": float(p), "n": int(len(sub))})
    adj = _bh([r["p_value"] for r in rows])
    for r, q in zip(rows, adj):
        r["q_value"] = q
        r["strength"] = ("forte" if abs(r["rho"]) >= 0.5 else "modérée" if abs(r["rho"]) >= 0.3 else "faible")
        r["significant"] = q < 0.05
        r["rho"], r["p_value"], r["q_value"] = round(r["rho"], 3), round(r["p_value"], 4), round(q, 4)
    rows.sort(key=lambda r: -abs(r["rho"]))
    matrix_cols = [c for c in drivers + outcomes if c in d and d[c].notna().sum() >= min_n]
    matrix_cols = list(dict.fromkeys(matrix_cols))
    matrix = d[matrix_cols].corr(method="spearman").round(3) if matrix_cols else pd.DataFrame()
    return {"pairs": rows, "note": CAUSALITY_NOTE,
            "matrix": {"columns": [METRIC_LABELS.get(c, c) for c in matrix.columns],
                       "keys": list(matrix.columns), "values": matrix.fillna(0).values.tolist()}}


def compare_periods(session: Session, a: tuple[date, date], b: tuple[date, date]) -> dict:
    sa, sb = summary(session, *a), summary(session, *b)
    keys = ["regularity", "completion_rate", "total_hours", "avg_mood", "avg_energy", "avg_sleep", "n_intentions"]
    diff = {}
    for k in keys:
        va, vb = sa.get(k), sb.get(k)
        diff[k] = _round(vb - va) if isinstance(va, (int, float)) and isinstance(vb, (int, float)) else None
    return {"a": sa, "b": sb, "difference": diff}


def goals_progress(session: Session) -> list[dict]:
    goals = session.query(m.Goal).all()
    children: dict[int | None, list[m.Goal]] = {}
    for g in goals:
        children.setdefault(g.parent_id, []).append(g)

    def collect(g: m.Goal) -> list[m.Intention]:
        items = list(g.intentions)
        for c in children.get(g.id, []):
            items += collect(c)
        return items

    out = []
    for g in goals:
        items = collect(g)
        closed = [i for i in items if i.status != "prevu"]
        minutes = sum(sum(a.duration_minutes or 0 for a in i.activities) or (i.actual_minutes or 0) for i in items)
        last = max((i.day.date for i in items), default=None)
        out.append({
            "id": g.id, "title": g.title, "horizon": g.horizon, "dimension": g.dimension, "status": g.status,
            "parent_id": g.parent_id, "target_date": str(g.target_date) if g.target_date else None,
            "n_intentions": len(items), "n_reviewed": len(closed),
            "completion_rate": _round(np.mean([STATUS_SCORE.get(i.status, 0) for i in closed])) if closed else None,
            "hours": round(minutes / 60, 1), "last_action": str(last) if last else None,
            "days_since_last_action": (date.today() - last).days if last else None,
        })
    return out


def experiment_analysis(session: Session, exp: m.Experiment) -> dict:
    """Compare la période d'expérience à une période de référence de même durée juste avant."""
    end = exp.end_date or date.today()
    length = (end - exp.start_date).days + 1
    base_start = exp.start_date - timedelta(days=length)
    fr = load_frames(session, base_start, end)
    daily = daily_series(fr, base_start, end)
    metric = exp.metric
    label = METRIC_LABELS.get(metric, metric)
    if daily.empty or metric not in daily:
        return {"status": "insuffisant", "message": "Pas encore de données pour cette métrique.", "metric": metric}
    daily = daily[daily["logged"]]
    base = daily.loc[: pd.Timestamp(exp.start_date) - pd.Timedelta(days=1), metric].dropna()
    test = daily.loc[pd.Timestamp(exp.start_date):, metric].dropna()
    res = {"metric": metric, "label": label, "n_baseline": int(len(base)), "n_experiment": int(len(test)),
           "baseline_period": [str(base_start), str(exp.start_date - timedelta(days=1))],
           "experiment_period": [str(exp.start_date), str(end)],
           "baseline_mean": _round(base.mean()), "experiment_mean": _round(test.mean()),
           "baseline_median": _round(base.median()), "experiment_median": _round(test.median()),
           "note": CAUSALITY_NOTE + " D'autres facteurs ont pu changer pendant la même période."}
    if len(base) < 5 or len(test) < 5:
        res.update(status="insuffisant",
                   message="Au moins 5 jours renseignés sont nécessaires dans chaque période pour conclure.")
        return res
    u = stats.mannwhitneyu(test, base, alternative="two-sided")
    cliff = (2 * u.statistic) / (len(test) * len(base)) - 1  # delta de Cliff
    res.update(p_value=_round(float(u.pvalue), 4), effect_size=_round(float(cliff), 3))
    magnitude = "négligeable" if abs(cliff) < 0.147 else "faible" if abs(cliff) < 0.33 else "moyen" if abs(cliff) < 0.474 else "fort"
    direction = "plus élevé" if test.mean() > base.mean() else "plus faible"
    if u.pvalue < 0.05:
        res.update(status="difference",
                   message=f"Pendant l'expérience, {label.lower()} est {direction} qu'avant (effet {magnitude}, p = {u.pvalue:.3f}).")
    else:
        res.update(status="pas_de_difference",
                   message=f"Pas de différence nette pour {label.lower()} entre les deux périodes (p = {u.pvalue:.3f}).")
    return res


def intention_count_effect(fr: Frames, daily: pd.DataFrame) -> dict | None:
    """Réalise t on plus souvent ses objectifs quand on en fixe peu ?"""
    d = daily[(daily["n_closed"] > 0)].copy()
    if len(d) < 14:
        return None
    d["bucket"] = pd.cut(d["n_intentions"], bins=[0, 3, 4, 5, 100], labels=["1 à 3", "4", "5", "6 et plus"])
    g = d.groupby("bucket", observed=True)["completion_rate"].agg(["mean", "count"])
    g = g[g["count"] >= 4]
    if len(g) < 2:
        return None
    rho, p = stats.spearmanr(d["n_intentions"], d["completion_rate"])
    best = g["mean"].idxmax()
    return {"buckets": [{"bucket": str(k), "completion_rate": _round(v["mean"]), "n_days": int(v["count"])}
                        for k, v in g.iterrows()],
            "best": str(best), "rho": _round(float(rho), 3), "p_value": _round(float(p), 4)}


def weekday_profile(daily: pd.DataFrame) -> list[dict]:
    names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    d = daily[daily["logged"]]
    if d.empty:
        return []
    g = d.groupby("weekday").agg(completion_rate=("completion_rate", "mean"), actual_minutes=("actual_minutes", "mean"),
                                 n=("logged", "count"))
    return [{"weekday": names[int(k)], "completion_rate": _round(r.completion_rate),
             "actual_minutes": _round(r.actual_minutes, 0), "n_days": int(r.n)} for k, r in g.iterrows()]


def insights(session: Session, start: date | None = None, end: date | None = None) -> list[dict]:
    """Recommandations accompagnées de leurs données justificatives."""
    fr = load_frames(session, start, end)
    daily = daily_series(fr)
    out: list[dict] = []
    if daily.empty:
        return out

    eff = intention_count_effect(fr, daily)
    if eff and eff["p_value"] is not None and eff["p_value"] < 0.1 and eff["rho"] < 0:
        best = next(b for b in eff["buckets"] if b["bucket"] == eff["best"])
        out.append({
            "type": "planification", "icon": "target",
            "title": "Moins d'objectifs, plus de réalisations",
            "message": (f"Tes données montrent que tu réalises plus souvent tes objectifs lorsque tu en fixes "
                        f"{best['bucket']} le matin (taux de {round(best['completion_rate'] * 100)} % sur {best['n_days']} jours)."),
            "evidence": eff, "caveat": CAUSALITY_NOTE,
        })

    cal = calibration(fr)
    biased = [c for c in cal.get("categories", []) if c["n"] >= 4 and c["bias"] in ("sous estimation", "surestimation")]
    biased.sort(key=lambda c: -abs((c["median_ratio"] or 1) - 1))
    for c in biased[:2]:
        pct = round(abs((c["median_ratio"] or 1) - 1) * 100)
        more = "plus" if c["bias"] == "sous estimation" else "moins"
        out.append({
            "type": "calibration", "icon": "clock",
            "title": f"Estimation du temps : {c['category']}",
            "message": (f"Les activités « {c['category']} » prennent en moyenne {pct} % de {more} de temps que ton "
                        f"estimation initiale ({c['mean_estimated']:g} min prévues, {c['mean_actual']:g} min réelles, {c['n']} observations)."),
            "evidence": c, "caveat": "Estimation fondée sur l'historique, à ajuster si la nature des tâches change.",
        })

    for t in trends(daily, fr=fr)[:4]:
        out.append({"type": "tendance", "icon": "trend_up" if t["direction"] == "hausse" else "trend_down",
                    "title": f"Tendance : {t['label']}", "message": t["message"], "evidence": t,
                    "caveat": "Comparaison descriptive entre deux périodes consécutives."})

    corr = correlations(daily)
    for pair in [p for p in corr["pairs"] if p["significant"] and abs(p["rho"]) >= 0.3][:3]:
        sens = "plus" if pair["rho"] > 0 else "moins"
        out.append({
            "type": "association", "icon": "link",
            "title": f"{pair['x_label']} et {pair['y_label'].lower()}",
            "message": (f"Les jours où {pair['x_label'].lower()} est plus élevé, {pair['y_label'].lower()} tend à être "
                        f"{sens} élevé (corrélation {pair['strength']}, rho = {pair['rho']}, {pair['n']} jours)."),
            "evidence": pair, "caveat": CAUSALITY_NOTE,
        })

    ab = abandons(fr)
    for c in [c for c in ab["categories"] if c["n"] >= 4 and (c["abandon_rate"] or 0) >= 0.5][:2]:
        reason = f" Raison la plus citée : « {ab['reasons'][0]['reason']} »." if ab["reasons"] else ""
        out.append({
            "type": "abandon", "icon": "alert",
            "title": f"Objectif souvent abandonné : {c['category']}",
            "message": (f"« {c['category']} » n'est pas réalisé dans {round(c['abandon_rate'] * 100)} % des cas "
                        f"({c['abandoned']} sur {c['n']}).{reason} Un format plus court ou un autre moment de la journée peut être testé."),
            "evidence": c, "caveat": "Suggestion à valider par une expérience personnelle.",
        })

    wd = [w for w in weekday_profile(daily) if w["n_days"] >= 3 and w["completion_rate"] is not None]
    if len(wd) >= 5:
        best = max(wd, key=lambda w: w["completion_rate"])
        worst = min(wd, key=lambda w: w["completion_rate"])
        if best["completion_rate"] - worst["completion_rate"] >= 0.2:
            out.append({
                "type": "rythme", "icon": "calendar",
                "title": "Rythme de la semaine",
                "message": (f"Ton meilleur jour est le {best['weekday'].lower()} ({round(best['completion_rate'] * 100)} % de réalisation) "
                            f"et le plus difficile le {worst['weekday'].lower()} ({round(worst['completion_rate'] * 100)} %)."),
                "evidence": {"weekdays": wd}, "caveat": "Description de tes habitudes passées.",
            })

    goals = [g for g in goals_progress(session) if g["status"] == "actif" and g["horizon"] in ("mensuel", "hebdomadaire", "annuel")]
    for g in [g for g in goals if (g["days_since_last_action"] or 0) >= 14][:2]:
        out.append({
            "type": "objectif", "icon": "flag",
            "title": f"Objectif en sommeil : {g['title']}",
            "message": f"Aucune action reliée à cet objectif depuis {g['days_since_last_action']} jours.",
            "evidence": g, "caveat": "Peut être volontaire : à mettre en pause ou à relancer.",
        })

    people = session.query(m.Person).filter(m.Person.contact_every_days.isnot(None)).all()
    for p in people:
        last = max((i.date for i in p.interactions), default=None)
        gap = (date.today() - last).days if last else None
        if gap is None or gap > p.contact_every_days:
            out.append({
                "type": "relation", "icon": "users", "title": f"Relation à entretenir : {p.name}",
                "message": (f"Dernier échange il y a {gap} jours (rythme souhaité : tous les {p.contact_every_days} jours)."
                            if gap is not None else "Aucun échange enregistré pour le moment."),
                "evidence": {"person_id": p.id, "days_since": gap}, "caveat": "Rappel issu de ton propre rythme souhaité.",
            })
    return out
