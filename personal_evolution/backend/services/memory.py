"""Mémoire personnelle interrogeable.

Un index plein texte SQLite FTS5 est maintenu automatiquement à chaque écriture
(événement after_flush). Chaque résultat renvoie à sa source d'origine.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .. import models as m
from ..domain import REFLECTION_KINDS, dimension_label

FTS_TABLE = "memory_index"


def ensure_index(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5("
                "kind UNINDEXED, ref_id UNINDEXED, day UNINDEXED, dimension UNINDEXED, "
                "title, content, tokenize='unicode61 remove_diacritics 2')"
            )
        )


def _day_date(conn, day_id: int | None) -> str | None:
    if not day_id:
        return None
    row = conn.execute(text("SELECT date FROM days WHERE id=:i"), {"i": day_id}).fetchone()
    return str(row[0]) if row else None


def _join(*parts) -> str:
    return "\n".join(str(p) for p in parts if p)


def _document(conn, obj) -> tuple[str, int, str | None, str | None, str, str] | None:
    """Transforme un objet en document indexable (kind, id, date, dimension, titre, contenu)."""
    if isinstance(obj, m.Intention):
        return ("intention", obj.id, _day_date(conn, obj.day_id), obj.dimension, obj.description,
                _join(obj.category, obj.result, obj.reason))
    if isinstance(obj, m.Activity):
        return ("activite", obj.id, _day_date(conn, obj.day_id), obj.dimension, obj.description,
                _join(obj.category, obj.result))
    if isinstance(obj, m.Reflection):
        return ("reflexion", obj.id, _day_date(conn, obj.day_id), obj.dimension,
                REFLECTION_KINDS.get(obj.kind, obj.kind), _join(obj.content, obj.reference, obj.tags))
    if isinstance(obj, m.Media):
        if not (obj.caption or obj.transcription):
            return None
        return ("media", obj.id, _day_date(conn, obj.day_id), obj.dimension,
                obj.caption or obj.original_name or obj.type, _join(obj.transcription))
    if isinstance(obj, m.Decision):
        return ("decision", obj.id, str(obj.date) if obj.date else None, obj.dimension, obj.title,
                _join(obj.context, obj.reasons, obj.alternatives, obj.choice, obj.outcome, obj.lessons))
    if isinstance(obj, m.Goal):
        return ("objectif", obj.id, str(obj.start_date) if obj.start_date else None, obj.dimension, obj.title,
                _join(obj.description, obj.metric, obj.abandon_reason))
    if isinstance(obj, m.Source):
        if not obj.raw_text:
            return None
        return ("source", obj.id, _day_date(conn, obj.day_id), None, f"Saisie {obj.moment or ''}".strip(), obj.raw_text)
    if isinstance(obj, m.Day):
        body = _join(obj.highlight, obj.general_comment, obj.professional_contribution)
        if not body:
            return None
        return ("journee", obj.id, str(obj.date), None, "Bilan de la journée", body)
    if isinstance(obj, m.Experiment):
        return ("experience", obj.id, str(obj.start_date), None, obj.title,
                _join(obj.hypothesis, obj.intervention, obj.conclusion))
    if isinstance(obj, m.Interaction):
        return ("interaction", obj.id, str(obj.date), "relationnel", obj.kind, _join(obj.note))
    if isinstance(obj, m.SkillProgress):
        return ("competence", obj.id, str(obj.date), None, "Progression de compétence",
                _join(obj.evidence, obj.comment))
    return None


_INDEXED = (m.Intention, m.Activity, m.Reflection, m.Media, m.Decision, m.Goal, m.Source, m.Day,
            m.Experiment, m.Interaction, m.SkillProgress)


def _kind_of(obj) -> str | None:
    names = {m.Intention: "intention", m.Activity: "activite", m.Reflection: "reflexion", m.Media: "media",
             m.Decision: "decision", m.Goal: "objectif", m.Source: "source", m.Day: "journee",
             m.Experiment: "experience", m.Interaction: "interaction", m.SkillProgress: "competence"}
    return names.get(type(obj))


@event.listens_for(Session, "after_flush")
def _sync_index(session: Session, _ctx) -> None:
    touched = [o for o in list(session.new) + list(session.dirty) if isinstance(o, _INDEXED)]
    deleted = [o for o in session.deleted if isinstance(o, _INDEXED)]
    if not touched and not deleted:
        return
    conn = session.connection()
    for obj in touched + deleted:
        kind = _kind_of(obj)
        if obj.id is not None:
            conn.execute(text(f"DELETE FROM {FTS_TABLE} WHERE kind=:k AND ref_id=:i"), {"k": kind, "i": obj.id})
    for obj in touched:
        doc = _document(conn, obj)
        if doc:
            conn.execute(
                text(f"INSERT INTO {FTS_TABLE}(kind, ref_id, day, dimension, title, content) VALUES (:k,:i,:d,:dim,:t,:c)"),
                {"k": doc[0], "i": doc[1], "d": doc[2], "dim": doc[3], "t": doc[4] or "", "c": doc[5] or ""},
            )


def rebuild(session: Session) -> int:
    """Reconstruit entièrement l'index (après une restauration par exemple)."""
    conn = session.connection()
    conn.execute(text(f"DELETE FROM {FTS_TABLE}"))
    count = 0
    for model in _INDEXED:
        for obj in session.query(model).all():
            doc = _document(conn, obj)
            if doc:
                conn.execute(
                    text(f"INSERT INTO {FTS_TABLE}(kind, ref_id, day, dimension, title, content) VALUES (:k,:i,:d,:dim,:t,:c)"),
                    {"k": doc[0], "i": doc[1], "d": doc[2], "dim": doc[3], "t": doc[4] or "", "c": doc[5] or ""},
                )
                count += 1
    session.commit()
    return count


KIND_LABELS = {
    "intention": "Intention", "activite": "Activité", "reflexion": "Réflexion", "media": "Média",
    "decision": "Décision", "objectif": "Objectif", "source": "Saisie originale", "journee": "Journée",
    "experience": "Expérience", "interaction": "Relation", "competence": "Compétence",
}


def _fts_query(q: str) -> str:
    words = re.findall(r"\w+", q, flags=re.UNICODE)
    words = [w for w in words if len(w) > 1 and _strip(w) not in STOPWORDS]
    return " OR ".join(f'"{w}"*' for w in words)


def _strip(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "a", "au", "aux", "en", "je", "j", "ai", "me",
    "m", "mon", "ma", "mes", "qu", "que", "qui", "quoi", "quel", "quels", "quelle", "quelles", "est", "ce", "cette",
    "ces", "sur", "pour", "dans", "par", "avec", "il", "elle", "on", "nous", "vous", "plus", "moins", "pas", "ne",
    "se", "sa", "son", "ses", "mois", "dernier", "derniere", "annee", "semaine", "jour", "jours", "fait", "eu",
    "suis", "etait", "ete", "comment", "pourquoi", "reviennent", "regulierement", "souvent",
}


def search(session: Session, q: str, *, kinds: list[str] | None = None, start: date | None = None,
           end: date | None = None, dimension: str | None = None, limit: int = 30) -> list[dict]:
    query = _fts_query(q)
    if not query:
        return []
    sql = (
        f"SELECT kind, ref_id, day, dimension, title, snippet({FTS_TABLE}, 5, '[', ']', ' ... ', 18) AS snip, "
        f"bm25({FTS_TABLE}) AS score FROM {FTS_TABLE} WHERE {FTS_TABLE} MATCH :q"
    )
    params: dict = {"q": query, "limit": limit}
    if kinds:
        sql += " AND kind IN (" + ",".join(f":k{i}" for i in range(len(kinds))) + ")"
        params.update({f"k{i}": k for i, k in enumerate(kinds)})
    if start:
        sql += " AND day >= :start"
        params["start"] = str(start)
    if end:
        sql += " AND day <= :end"
        params["end"] = str(end)
    if dimension:
        sql += " AND dimension = :dim"
        params["dim"] = dimension
    sql += " ORDER BY score LIMIT :limit"
    rows = session.connection().execute(text(sql), params).fetchall()
    return [
        {
            "kind": r.kind, "kind_label": KIND_LABELS.get(r.kind, r.kind), "ref_id": r.ref_id, "date": r.day,
            "dimension": r.dimension, "dimension_label": dimension_label(r.dimension) if r.dimension else None,
            "title": r.title, "snippet": r.snip, "score": round(-r.score, 3),
        }
        for r in rows
    ]
