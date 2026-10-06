"""Modèles prédictifs personnels.

Le niveau de sophistication s'adapte à la quantité de données :
peu d'historique -> taux de base lissés (bayésien) ; assez d'historique ->
régression logistique validée par validation croisée temporelle.
Chaque sortie est une estimation accompagnée de son incertitude.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_SAMPLES_ML = 40
DISCLAIMER = "Estimation fondée sur ton historique, pas une certitude."


def _features(df: pd.DataFrame, days: pd.DataFrame | None) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    X["estimated_minutes"] = df["estimated_minutes"].fillna(df["estimated_minutes"].median() if df["estimated_minutes"].notna().any() else 30)
    X["log_estimated"] = np.log1p(X["estimated_minutes"])
    X["priority_high"] = (df["priority"] == 1).astype(int)
    X["priority_low"] = (df["priority"] == 3).astype(int)
    X["n_same_day"] = df["n_same_day"].fillna(1)
    X["weekend"] = (pd.to_datetime(df["date"]).dt.dayofweek >= 5).astype(int)
    for dim in ["spirituel", "physique", "etudes", "professionnel", "personnel", "relationnel", "loisirs"]:
        X[f"dim_{dim}"] = (df["dimension"] == dim).astype(int)
    if days is not None and not days.empty:
        d = days.set_index("date")[["sleep_hours", "energy", "motivation"]]
        joined = pd.to_datetime(df["date"]).map(lambda t: t)
        for col in ["sleep_hours", "energy", "motivation"]:
            vals = joined.map(d[col]) if col in d else np.nan
            vals = pd.to_numeric(vals, errors="coerce")
            fill = float(vals.median()) if vals.notna().any() else (7 if col == "sleep_hours" else 3)
            X[col] = vals.fillna(fill)
    return X


@dataclass
class CompletionModel:
    kind: str
    n: int
    auc: float | None
    model: object | None
    columns: list[str]
    base_rates: dict
    global_rate: float
    days: pd.DataFrame | None


def fit_completion(intentions: pd.DataFrame, days: pd.DataFrame | None = None) -> CompletionModel:
    data = intentions[intentions["closed"]].copy() if not intentions.empty else intentions
    n = int(len(data))
    if n == 0:
        return CompletionModel("aucune_donnee", 0, None, None, [], {}, 0.5, days)
    y = data["status"].isin(["realise", "partiel"]).astype(int)
    # Lissage bayésien Beta(2, 2) par catégorie puis dimension.
    global_rate = float((y.sum() + 1) / (n + 2))
    rates = {}
    for key in ("category", "dimension"):
        for val, g in data.assign(y=y).groupby(key, dropna=True):
            k, cnt = g["y"].sum(), len(g)
            rates[(key, val)] = {"rate": float((k + 2 * global_rate) / (cnt + 2)), "n": int(cnt)}
    if n < MIN_SAMPLES_ML or y.nunique() < 2:
        return CompletionModel("taux_de_base", n, None, None, [], rates, global_rate, days)

    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import TimeSeriesSplit

    data = data.sort_values("date")
    y = data["status"].isin(["realise", "partiel"]).astype(int)
    X = _features(data, days)
    aucs = []
    for train, test in TimeSeriesSplit(n_splits=4).split(X):
        if y.iloc[train].nunique() < 2 or y.iloc[test].nunique() < 2:
            continue
        clf = LogisticRegression(max_iter=500, C=0.5).fit(X.iloc[train], y.iloc[train])
        aucs.append(roc_auc_score(y.iloc[test], clf.predict_proba(X.iloc[test])[:, 1]))
    clf = LogisticRegression(max_iter=500, C=0.5).fit(X, y)
    return CompletionModel("regression_logistique", n, float(np.mean(aucs)) if aucs else None, clf,
                           list(X.columns), rates, global_rate, days)


def predict_completion(model: CompletionModel, item: dict) -> dict:
    """Probabilité estimée de réaliser une intention."""
    rate_info = model.base_rates.get(("category", item.get("category"))) or model.base_rates.get(
        ("dimension", item.get("dimension")))
    base = rate_info["rate"] if rate_info else model.global_rate
    n_ref = rate_info["n"] if rate_info else model.n
    out = {"model": model.kind, "n_training": model.n, "disclaimer": DISCLAIMER, "base_rate": round(base, 3),
           "n_similar": n_ref}
    if model.kind == "regression_logistique":
        row = pd.DataFrame([{
            "estimated_minutes": item.get("estimated_minutes"), "priority": item.get("priority", 2),
            "n_same_day": item.get("n_intentions") or 3, "date": item.get("date") or pd.Timestamp.today(),
            "dimension": item.get("dimension"),
        }])
        X = _features(row, model.days).reindex(columns=model.columns, fill_value=0)
        p_ml = float(model.model.predict_proba(X)[0, 1])
        # Mélange avec le taux propre à la catégorie pour rester ancré sur l'historique.
        w = min(0.5, n_ref / 40) if rate_info and rate_info["n"] else 0
        p = (1 - w) * p_ml + w * base
        out.update(probability=round(p, 3), auc_validation=round(model.auc, 3) if model.auc else None)
        coefs = dict(zip(model.columns, model.model.coef_[0]))
        out["main_factors"] = [
            {"feature": k, "effect": "favorable" if v > 0 else "défavorable", "weight": round(float(v), 3)}
            for k, v in sorted(coefs.items(), key=lambda kv: -abs(kv[1]))[:4]
        ]
    else:
        out["probability"] = round(base, 3)
    n_eff = max(n_ref, 1)
    se = np.sqrt(out["probability"] * (1 - out["probability"]) / (n_eff + 2))
    out["interval"] = [round(float(max(0.0, out["probability"] - 1.96 * se)), 3),
                       round(float(min(1.0, out["probability"] + 1.96 * se)), 3)]
    return out


def predict_duration(intentions: pd.DataFrame, category: str | None, dimension: str | None, estimated: int) -> dict:
    """Durée probable d'une activité à partir des écarts passés entre prévu et réalisé."""
    d = intentions.dropna(subset=["estimated_minutes", "actual_minutes"]) if not intentions.empty else intentions
    d = d[(d["estimated_minutes"] > 0) & (d["actual_minutes"] > 0)] if len(d) else d
    scope = "aucune"
    sub = d.iloc[0:0] if len(d) else d
    if len(d) and category is not None:
        sub = d[d["category"] == category]
        scope = "categorie"
    if len(sub) < 4 and len(d) and dimension is not None:
        sub = d[d["dimension"] == dimension]
        scope = "dimension"
    if len(sub) < 4:
        sub, scope = d, "global"
    if len(sub) < 3:
        return {"estimated": estimated, "predicted": estimated, "interval": None, "n": int(len(sub)),
                "scope": scope, "message": "Pas encore assez d'historique pour corriger ton estimation.",
                "disclaimer": DISCLAIMER}
    ratio = (sub["actual_minutes"] / sub["estimated_minutes"]).clip(0.1, 10)
    lr = np.log(ratio)
    # Moyenne des log ratios, rétrécie vers 0 (pas de correction) quand n est petit.
    shrink = len(lr) / (len(lr) + 5)
    mu = float(lr.mean()) * shrink
    pred = estimated * np.exp(mu)
    q1, q3 = np.percentile(ratio, [20, 80])
    return {"estimated": estimated, "predicted": int(round(pred)),
            "interval": [int(round(estimated * q1)), int(round(estimated * q3))], "n": int(len(sub)), "scope": scope,
            "median_ratio": round(float(np.median(ratio)), 2),
            "message": f"Pour ce type de tâche, prévois plutôt {int(round(pred))} minutes.", "disclaimer": DISCLAIMER}


def simulate_scenario(intentions: pd.DataFrame, activities: pd.DataFrame, *, category: str | None,
                      dimension: str | None, minutes_per_day: int, days: int, days_per_week: int = 7,
                      n_runs: int = 4000, seed: int = 7) -> dict:
    """Monte Carlo : que pourrait représenter X minutes par jour pendant N jours ?

    La simulation tient compte de ta régularité passée (probabilité de réaliser
    l'activité un jour prévu) et de l'écart habituel entre prévu et réalisé.
    """
    rng = np.random.default_rng(seed)
    it = intentions[intentions["closed"]] if not intentions.empty else intentions
    sub = it
    if len(it) and category:
        sub = it[it["category"] == category]
    if len(sub) < 5 and len(it) and dimension:
        sub = it[it["dimension"] == dimension]
    if len(sub) < 5:
        sub = it
    k = int(sub["status"].isin(["realise", "partiel"]).sum()) if len(sub) else 0
    n = int(len(sub))
    # Incertitude sur la régularité elle même : tirage Beta par simulation.
    p_draws = rng.beta(k + 1, n - k + 1, size=n_runs)
    d = sub.dropna(subset=["estimated_minutes", "actual_minutes"]) if len(sub) else sub
    d = d[(d["estimated_minutes"] > 0) & (d["actual_minutes"] > 0)] if len(d) else d
    ratios = (d["actual_minutes"] / d["estimated_minutes"]).clip(0.1, 3).to_numpy() if len(d) >= 3 else np.array([1.0])
    planned_days = int(round(days * days_per_week / 7))
    done_days = rng.binomial(planned_days, p_draws)
    totals = np.array([
        (rng.choice(ratios, size=nd, replace=True) * minutes_per_day).sum() if nd else 0.0 for nd in done_days
    ]) / 60
    current = 0.0
    if not activities.empty:
        mask = activities["category"] == category if category else activities["dimension"] == dimension
        current = float(activities.loc[mask, "minutes"].sum()) / 60 if mask is not None else 0.0
    ideal = planned_days * minutes_per_day / 60
    p10, p50, p90 = np.percentile(totals, [10, 50, 90])
    return {
        "type": "simulation",
        "category": category, "dimension": dimension, "minutes_per_day": minutes_per_day, "days": days,
        "planned_days": planned_days, "ideal_hours": round(ideal, 1),
        "historical_adherence": round(k / n, 3) if n else None, "n_history": n, "n_ratio_samples": int(len(ratios)),
        "hours_p10": round(float(p10), 1), "hours_median": round(float(p50), 1), "hours_p90": round(float(p90), 1),
        "current_hours": round(current, 1), "projected_total_median": round(current + float(p50), 1),
        "histogram": np.histogram(totals, bins=20)[0].tolist(),
        "histogram_edges": [round(float(x), 1) for x in np.histogram(totals, bins=20)[1]],
        "message": (f"Si ton rythme passé se maintient, {minutes_per_day} minutes par jour pendant {days} jours "
                    f"représenteraient probablement entre {p10:.0f} et {p90:.0f} heures (médiane {p50:.0f} h), "
                    f"contre {ideal:.0f} h si tout était réalisé."),
        "disclaimer": "Simulation à partir de ton historique : une estimation, pas une prédiction certaine.",
    }


def skill_projection(timeline: list[dict], horizon_days: int = 90) -> dict | None:
    """Tendance linéaire de l'auto évaluation d'une compétence, bornée à l'échelle 1 à 5."""
    pts = [(pd.Timestamp(t["date"]), t["self_rating"]) for t in timeline if t.get("self_rating") is not None]
    if len(pts) < 3:
        return None
    t0 = pts[0][0]
    x = np.array([(d - t0).days for d, _ in pts], dtype=float)
    y = np.array([v for _, v in pts], dtype=float)
    if np.ptp(x) == 0:
        return None
    slope, intercept = np.polyfit(x, y, 1)
    future = x[-1] + horizon_days
    proj = float(np.clip(intercept + slope * future, 0, 5))
    resid = y - (intercept + slope * x)
    sd = float(np.std(resid, ddof=1)) if len(y) > 2 else 0.5
    return {"slope_per_month": round(float(slope) * 30, 3), "projected": round(proj, 2),
            "interval": [round(max(0, proj - 2 * sd), 2), round(min(5, proj + 2 * sd), 2)],
            "horizon_days": horizon_days, "disclaimer": DISCLAIMER}
