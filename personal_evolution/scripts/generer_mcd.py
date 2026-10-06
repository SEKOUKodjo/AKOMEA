"""Génère le Modèle Conceptuel de Données (MCD, méthode Merise) de PEI.

    python scripts/generer_mcd.py

Produit dans docs/ :
    mcd.svg   schéma vectoriel
    MCD.md    explications, associations, cardinalités, dictionnaire des données, MLD
    MCD.pdf   le tout en PDF (schéma en A3 paysage), nécessite reportlab

Les propriétés sont lues directement dans backend/models.py : le document reste
fidèle au code.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text  # noqa: E402
from sqlalchemy.types import JSON  # noqa: E402

from backend.models import Base  # noqa: E402

DOCS = ROOT / "docs"
GREEN, YELLOW, RED = "#006A4E", "#FFCE00", "#D21034"
INK, MUTED, ASSO_FILL, ASSO_LINE = "#10231C", "#5B6A63", "#FFF6CC", "#B58F00"

# Entités : nom conceptuel, table, rôle

ENTITIES = {
    "days": ("JOUR", "Une journée vécue et ses indicateurs déclarés (sommeil, énergie, humeur...)."),
    "goals": ("OBJECTIF", "Objectif hiérarchique, de la vision jusqu'à l'objectif hebdomadaire."),
    "intentions": ("INTENTION", "Ce que je veux faire un jour donné (niveau Intention)."),
    "activities": ("ACTIVITE", "Ce que j'ai réellement fait et ce que cela a produit (niveaux Action et Résultat)."),
    "reflections": ("REFLEXION", "Réflexion typée : apprentissage, gratitude, difficulté, passage biblique..."),
    "media": ("MEDIA", "Métadonnées d'un fichier audio, vidéo, image ou document conservé dans storage/."),
    "sources": ("SOURCE", "Donnée brute d'origine (texte saisi, audio transcrit, formulaire), jamais modifiée."),
    "extractions": ("EXTRACTION", "Proposition de l'IA sur une source, puis sa version validée ou corrigée."),
    "predictions": ("PREDICTION", "Estimation émise par un modèle, conservée pour être comparée à la réalité."),
    "skills": ("COMPETENCE", "Compétence suivie dans le temps."),
    "skill_progress": ("EVALUATION", "Point d'évaluation d'une compétence : ressenti et preuve objective."),
    "decisions": ("DECISION", "Décision importante : contexte, raisons, choix, puis résultat observé."),
    "experiments": ("EXPERIENCE", "Expérience personnelle : hypothèse testée sur une période."),
    "people": ("PERSONNE", "Personne de l'entourage (famille, ami, mentor...)."),
    "interactions": ("ECHANGE", "Échange avec une personne : appel, visite, rencontre, message."),
}

# Description de chaque propriété (dictionnaire des données)

DESC = {
    "days": {
        "id": "Identifiant de la journée", "date": "Date calendaire, unique",
        "sleep_hours": "Durée de sommeil en heures (0 à 24)", "sleep_quality": "Qualité du sommeil (1 à 5)",
        "energy": "Niveau d'énergie déclaré (1 à 5)", "motivation": "Motivation déclarée (1 à 5)",
        "mood": "Humeur déclarée (1 à 5)", "stress": "Niveau de stress (1 à 5)", "fatigue": "Fatigue (1 à 5)",
        "screen_minutes": "Temps d'écran en minutes", "sedentary_minutes": "Temps sédentaire en minutes",
        "water_liters": "Eau bue en litres", "steps": "Nombre de pas",
        "professional_contribution": "Réponse à « Qu'ai je fait aujourd'hui pour mon évolution professionnelle ? »",
        "highlight": "Ce qui a marqué la journée", "general_comment": "Commentaire libre du soir",
        "morning_done_at": "Horodatage de la validation du matin", "evening_done_at": "Horodatage du bilan du soir",
        "created_at": "Date de création", "updated_at": "Date de dernière modification",
    },
    "goals": {
        "id": "Identifiant de l'objectif", "parent_id": "Objectif parent (décomposition)",
        "title": "Intitulé", "description": "Description détaillée", "dimension": "Dimension de vie",
        "horizon": "vision, long_terme, annuel, mensuel ou hebdomadaire", "status": "actif, atteint, en_pause, abandonne",
        "start_date": "Date de début", "target_date": "Échéance visée", "completed_at": "Date d'atteinte",
        "metric": "Indicateur de réussite (ex. nombre de projets)", "target_value": "Valeur cible de l'indicateur",
        "abandon_reason": "Raison d'un abandon", "created_at": "Date de création",
    },
    "intentions": {
        "id": "Identifiant de l'intention", "day_id": "Journée concernée", "goal_id": "Objectif auquel elle contribue",
        "dimension": "Dimension de vie", "category": "Type d'activité (Python, Sport...)",
        "description": "Intention formulée", "priority": "1 haute, 2 normale, 3 basse",
        "estimated_minutes": "Durée prévue en minutes", "status": "prevu, realise, partiel, non_realise, abandonne, reporte",
        "actual_minutes": "Durée réellement consacrée", "result": "Résultat obtenu",
        "reason": "Raison d'un abandon ou d'un écart", "position": "Ordre d'affichage dans la journée",
        "source_id": "Source d'origine (saisie du matin)", "created_at": "Date de création",
        "reviewed_at": "Date du bilan de cette intention",
    },
    "activities": {
        "id": "Identifiant de l'activité", "day_id": "Journée où elle a eu lieu",
        "intention_id": "Intention qu'elle concrétise (vide si non prévue)", "skill_id": "Compétence exercée",
        "dimension": "Dimension de vie", "category": "Type d'activité", "description": "Ce qui a été fait",
        "start_time": "Heure de début (HH:MM)", "end_time": "Heure de fin (HH:MM)",
        "duration_minutes": "Durée en minutes", "result": "Ce que l'activité a produit",
        "planned": "Vrai si l'activité était prévue", "source_id": "Source d'origine", "created_at": "Date de création",
    },
    "reflections": {
        "id": "Identifiant", "day_id": "Journée concernée", "dimension": "Dimension de vie",
        "kind": "reflexion, apprentissage, difficulte, gratitude, idee, evenement, passage, engagement...",
        "content": "Texte de la réflexion", "reference": "Référence (passage biblique, livre, lien)",
        "tags": "Mots clés libres", "source_type": "texte ou audio", "source_id": "Source d'origine",
        "created_at": "Date de création",
    },
    "media": {
        "id": "Identifiant du média", "day_id": "Journée de rattachement", "type": "audio, video, image, document",
        "moment": "matin, journee, soir", "dimension": "Dimension de vie",
        "file_path": "Chemin du fichier, relatif à storage/", "original_name": "Nom d'origine du fichier",
        "mime_type": "Type MIME", "size_bytes": "Taille en octets", "sha256": "Empreinte d'intégrité du fichier",
        "caption": "Légende", "transcription": "Texte transcrit (audio, vidéo)",
        "transcription_status": "en_attente, en_cours, termine, indisponible, erreur",
        "transcription_engine": "Moteur utilisé (ex. faster-whisper:small)",
        "transcription_error": "Message d'erreur éventuel", "created_at": "Date d'enregistrement",
    },
    "sources": {
        "id": "Identifiant de la source", "day_id": "Journée concernée",
        "kind": "texte, audio, video, formulaire", "moment": "matin, journee, soir",
        "raw_text": "Texte brut d'origine ou transcription", "media_id": "Média d'origine (si audio ou vidéo)",
        "created_at": "Date de création",
    },
    "extractions": {
        "id": "Identifiant", "source_id": "Source analysée", "engine": "Moteur d'extraction",
        "engine_version": "Version du moteur", "proposed": "Proposition de l'IA (JSON)",
        "validated": "Version validée par l'utilisateur (JSON)", "status": "propose, valide, corrige, rejete",
        "created_at": "Date de la proposition", "validated_at": "Date de validation",
    },
    "predictions": {
        "id": "Identifiant", "target": "Ce qui est prédit : completion, duree...",
        "subject_type": "Type d'objet concerné (ex. intention)", "subject_id": "Identifiant de l'objet concerné",
        "value": "Valeur prédite (probabilité, minutes...)", "lower": "Borne basse de l'intervalle",
        "upper": "Borne haute de l'intervalle", "model": "Modèle utilisé", "n_training": "Taille de l'historique d'apprentissage",
        "features": "Variables utilisées (JSON)", "actual": "Valeur réellement observée ensuite",
        "created_at": "Date de la prédiction",
    },
    "skills": {
        "id": "Identifiant", "name": "Nom de la compétence, unique", "category": "Famille (ex. Data science)",
        "dimension": "Dimension de vie", "description": "Description", "target_level": "Niveau visé (1 à 5)",
        "keywords": "Mots clés reliant automatiquement les activités", "created_at": "Date de création",
    },
    "skill_progress": {
        "id": "Identifiant", "skill_id": "Compétence évaluée", "date": "Date de l'évaluation",
        "self_rating": "Auto évaluation (0 à 5)", "objective_score": "Score objectif (0 à 100)",
        "evidence_type": "exercice, projet, test, formation, production", "evidence": "Description de la preuve",
        "comment": "Commentaire", "created_at": "Date de création",
    },
    "decisions": {
        "id": "Identifiant", "date": "Date de la décision", "title": "Décision", "dimension": "Dimension de vie",
        "context": "Contexte", "reasons": "Raisons", "alternatives": "Alternatives envisagées",
        "choice": "Choix effectué", "expected_outcome": "Résultat attendu", "confidence": "Confiance (1 à 5)",
        "review_date": "Date prévue pour juger le résultat", "outcome": "Résultat observé",
        "outcome_rating": "Appréciation du résultat (1 à 5)", "lessons": "Leçon tirée", "created_at": "Date de création",
    },
    "experiments": {
        "id": "Identifiant", "title": "Titre", "hypothesis": "Hypothèse testée", "intervention": "Ce qui est changé",
        "metric": "Indicateur observé (colonne de la série quotidienne)", "start_date": "Début",
        "end_date": "Fin (vide si en cours)", "status": "en_cours, termine", "conclusion": "Conclusion",
        "created_at": "Date de création",
    },
    "people": {
        "id": "Identifiant", "name": "Nom", "relation": "famille, ami, collègue, mentor, communauté",
        "notes": "Notes", "contact_every_days": "Rythme de contact souhaité en jours", "created_at": "Date de création",
    },
    "interactions": {
        "id": "Identifiant", "person_id": "Personne concernée", "date": "Date de l'échange",
        "kind": "appel, visite, message, rencontre, conversation", "note": "Note sur l'échange", "created_at": "Date de création",
    },
}


@dataclass
class Asso:
    name: str
    a: str          # table côté A
    card_a: str
    b: str          # table côté B
    card_b: str
    fk: str         # clé étrangère produite dans le MLD (table.colonne)
    meaning: str    # phrase de lecture
    pos: tuple[int, int]
    role_a: str = ""
    role_b: str = ""


ASSOS = [
    Asso("DECOMPOSER", "goals", "0,n", "goals", "0,1", "goals.parent_id",
         "Un objectif peut se décomposer en plusieurs sous objectifs ; un objectif a au plus un objectif parent.",
         (185, 470), "parent", "enfant"),
    Asso("CONTRIBUER", "goals", "0,n", "intentions", "0,1", "intentions.goal_id",
         "Un objectif reçoit la contribution de zéro ou plusieurs intentions ; une intention contribue à au plus un objectif.",
         (945, 150)),
    Asso("PREVOIR", "days", "0,n", "intentions", "1,1", "intentions.day_id",
         "Une journée comporte zéro ou plusieurs intentions ; une intention est prévue pour exactement une journée.",
         (1080, 330)),
    Asso("CONCERNER", "intentions", "0,n", "predictions", "0,1", "predictions.subject_id",
         "Une intention peut faire l'objet de plusieurs prédictions ; une prédiction concerne au plus une intention.",
         (1715, 150)),
    Asso("EXPRIMER", "sources", "0,n", "intentions", "0,1", "intentions.source_id",
         "Une source peut exprimer plusieurs intentions ; une intention provient d'au plus une source.",
         (1715, 420)),
    Asso("REALISER", "days", "0,n", "activities", "1,1", "activities.day_id",
         "Une journée comporte zéro ou plusieurs activités ; une activité a lieu exactement un jour.",
         (1080, 610)),
    Asso("CONCRETISER", "intentions", "0,n", "activities", "0,1", "activities.intention_id",
         "Une intention peut être concrétisée par plusieurs activités ; une activité concrétise au plus une intention.",
         (1395, 452)),
    Asso("RELATER", "sources", "0,n", "activities", "0,1", "activities.source_id",
         "Une source peut relater plusieurs activités ; une activité provient d'au plus une source.",
         (1715, 690)),
    Asso("SAISIR", "days", "0,n", "sources", "0,1", "sources.day_id",
         "Une journée regroupe zéro ou plusieurs sources ; une source est rattachée à au plus une journée.",
         (1715, 842)),
    Asso("NOTER", "days", "0,n", "reflections", "1,1", "reflections.day_id",
         "Une journée comporte zéro ou plusieurs réflexions ; une réflexion appartient exactement à une journée.",
         (1080, 960)),
    Asso("CONSIGNER", "sources", "0,n", "reflections", "0,1", "reflections.source_id",
         "Une source peut consigner plusieurs réflexions ; une réflexion provient d'au plus une source.",
         (1715, 990)),
    Asso("ATTACHER", "days", "0,n", "media", "0,1", "media.day_id",
         "Une journée peut avoir plusieurs médias ; un média est rattaché à au plus une journée.",
         (1080, 1230)),
    Asso("TRANSCRIRE", "media", "0,n", "sources", "0,1", "sources.media_id",
         "Un média peut donner lieu à des sources (sa transcription) ; une source provient d'au plus un média.",
         (1715, 1290)),
    Asso("ANALYSER", "sources", "0,n", "extractions", "1,1", "extractions.source_id",
         "Une source peut être analysée plusieurs fois ; une extraction porte sur exactement une source.",
         (2325, 717)),
    Asso("EXERCER", "skills", "0,n", "activities", "0,1", "activities.skill_id",
         "Une compétence est exercée par zéro ou plusieurs activités ; une activité exerce au plus une compétence.",
         (1080, 1075)),
    Asso("EVALUER", "skills", "0,n", "skill_progress", "1,1", "skill_progress.skill_id",
         "Une compétence reçoit zéro ou plusieurs évaluations ; une évaluation concerne exactement une compétence.",
         (475, 1260)),
    Asso("ECHANGER", "people", "0,n", "interactions", "1,1", "interactions.person_id",
         "Une personne a zéro ou plusieurs échanges ; un échange concerne exactement une personne.",
         (475, 1830)),
]

# Position des entités sur le schéma (x, y du coin haut gauche)
POS = {
    "goals": (40, 40), "days": (620, 420), "skills": (620, 1150), "skill_progress": (40, 1150),
    "intentions": (1250, 40), "activities": (1250, 520), "reflections": (1250, 900), "media": (1250, 1230),
    "predictions": (1880, 40), "sources": (1880, 640), "extractions": (2480, 640),
    "people": (40, 1720), "interactions": (620, 1720), "decisions": (1250, 1720), "experiments": (1880, 1720),
}
BOX_W, HEAD_H, LINE_H, FONT = 290, 36, 22, 15
# Points d'accroche imposés pour éviter qu'un lien traverse une entité
ANCHORS = {("SAISIR", "days"): (910, 842), ("EXERCER", "activities"): (1310, 784)}
ELL_W, ELL_H = 170, 58


# Lecture du schéma SQLAlchemy

def columns(table: str) -> list:
    return list(Base.metadata.tables[table].columns)


def fk_columns(table: str) -> set[str]:
    cols = {c.name for c in columns(table) if c.foreign_keys}
    if table == "predictions":
        cols.add("subject_id")  # référence polymorphe (subject_type, subject_id)
    return cols


def conceptual_props(table: str) -> list[str]:
    """Propriétés du MCD : sans les clés étrangères, qui n'existent qu'au niveau logique."""
    return [c.name for c in columns(table) if c.name not in fk_columns(table)]


def type_label(col) -> str:
    t = col.type
    if isinstance(t, Boolean):
        return "Booléen"
    if isinstance(t, Integer):
        return "Entier"
    if isinstance(t, Float):
        return "Réel"
    if isinstance(t, DateTime):
        return "Date et heure"
    if isinstance(t, Date):
        return "Date"
    if isinstance(t, Text):
        return "Texte long"
    if isinstance(t, String):
        return f"Texte ({t.length})" if t.length else "Texte"
    if isinstance(t, JSON):
        return "JSON"
    return type(t).__name__


def constraints(table: str, col) -> str:
    out = []
    if col.primary_key:
        out.append("Clé primaire")
    for fk in col.foreign_keys:
        out.append(f"Clé étrangère vers {fk.column.table.name}")
    if table == "predictions" and col.name == "subject_id":
        out.append("Référence polymorphe")
    if col.unique:
        out.append("Unique")
    if not col.nullable and not col.primary_key:
        out.append("Obligatoire")
    if col.default is not None and not callable(getattr(col.default, "arg", None)):
        out.append(f"Défaut : {col.default.arg}")
    elif col.default is not None:
        out.append("Défaut : maintenant")
    return ", ".join(out) or "Facultatif"


# Dessin du schéma : primitives communes à SVG et reportlab

def box_height(table: str) -> int:
    return HEAD_H + LINE_H * len(conceptual_props(table)) + 12


def box_rect(table: str) -> tuple[int, int, int, int]:
    x, y = POS[table]
    return x, y, BOX_W, box_height(table)


def border_point(rect, target) -> tuple[float, float]:
    """Point du bord du rectangle sur la droite qui joint son centre à la cible."""
    x, y, w, h = rect
    cx, cy = x + w / 2, y + h / 2
    dx, dy = target[0] - cx, target[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2) / abs(dx) if dx else math.inf
    sy = (h / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def ellipse_point(center, target) -> tuple[float, float]:
    cx, cy = center
    dx, dy = target[0] - cx, target[1] - cy
    a, b = ELL_W / 2, ELL_H / 2
    k = 1 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2) if (dx or dy) else 0
    return cx + dx * k, cy + dy * k


def primitives() -> tuple[list[tuple], int, int]:
    prims: list[tuple] = []
    # Liens et cardinalités
    for asso in ASSOS:
        for side, (table, card, role) in enumerate(((asso.a, asso.card_a, asso.role_a), (asso.b, asso.card_b, asso.role_b))):
            rect = box_rect(table)
            if asso.a == asso.b:  # association réflexive : deux pattes distinctes
                x, y, w, h = rect
                start = (x + (70 if side == 0 else w - 70), y + h)
            elif (asso.name, table) in ANCHORS:
                start = ANCHORS[(asso.name, table)]
            else:
                start = border_point(rect, asso.pos)
            end = ellipse_point(asso.pos, start)
            prims.append(("line", start, end))
            t = 0.28
            lx, ly = start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t
            label = f"{card} {role}".strip()
            prims.append(("card", (lx, ly), label))
    # Entités
    for table, (name, _role) in ENTITIES.items():
        x, y, w, h = box_rect(table)
        prims.append(("entity", (x, y, w, h), name, table, conceptual_props(table)))
    # Associations
    for asso in ASSOS:
        prims.append(("asso", asso.pos, asso.name))
    width = max(x + BOX_W for x, _ in POS.values()) + 40
    height = max(POS[t][1] + box_height(t) for t in POS) + 40
    return prims, width, height


def to_svg() -> str:
    prims, W, H = primitives()
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Helvetica, Arial, sans-serif">', f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>']
    # bande du drapeau
    out.append(f'<rect x="0" y="0" width="{W * 0.3}" height="10" fill="{RED}"/>')
    for i, c in enumerate([YELLOW, GREEN, YELLOW, GREEN, YELLOW]):
        out.append(f'<rect x="{W * 0.3 + i * W * 0.14}" y="0" width="{W * 0.14}" height="10" fill="{c}"/>')
    for p in prims:
        if p[0] == "line":
            (x1, y1), (x2, y2) = p[1], p[2]
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{MUTED}" stroke-width="1.6"/>')
    for p in prims:
        if p[0] == "entity":
            x, y, w, h = p[1]
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#FFFFFF" stroke="{GREEN}" stroke-width="2.2"/>')
            out.append(f'<path d="M{x} {y + HEAD_H} V{y + 8} Q{x} {y} {x + 8} {y} H{x + w - 8} Q{x + w} {y} {x + w} {y + 8} '
                       f'V{y + HEAD_H} Z" fill="{GREEN}"/>')
            out.append(f'<text x="{x + w / 2}" y="{y + 24}" text-anchor="middle" font-size="17" font-weight="bold" '
                       f'fill="#FFFFFF">{p[2]}</text>')
            for i, prop in enumerate(p[4]):
                ty = y + HEAD_H + 18 + i * LINE_H
                deco = ' text-decoration="underline" font-weight="bold"' if i == 0 else ""
                out.append(f'<text x="{x + 12}" y="{ty}" font-size="{FONT}" fill="{INK}"{deco}>{prop}</text>')
        elif p[0] == "asso":
            cx, cy = p[1]
            out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{ELL_W / 2}" ry="{ELL_H / 2}" fill="{ASSO_FILL}" '
                       f'stroke="{ASSO_LINE}" stroke-width="2"/>')
            out.append(f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="14" font-weight="bold" fill="{INK}">{p[2]}</text>')
        elif p[0] == "card":
            (lx, ly), label = p[1], p[2]
            tw = 9 * len(label) + 8
            out.append(f'<rect x="{lx - tw / 2:.1f}" y="{ly - 11:.1f}" width="{tw}" height="20" rx="4" fill="#FFFFFF" '
                       f'stroke="{RED}" stroke-width="1"/>')
            out.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" font-size="13" font-weight="bold" '
                       f'fill="{RED}">{label}</text>')
    # légende
    lx, ly = 2480, 1720
    out.append(f'<text x="{lx}" y="{ly + 10}" font-size="16" font-weight="bold" fill="{GREEN}">Légende</text>')
    legend = [("Entité (identifiant souligné)", "entity"), ("Association", "asso"), ("Cardinalité min,max", "card")]
    for i, (txt, kind) in enumerate(legend):
        y = ly + 40 + i * 42
        if kind == "entity":
            out.append(f'<rect x="{lx}" y="{y - 14}" width="44" height="26" rx="4" fill="#FFFFFF" stroke="{GREEN}" stroke-width="2"/>'
                       f'<rect x="{lx}" y="{y - 14}" width="44" height="9" fill="{GREEN}"/>')
        elif kind == "asso":
            out.append(f'<ellipse cx="{lx + 22}" cy="{y}" rx="22" ry="13" fill="{ASSO_FILL}" stroke="{ASSO_LINE}" stroke-width="2"/>')
        else:
            out.append(f'<rect x="{lx}" y="{y - 11}" width="44" height="20" rx="4" fill="#FFFFFF" stroke="{RED}"/>'
                       f'<text x="{lx + 22}" y="{y + 4}" text-anchor="middle" font-size="12" font-weight="bold" fill="{RED}">0,n</text>')
        out.append(f'<text x="{lx + 56}" y="{y + 5}" font-size="14" fill="{INK}">{txt}</text>')
    out.append(f'<text x="{lx}" y="{ly + 180}" font-size="13" fill="{MUTED}">Modèle Conceptuel de Données, méthode Merise</text>')
    out.append(f'<text x="{lx}" y="{ly + 200}" font-size="13" fill="{MUTED}">Personal Evolution Intelligence, {date.today():%d/%m/%Y}</text>')
    out.append("</svg>")
    return "\n".join(out)


def draw_on_canvas(c, ox: float, oy: float, scale: float) -> None:
    """Dessine le MCD en vectoriel sur un canevas reportlab (origine en bas à gauche)."""
    from reportlab.lib import colors

    prims, W, H = primitives()

    def X(v):
        return ox + v * scale

    def Y(v):
        return oy + (H - v) * scale

    hx = colors.HexColor
    c.setLineWidth(1.6 * scale)
    c.setStrokeColor(hx(MUTED))
    for p in prims:
        if p[0] == "line":
            (x1, y1), (x2, y2) = p[1], p[2]
            c.line(X(x1), Y(y1), X(x2), Y(y2))
    for p in prims:
        if p[0] == "entity":
            x, y, w, h = p[1]
            c.setStrokeColor(hx(GREEN))
            c.setLineWidth(2.2 * scale)
            c.setFillColor(colors.white)
            c.roundRect(X(x), Y(y + h), w * scale, h * scale, 8 * scale, stroke=1, fill=1)
            c.setFillColor(hx(GREEN))
            c.roundRect(X(x), Y(y + HEAD_H), w * scale, HEAD_H * scale, 8 * scale, stroke=0, fill=1)
            c.rect(X(x), Y(y + HEAD_H), w * scale, 10 * scale, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 17 * scale)
            c.drawCentredString(X(x + w / 2), Y(y + 24), p[2])
            for i, prop in enumerate(p[4]):
                ty = y + HEAD_H + 18 + i * LINE_H
                c.setFillColor(hx(INK))
                c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", FONT * scale)
                c.drawString(X(x + 12), Y(ty), prop)
                if i == 0:
                    tw = c.stringWidth(prop, "Helvetica-Bold", FONT * scale)
                    c.setLineWidth(0.8 * scale)
                    c.setStrokeColor(hx(INK))
                    c.line(X(x + 12), Y(ty + 3), X(x + 12) + tw, Y(ty + 3))
        elif p[0] == "asso":
            cx, cy = p[1]
            c.setStrokeColor(hx(ASSO_LINE))
            c.setFillColor(hx(ASSO_FILL))
            c.setLineWidth(2 * scale)
            c.ellipse(X(cx - ELL_W / 2), Y(cy + ELL_H / 2), X(cx + ELL_W / 2), Y(cy - ELL_H / 2), stroke=1, fill=1)
            c.setFillColor(hx(INK))
            c.setFont("Helvetica-Bold", 14 * scale)
            c.drawCentredString(X(cx), Y(cy + 5), p[2])
        elif p[0] == "card":
            (lx, ly), label = p[1], p[2]
            tw = 9 * len(label) + 8
            c.setStrokeColor(hx(RED))
            c.setFillColor(colors.white)
            c.setLineWidth(1 * scale)
            c.roundRect(X(lx - tw / 2), Y(ly + 9), tw * scale, 20 * scale, 4 * scale, stroke=1, fill=1)
            c.setFillColor(hx(RED))
            c.setFont("Helvetica-Bold", 13 * scale)
            c.drawCentredString(X(lx), Y(ly + 4), label)
    lx, ly = 2480, 1720
    c.setFillColor(hx(GREEN))
    c.setFont("Helvetica-Bold", 16 * scale)
    c.drawString(X(lx), Y(ly + 10), "Légende")
    c.setFont("Helvetica", 14 * scale)
    c.setFillColor(hx(INK))
    for i, txt in enumerate(["Rectangle vert : entité (identifiant souligné)", "Ellipse jaune : association",
                             "Étiquette rouge : cardinalité min,max"]):
        c.drawString(X(lx), Y(ly + 45 + i * 30), txt)


# Contenu explicatif

def build_sections() -> list[tuple]:
    S: list[tuple] = []
    S.append(("h1", "1. Qu'est ce que le MCD ?"))
    S.append(("p", "Le Modèle Conceptuel de Données (méthode Merise) décrit les informations manipulées par PEI "
                   "indépendamment de toute technique : des <b>entités</b> (objets du réel ayant une existence propre), "
                   "reliées par des <b>associations</b> (verbes qui expriment un lien de sens), chacune affectée de "
                   "<b>cardinalités</b> qui disent combien de fois une occurrence d'entité participe à l'association."))
    S.append(("ul", [
        "Une <b>entité</b> est représentée par un rectangle vert. Sa première propriété, soulignée, est son identifiant.",
        "Une <b>association</b> est représentée par une ellipse jaune portant un verbe à l'infinitif.",
        "Une <b>cardinalité</b> « min,max » est écrite en rouge sur chaque patte : le minimum (0 ou 1) dit si la "
        "participation est facultative ou obligatoire, le maximum (1 ou n) dit si elle est unique ou multiple.",
        "Au niveau conceptuel il n'y a pas de clé étrangère : elles n'apparaissent qu'au passage au modèle logique (MLD).",
    ]))
    S.append(("p", "Le MCD de PEI compte <b>15 entités</b> et <b>17 associations</b>. Il est organisé autour de deux "
                   "pivots : <b>JOUR</b>, qui donne la dimension longitudinale (tout se rattache à une date), et "
                   "<b>SOURCE</b>, qui garantit la traçabilité (toute donnée structurée remonte à sa donnée brute)."))

    S.append(("h1", "2. Le schéma"))
    S.append(("diagram",))
    S.append(("p", "Le schéma est fourni en vectoriel (docs/mcd.svg et page précédente du PDF) : il peut être zoomé sans perte."))

    S.append(("h1", "3. Les entités"))
    S.append(("table", ["Entité", "Table", "Rôle", "Propriétés"],
              [[ENTITIES[t][0], t, ENTITIES[t][1], str(len(conceptual_props(t)))] for t in ENTITIES],
              [0.17, 0.17, 0.54, 0.12]))
    S.append(("p", "Trois groupes se dégagent :"))
    S.append(("ul", [
        "<b>Le cœur quotidien</b> : JOUR, INTENTION, ACTIVITE, REFLEXION, MEDIA. Il traduit la chaîne "
        "Intention, Action, Résultat (le résultat est une propriété de l'activité et de l'intention).",
        "<b>La traçabilité et l'intelligence</b> : SOURCE, EXTRACTION, PREDICTION. Elles conservent la donnée "
        "brute, ce que l'IA en a tiré, ce que l'utilisateur a validé, et ce que les modèles ont prédit.",
        "<b>Les dimensions longues</b> : OBJECTIF, COMPETENCE, EVALUATION, DECISION, EXPERIENCE, PERSONNE, ECHANGE.",
    ]))

    S.append(("h1", "4. Les associations et leurs cardinalités"))
    S.append(("p", "Chaque ligne se lit dans les deux sens. Exemple pour PREVOIR : « une JOUR(née) prévoit 0 à n "
                   "intentions » et « une INTENTION est prévue pour 1 et 1 seul jour »."))
    rows = []
    for a in ASSOS:
        ea, eb = ENTITIES[a.a][0], ENTITIES[a.b][0]
        if a.role_a:
            ea, eb = f"{ea} ({a.role_a})", f"{eb} ({a.role_b})"
        rows.append([a.name, ea, a.card_a, eb, a.card_b, a.meaning])
    S.append(("table", ["Association", "Entité A", "Card. A", "Entité B", "Card. B", "Lecture"], rows,
              [0.14, 0.14, 0.07, 0.15, 0.07, 0.43]))

    S.append(("h1", "5. Justification des cardinalités"))
    S.append(("ul", [
        "<b>Minimum 1 côté INTENTION, ACTIVITE, REFLEXION (PREVOIR, REALISER, NOTER)</b> : ces éléments n'ont pas de "
        "sens hors d'une journée. Supprimer une journée supprime donc ses intentions, activités et réflexions (cascade).",
        "<b>Minimum 0 côté JOUR</b> : une journée peut exister sans intention, par exemple si seul le sommeil a été saisi.",
        "<b>CONCRETISER (0,n) / (0,1)</b> : une activité peut être imprévue (aucune intention), et une intention "
        "peut être réalisée en plusieurs séances ; c'est ce lien qui permet de comparer le prévu et le réalisé.",
        "<b>CONTRIBUER (0,n) / (0,1)</b> : une intention n'est pas obligatoirement reliée à un objectif ; quand elle "
        "l'est, le temps consacré remonte, par DECOMPOSER, jusqu'à la vision.",
        "<b>DECOMPOSER, association réflexive</b> : un objectif a au plus un parent (0,1) et peut avoir plusieurs "
        "sous objectifs (0,n). La vision est un objectif sans parent.",
        "<b>EXPRIMER, RELATER, CONSIGNER (0,n) / (0,1)</b> : une même saisie (par exemple le bilan dicté du soir) peut "
        "produire plusieurs éléments structurés ; un élément saisi directement au formulaire peut ne pas avoir de source.",
        "<b>ANALYSER (0,n) / (1,1)</b> : une extraction n'existe que par sa source ; une source peut être analysée "
        "plusieurs fois (nouvelle version du moteur), sans jamais être modifiée.",
        "<b>TRANSCRIRE (0,n) / (0,1)</b> : un média audio ou vidéo donne naissance à une source qui contient sa "
        "transcription ; une image ou un document n'en produit pas. Le fichier d'origine n'est jamais altéré.",
        "<b>ATTACHER et SAISIR (0,n) / (0,1)</b> : un média ou une source est normalement daté, mais peut exister "
        "sans journée (import ultérieur) ; si la journée est supprimée, le lien est mis à vide sans perdre l'original.",
        "<b>EXERCER (0,n) / (0,1)</b> : le rattachement d'une activité à une compétence est automatique (mots clés) "
        "et facultatif.",
        "<b>EVALUER et ECHANGER (0,n) / (1,1)</b> : une évaluation n'existe que pour une compétence, un échange que "
        "pour une personne.",
        "<b>CONCERNER (0,n) / (0,1)</b> : une prédiction porte en général sur une intention. Dans l'implémentation "
        "le lien est <i>polymorphe</i> (subject_type, subject_id) afin de pouvoir, plus tard, prédire sur d'autres "
        "objets (compétence, objectif) sans changer le schéma.",
    ]))

    S.append(("h1", "6. Entités indépendantes et choix de modélisation"))
    S.append(("ul", [
        "<b>DECISION</b> et <b>EXPERIENCE</b> ne sont reliées à aucune entité : elles se rattachent au temps par "
        "leurs propres dates. L'expérience compare un indicateur (propriété metric) calculé sur les journées de "
        "sa période et de la période précédente : c'est un lien de calcul, pas une association stockée.",
        "La <b>dimension</b> de vie (spirituel, physique, études...) et les <b>statuts</b> sont des propriétés à "
        "domaine de valeurs fermé, définies dans backend/domain.py, plutôt que des entités : la liste est stable, "
        "et cela évite des jointures dans toutes les analyses. Si l'utilisateur doit un jour créer ses propres "
        "dimensions, on ajoutera une entité DIMENSION reliée par une association (0,n) / (0,1).",
        "Le <b>Résultat</b> de la chaîne Intention, Action, Résultat est une propriété (result) de l'activité et "
        "de l'intention, car il est toujours unique et décrit en texte libre.",
        "La table technique <b>memory_index</b> (index plein texte FTS5) n'apparaît pas dans le MCD : c'est une "
        "structure d'accès dérivée, reconstruisible à tout moment (python run.py reindex).",
    ]))

    S.append(("h1", "7. Passage au Modèle Logique de Données (MLD)"))
    S.append(("p", "Règles appliquées : chaque entité devient une table, son identifiant devient la clé primaire. "
                   "Pour une association de type (x,n) / (x,1), la clé primaire du côté n migre comme clé étrangère "
                   "dans la table du côté 1. Si le minimum est 0, la clé étrangère peut être vide ; s'il vaut 1, elle "
                   "est obligatoire. Aucune association n'est de type (n,n), il n'y a donc pas de table de liaison."))
    mld = []
    for t in ENTITIES:
        cols = []
        for col in columns(t):
            name = col.name
            if col.primary_key:
                name = f"<u>{name}</u>"
            if col.name in fk_columns(t):
                name = f"#{name}"
            cols.append(name)
        mld.append(f"<b>{t}</b> ({', '.join(cols)})")
    S.append(("mld", mld))
    S.append(("p", "Notation : identifiant souligné, clé étrangère précédée de #."))
    fk_rows = [[a.name, a.fk, f"{a.b if a.fk.split('.')[0] == a.b else a.a}",
                "Obligatoire" if "1,1" in (a.card_a, a.card_b) else "Facultative"] for a in ASSOS]
    for r, a in zip(fk_rows, ASSOS):
        ref = a.a if a.fk.split(".")[0] == a.b else a.b
        r[2] = ref
    S.append(("table", ["Association", "Clé étrangère créée", "Référence", "Nature"], fk_rows, [0.2, 0.35, 0.25, 0.2]))
    S.append(("p", "Comportement à la suppression : les clés obligatoires vers JOUR, SOURCE, COMPETENCE et PERSONNE sont "
                   "en suppression en cascade ; les clés facultatives sont mises à vide (SET NULL), afin de ne jamais "
                   "perdre une donnée d'origine."))

    S.append(("h1", "8. Dictionnaire des données : propriétés de chaque table"))
    S.append(("p", "Pour chaque table : nom de la propriété, type, contraintes et signification. Les échelles 1 à 5 "
                   "vont du plus faible au plus fort."))
    for t, (name, role) in ENTITIES.items():
        S.append(("h2", f"{name} (table {t})"))
        S.append(("p", role))
        rows = [[col.name, type_label(col), constraints(t, col), DESC.get(t, {}).get(col.name, "")] for col in columns(t)]
        S.append(("table", ["Propriété", "Type", "Contraintes", "Description"], rows, [0.22, 0.14, 0.24, 0.40]))
    return S


# Rendus

def to_markdown(sections) -> str:
    out = ["# Modèle Conceptuel de Données de PEI", "", f"*Personal Evolution Intelligence, {date.today():%d/%m/%Y}*", ""]

    def md(t: str) -> str:
        return (t.replace("<b>", "**").replace("</b>", "**").replace("<i>", "*").replace("</i>", "*")
                .replace("<u>", "__").replace("</u>", "__"))
    for s in sections:
        k = s[0]
        if k == "h1":
            out += [f"## {s[1]}", ""]
        elif k == "h2":
            out += [f"### {s[1]}", ""]
        elif k == "p":
            out += [md(s[1]), ""]
        elif k == "ul":
            out += [f"* {md(i)}" for i in s[1]] + [""]
        elif k == "diagram":
            out += ["![MCD de PEI](mcd.png)", "", "Version vectorielle : [mcd.svg](mcd.svg)", ""]
        elif k == "table":
            out += ["| " + " | ".join(s[1]) + " |", "|" + "---|" * len(s[1])]
            out += ["| " + " | ".join(md(str(c)).replace("|", "/") for c in r) + " |" for r in s[2]] + [""]
        elif k == "mld":
            out += [f"* {md(line)}" for line in s[1]] + [""]
    return "\n".join(out)


def to_pdf(sections, path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A3, A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, ListFlowable, ListItem, NextPageTemplate,
                                    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

    green, yellow, red = colors.HexColor(GREEN), colors.HexColor(YELLOW), colors.HexColor(RED)
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["BodyText"], fontName="Helvetica", fontSize=10, leading=14.5, spaceAfter=6)
    s_h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=green, spaceBefore=12, spaceAfter=8)
    s_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=green, spaceBefore=10, spaceAfter=3)
    cell = ParagraphStyle("c", parent=body, fontSize=8.3, leading=10.8, spaceAfter=0)
    cell_h = ParagraphStyle("ch", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    mld_style = ParagraphStyle("mld", parent=body, fontName="Courier", fontSize=8.2, leading=11, leftIndent=8)

    portrait, a3 = A4, landscape(A3)
    pw = portrait[0] - 4 * cm

    class Diagram(Flowable):
        def wrap(self, aw, ah):
            self.aw, self.ah = aw, ah
            return aw, ah

        def draw(self):
            _, W, H = primitives()
            scale = min(self.aw / W, self.ah / H)
            ox = (self.aw - W * scale) / 2
            oy = (self.ah - H * scale) / 2
            draw_on_canvas(self.canv, ox, oy, scale)

    def band(canvas, doc):
        canvas.saveState()
        w, h = canvas._pagesize
        canvas.setFillColor(red)
        canvas.rect(0, h - 8, w * 0.3, 8, stroke=0, fill=1)
        for i, col in enumerate([yellow, green, yellow, green, yellow]):
            canvas.setFillColor(col)
            canvas.rect(w * 0.3 + i * w * 0.14, h - 8, w * 0.14, 8, stroke=0, fill=1)
        if doc.page > 1:
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor(MUTED))
            canvas.drawString(2 * cm, 1.2 * cm, "PEI, Modèle Conceptuel de Données")
            canvas.drawRightString(w - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(path), pagesize=portrait, title="PEI : Modèle Conceptuel de Données", author="PEI")
    doc.addPageTemplates([
        PageTemplate("portrait", [Frame(2 * cm, 2 * cm, pw, portrait[1] - 4 * cm, id="p")], onPage=band, pagesize=portrait),
        PageTemplate("a3", [Frame(1.2 * cm, 1.6 * cm, a3[0] - 2.4 * cm, a3[1] - 3 * cm, id="d")], onPage=band, pagesize=a3),
    ])

    story = [Spacer(1, 6 * cm),
             Paragraph("Modèle Conceptuel de Données", ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=26, leading=32,
                                                                      textColor=green, alignment=TA_CENTER)),
             Paragraph("Personal Evolution Intelligence", ParagraphStyle("st", fontName="Helvetica", fontSize=16, leading=22,
                                                                         alignment=TA_CENTER)),
             Spacer(1, 1 * cm),
             Paragraph("Méthode Merise : entités, associations, cardinalités, dictionnaire des données et MLD",
                       ParagraphStyle("s3", parent=body, alignment=TA_CENTER, fontSize=11)),
             Spacer(1, 6 * cm),
             Paragraph(f"15 entités, 17 associations, {sum(len(columns(t)) for t in ENTITIES)} propriétés<br/>"
                       f"Version du {date.today():%d/%m/%Y}",
                       ParagraphStyle("s4", parent=body, alignment=TA_CENTER, textColor=colors.HexColor(MUTED))),
             PageBreak()]

    def tbl(header, rows, widths):
        data = [[Paragraph(h, cell_h) for h in header]] + [[Paragraph(str(c), cell) for c in r] for r in rows]
        t = Table(data, colWidths=[w * pw for w in widths], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), green), ("LINEBELOW", (0, 0), (-1, 0), 2, yellow),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F2")]),
            ("GRID", (0, 1), (-1, -1), 0.3, colors.HexColor("#DFE6E0")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    for s in sections:
        k = s[0]
        if k == "h1":
            story.append(Paragraph(s[1], s_h1))
        elif k == "h2":
            story.append(Paragraph(s[1], s_h2))
        elif k == "p":
            story.append(Paragraph(s[1], body))
        elif k == "ul":
            story.append(ListFlowable([ListItem(Paragraph(i, body), leftIndent=12) for i in s[1]], bulletType="bullet",
                                      bulletColor=green, bulletFontSize=8, leftIndent=16))
        elif k == "diagram":
            story += [NextPageTemplate("a3"), PageBreak(), Diagram(), NextPageTemplate("portrait"), PageBreak()]
        elif k == "table":
            story += [tbl(s[1], s[2], s[3]), Spacer(1, 8)]
        elif k == "mld":
            story += [Paragraph(line, mld_style) for line in s[1]]
    doc.build(story)


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "mcd.svg").write_text(to_svg(), encoding="utf-8")
    sections = build_sections()
    (DOCS / "MCD.md").write_text(to_markdown(sections), encoding="utf-8")
    print("docs/mcd.svg et docs/MCD.md écrits")
    try:
        to_pdf(sections, DOCS / "MCD.pdf")
        print("docs/MCD.pdf écrit")
    except ImportError:
        print("reportlab absent : PDF non généré (pip install reportlab)")


if __name__ == "__main__":
    main()
