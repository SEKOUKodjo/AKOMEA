"""Vocabulaire du domaine : dimensions de vie, horizons, statuts."""
from __future__ import annotations

# Dimensions de l'évolution personnelle. La clé est stockée en base,
# le libellé est affiché ; l'icône renvoie à backend/icons.py.
DIMENSIONS: dict[str, dict[str, str]] = {
    "spirituel": {"label": "Spirituel", "icon": "cross"},
    "physique": {"label": "Physique", "icon": "pulse"},
    "etudes": {"label": "Études", "icon": "book"},
    "professionnel": {"label": "Professionnel", "icon": "briefcase"},
    "personnel": {"label": "Personnel", "icon": "user"},
    "relationnel": {"label": "Relationnel", "icon": "users"},
    "loisirs": {"label": "Loisirs et créativité", "icon": "music"},
}

# Hiérarchie : vision, objectifs long terme, annuels, mensuels, hebdomadaires.
HORIZONS: dict[str, str] = {
    "vision": "Vision",
    "long_terme": "Long terme",
    "annuel": "Annuel",
    "mensuel": "Mensuel",
    "hebdomadaire": "Hebdomadaire",
}

GOAL_STATUSES = {"actif": "Actif", "atteint": "Atteint", "en_pause": "En pause", "abandonne": "Abandonné"}

# Statut d'une intention quotidienne.
INTENTION_STATUSES = {
    "prevu": "Prévu",
    "realise": "Réalisé",
    "partiel": "Partiel",
    "non_realise": "Non réalisé",
    "abandonne": "Abandonné",
    "reporte": "Reporté",
}
DONE_STATUSES = {"realise", "partiel"}
CLOSED_STATUSES = {"realise", "partiel", "non_realise", "abandonne", "reporte"}

REFLECTION_KINDS = {
    "reflexion": "Réflexion",
    "apprentissage": "Apprentissage",
    "difficulte": "Difficulté",
    "gratitude": "Gratitude",
    "idee": "Idée",
    "evenement": "Événement marquant",
    "passage": "Passage biblique",
    "engagement": "Engagement",
    "preoccupation": "Préoccupation",
    "reussite": "Réussite",
}

MEDIA_TYPES = {"audio", "video", "image", "document"}
MOMENTS = {"matin": "Matin", "journee": "Journée", "soir": "Soir"}

# Indicateurs quotidiens déclarés (échelle 1 à 5 sauf mention).
DAY_METRICS = {
    "sleep_hours": "Sommeil (heures)",
    "sleep_quality": "Qualité du sommeil",
    "energy": "Énergie",
    "motivation": "Motivation",
    "mood": "Humeur",
    "stress": "Stress",
    "fatigue": "Fatigue",
    "screen_minutes": "Temps d'écran (minutes)",
    "sedentary_minutes": "Temps sédentaire (minutes)",
    "water_liters": "Hydratation (litres)",
    "steps": "Pas",
}


def dimension_label(key: str | None) -> str:
    """Libellé de la dimension dans la langue courante."""
    from .i18n import tr

    if not key:
        return tr("Non classé")
    return tr(DIMENSIONS.get(key, {}).get("label", key))


def label(mapping: dict, key: str | None, default: str = "") -> str:
    """Libellé traduit d'un statut, d'un horizon, d'un type de réflexion..."""
    from .i18n import tr

    if key is None:
        return default
    value = mapping.get(key, key)
    if isinstance(value, dict):
        value = value.get("label", key)
    return tr(value)


def labels(mapping: dict) -> dict[str, str]:
    """Copie traduite d'un dictionnaire de libellés."""
    return {k: label(mapping, k) for k in mapping}
