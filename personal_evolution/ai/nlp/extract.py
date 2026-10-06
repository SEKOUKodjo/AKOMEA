"""Extraction locale d'informations structurées à partir de texte français.

Moteur à règles, transparent et sans dépendance réseau. Il produit des
propositions ; l'utilisateur les valide ou les corrige avant tout stockage.

    "J'ai travaillé 1h30 sur Python et terminé les exercices de régression."
    -> Études / Python / 90 minutes / résultat : exercices de régression terminés
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field

from .lexicon import EMOTIONS, LEXICON

ENGINE = "pei-regles-fr"
VERSION = "1.0"

DIMENSION_LABELS = {
    "spirituel": "Spirituel", "physique": "Physique", "etudes": "Études", "professionnel": "Professionnel",
    "personnel": "Personnel", "relationnel": "Relationnel", "loisirs": "Loisirs et créativité",
}

# Normalisation


def fold(text: str) -> str:
    """Minuscules sans accents, longueur conservée (indices identiques au texte original)."""
    out = []
    for ch in text:
        base = unicodedata.normalize("NFD", ch)
        base = "".join(c for c in base if unicodedata.category(c) != "Mn") or ch
        out.append(base[0].lower() if len(base) >= 1 else ch.lower())
    folded = "".join(out)
    return folded.replace("’", "'").replace("‘", "'")


# Durées

NUMBER_WORDS = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8,
    "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16,
    "vingt": 20, "vingt cinq": 25, "trente": 30, "quarante": 40, "quarante cinq": 45, "cinquante": 50,
    "soixante": 60, "quatre vingt": 80, "quatre vingt dix": 90,
}
_NUM_WORDS = "|".join(sorted((re.escape(k) for k in NUMBER_WORDS), key=len, reverse=True))
NUM = rf"(?:\d+(?:[.,]\d+)?|{_NUM_WORDS})"
_H = r"(?:heures?|hrs?|h)"
_M = r"(?:minutes?|mins?|mn)"

DURATION_RE = re.compile(
    r"(?<![\w])(?:"
    rf"(?P<hm>\d{{1,2}})\s*h\s*(?P<hm_m>\d{{1,2}})(?:\s*{_M})?"
    rf"|(?P<hd>{NUM})\s+{_H}\s+et\s+(?P<frac>demie|demi|quart)"
    rf"|(?P<hx>{NUM})\s+heures?\s+(?:et\s+)?(?P<hx_m>{NUM})(?:\s+{_M})?(?=\W|$)"
    r"|(?P<half>(?:une\s+)?demi[\s-]?heure)"
    r"|(?P<q3>trois\s+quarts?\s+d.heure)"
    r"|(?P<q1>(?:un\s+)?quart\s+d.heure)"
    rf"|(?P<h>{NUM})\s*{_H}(?![a-z])"
    rf"|(?P<m>{NUM})\s*{_M}(?![a-z])"
    r")"
)


def _num(token: str) -> float:
    token = token.strip().replace("-", " ")
    token = re.sub(r"\s+", " ", token)
    if token in NUMBER_WORDS:
        return float(NUMBER_WORDS[token])
    return float(token.replace(",", "."))


def find_durations(folded: str) -> list[tuple[int, int, int]]:
    """Renvoie [(début, fin, minutes)] pour chaque durée trouvée."""
    found = []
    for mt in DURATION_RE.finditer(folded):
        g = mt.groupdict()
        minutes: float | None = None
        if g["hm"]:
            minutes = int(g["hm"]) * 60 + int(g["hm_m"])
        elif g["hd"]:
            minutes = _num(g["hd"]) * 60 + (15 if g["frac"] == "quart" else 30)
        elif g["hx"]:
            extra = _num(g["hx_m"])
            if extra >= 60:
                continue
            minutes = _num(g["hx"]) * 60 + extra
        elif g["half"]:
            minutes = 30
        elif g["q3"]:
            minutes = 45
        elif g["q1"]:
            minutes = 15
        elif g["h"]:
            minutes = _num(g["h"]) * 60
        elif g["m"]:
            minutes = _num(g["m"])
        if minutes is not None and 0 < minutes <= 24 * 60:
            found.append((mt.start(), mt.end(), int(round(minutes))))
    return found


def parse_minutes(text: str) -> int | None:
    """Convertit une durée isolée ("1h30", "une heure quinze", "45 min") en minutes."""
    d = find_durations(fold(text))
    return d[0][2] if d else None


def _mask(folded: str, spans: list[tuple[int, int, int]]) -> str:
    chars = list(folded)
    for start, end, _ in spans:
        for i in range(start, end):
            chars[i] = "§"
    return "".join(chars)


# Classification

_COMPILED = [(re.compile(rf"(?<![a-z]){pat}"), dim, cat, w) for pat, dim, cat, w in LEXICON]


def classify(folded: str) -> tuple[str | None, str | None, float]:
    """Retourne (dimension, catégorie, confiance) du mot clé le plus spécifique."""
    best = None
    for rx, dim, cat, weight in _COMPILED:
        if rx.search(folded):
            if best is None or weight > best[2]:
                best = (dim, cat, weight)
    if best is None:
        return None, None, 0.0
    return best[0], best[1], min(1.0, 0.4 + best[2] / 10)


# Découpage


_FILLERS = re.compile(
    r"^(?:\s|\bet\b|\bpuis\b|\bensuite\b|\baussi\b|\benfin\b|\bd.abord\b|\bdonc\b|\bmais\b|"
    r"aujourd.?hui|ce matin|ce soir|cet apres.midi|demain|"
    r"je (?:veux|voudrais|vais|compte|dois|souhaite|prevois de|pense|aimerais)|j.aimerais|"
    r"j.ai l.intention de|il faut que je|mon objectif (?:est|sera) de|objectifs?\s*:?|"
    r"au programme\s*:?|j.ai prevu de|je me fixe de|"
    r"\bde\b|\bd'|\bdu\b|:|-)+"
)

_SPLIT_INTENTIONS = re.compile(r"[,;.!?\n]+|\s+et\s+|\s+puis\s+|\s+ensuite\s+|\s+ainsi que\s+|\s+plus\s+")


def _segments(folded_masked: str, pattern: re.Pattern) -> list[tuple[int, int]]:
    spans, pos = [], 0
    for mt in pattern.finditer(folded_masked):
        if mt.start() > pos:
            spans.append((pos, mt.start()))
        pos = mt.end()
    if pos < len(folded_masked):
        spans.append((pos, len(folded_masked)))
    return spans


def _clean(original: str, folded: str) -> tuple[str, str]:
    """Retire les formules d'introduction ; renvoie (texte original nettoyé, version pliée)."""
    mt = _FILLERS.match(folded)
    cut = mt.end() if mt else 0
    o, f = original[cut:].strip(" ,.;:"), folded[cut:].strip(" ,.;:")
    return o, f


def _capitalize(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1].upper() + s[1:] if s else s


_HIGH = re.compile(r"absolument|surtout|prioritaire|priorite|important|imperativement|sans faute")
_LOW = re.compile(r"si possible|si j.ai le temps|eventuellement|peut.etre|si je peux|bonus")


@dataclass
class Item:
    type: str  # intention, activite, non_realise, resultat
    description: str
    dimension: str | None = None
    dimension_label: str | None = None
    category: str | None = None
    minutes: int | None = None
    planned_minutes: int | None = None
    priority: int = 2
    result: str | None = None
    reason: str | None = None
    status: str | None = None
    intention_id: int | None = None
    match_score: float = 0.0
    confidence: float = 0.0


@dataclass
class ExtractionResult:
    items: list[Item] = field(default_factory=list)
    reflections: list[dict] = field(default_factory=list)
    emotions: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    engine: str = ENGINE
    version: str = VERSION

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _make_item(kind: str, original: str, folded: str, durations, start: int, end: int) -> Item | None:
    o, f = _clean(original[start:end], folded[start:end])
    if len(f.replace("§", "").strip()) < 2:
        return None
    dim, cat, conf = classify(f)
    mins = [d[2] for d in durations if d[0] >= start and d[1] <= end]
    item = Item(type=kind, description=_capitalize(o), dimension=dim, dimension_label=DIMENSION_LABELS.get(dim),
                category=cat, minutes=mins[0] if mins else None, confidence=round(conf, 2))
    if _HIGH.search(f):
        item.priority = 1
    elif _LOW.search(f):
        item.priority = 3
    return item


def extract_intentions(text: str) -> ExtractionResult:
    """Matin : texte libre -> liste d'intentions proposées."""
    res = ExtractionResult()
    if not text or not text.strip():
        return res
    folded = fold(text)
    durations = find_durations(folded)
    masked = _mask(folded, durations)
    for start, end in _segments(masked, _SPLIT_INTENTIONS):
        item = _make_item("intention", text, folded, durations, start, end)
        if item is None:
            continue
        # Un fragment sans catégorie ni durée prolonge le précédent ("lire et résumer").
        if item.category is None and item.minutes is None and res.items:
            prev = res.items[-1]
            prev.description = f"{prev.description} et {item.description[:1].lower() + item.description[1:]}"
            continue
        res.items.append(item)
    for it in res.items:
        it.status = "prevu"
        if it.dimension is None:
            res.warnings.append(f"Dimension non reconnue pour : {it.description}")
    return res


# Bilan du soir

_SENTENCES = re.compile(r"[.!?\n;]+")
_CLAUSES = re.compile(r",|\s+et\s+|\s+puis\s+|\s+ensuite\s+|\s+mais\s+")
_NEG = re.compile(
    r"n.ai pas|ne suis pas|n.ai rien|pas eu le temps|pas pu|n.ai pu|pas reussi|rate|annule|abandonne|"
    r"laisse tomber|zappe|oublie|reporte|pas fait|n.est pas|n.etait pas"
)
_REASON = re.compile(r"\b(?:parce qu.?|car|a cause d.?|faute d.?|vu qu.?|puisqu.?|etant donne qu.?)\s*")
_PLANNED = re.compile(r"(?:avais|etait|j.ai) prevu|je voulais|je comptais|je devais|objectif (?:de|etait)|initialement")
_RESULT_VERB = re.compile(
    r"^(?:(?:j.ai|je suis|on a)\s+)?(?:enfin\s+|finalement\s+|bien\s+)?"
    r"(?:termine|fini|acheve|complete|boucle|reussi|realise|resolu|valide|soumis|envoye|publie|redige|ecrit)\b"
)
_LEARN = re.compile(r"j.ai (?:appris|compris|decouvert|retenu|realise que)|j.ai enfin compris|nouvelle notion")
_DIFFICULTY = re.compile(r"difficile|difficulte|bloque|galere|du mal a|pas compris|complique|obstacle|probleme")
_GRATITUDE = re.compile(r"merci|reconnaissant|gratitude|rends grace|benediction")
_EVENT = re.compile(r"ce qui m.a marque|marquant|m.a marque|evenement|inoubliable")
_PAST = re.compile(r"j.ai|je suis|on a|nous avons|j.etais|fait|termine|lu|travaille|couru|marche|prie|ecoute|regarde")


def _strip_reason(original: str, folded: str) -> tuple[str, str, str | None]:
    mt = _REASON.search(folded)
    if not mt:
        return original, folded, None
    reason = original[mt.end():].strip(" ,.;")
    return original[: mt.start()], folded[: mt.start()], reason or None


def extract_review(text: str, intentions: list[dict] | None = None) -> ExtractionResult:
    """Soir : bilan libre -> activités, non réalisations, résultats, réflexions.

    intentions : [{"id", "description", "category", "dimension", "estimated_minutes"}]
    """
    res = ExtractionResult()
    if not text or not text.strip():
        return res
    intentions = intentions or []
    folded_all = fold(text)

    for s_start, s_end in _segments(folded_all, _SENTENCES):
        s_orig, s_fold = text[s_start:s_end], folded_all[s_start:s_end]
        if not s_fold.strip():
            continue
        if _LEARN.search(s_fold):
            res.reflections.append({"kind": "apprentissage", "content": _capitalize(s_orig), "dimension": classify(s_fold)[0]})
        if _GRATITUDE.search(s_fold):
            res.reflections.append({"kind": "gratitude", "content": _capitalize(s_orig), "dimension": None})
        if _EVENT.search(s_fold):
            res.reflections.append({"kind": "evenement", "content": _capitalize(s_orig), "dimension": classify(s_fold)[0]})

        body_o, body_f, reason = _strip_reason(s_orig, s_fold)
        durations = find_durations(body_f)
        dim, cat, conf = classify(body_f)

        # Prévu contre réalisé dans une même phrase.
        if _PLANNED.search(body_f) and len(durations) >= 2 and cat:
            item = Item(type="activite", description=_capitalize(body_o), dimension=dim,
                        dimension_label=DIMENSION_LABELS.get(dim), category=cat, planned_minutes=durations[0][2],
                        minutes=durations[1][2], reason=reason, confidence=round(conf, 2))
            res.items.append(item)
            # Les propositions suivantes de la phrase peuvent porter un résultat.
            _attach_trailing_results(body_o, body_f, durations, item)
            continue

        if _DIFFICULTY.search(body_f) and not _NEG.search(body_f):
            res.reflections.append({"kind": "difficulte", "content": _capitalize(s_orig), "dimension": dim})

        masked = _mask(body_f, durations)
        last: Item | None = None
        for c_start, c_end in _segments(masked, _CLAUSES):
            c_fold = body_f[c_start:c_end].strip()
            if not c_fold:
                continue
            if _LEARN.search(c_fold):
                continue  # déjà enregistré comme apprentissage
            if _RESULT_VERB.search(c_fold.lstrip(" ,")) and last is not None:
                last.result = _join_result(last.result, _capitalize(body_o[c_start:c_end].strip(" ,")))
                continue
            negative = bool(_NEG.search(c_fold))
            kind = "non_realise" if negative else "activite"
            item = _make_item(kind, body_o, body_f, durations, c_start, c_end)
            if item is None:
                continue
            if _RESULT_VERB.search(c_fold) and item.category is None:
                previous = next((i for i in reversed(res.items) if i.type == "activite"), None)
                if previous is not None:
                    previous.result = _join_result(previous.result, item.description)
                    continue
                item.type, item.result = "resultat", item.description
            if item.category is None and item.minutes is None and item.type != "resultat":
                continue  # proposition sans information exploitable, conservée dans la source brute
            if not negative and not _PAST.search(c_fold) and item.minutes is None and item.type != "resultat":
                continue
            if negative:
                item.reason = reason
                item.minutes = None
            res.items.append(item)
            last = item
        if reason and not any(i.reason == reason for i in res.items):
            res.reflections.append({"kind": "difficulte", "content": _capitalize(reason), "dimension": dim})

    for word, (emotion, polarity) in EMOTIONS.items():
        if re.search(rf"(?<![a-z]){re.escape(word)}", folded_all):
            res.emotions.append({"word": word, "emotion": emotion, "polarity": polarity})

    _match_intentions(res, intentions)
    return res


def _join_result(prev: str | None, new: str) -> str:
    return f"{prev} ; {new}" if prev else new


def _attach_trailing_results(body_o: str, body_f: str, durations, item: Item) -> None:
    masked = _mask(body_f, durations)
    for c_start, c_end in _segments(masked, re.compile(r",|\s+et\s+")):
        clause = body_f[c_start:c_end].strip()
        if _RESULT_VERB.search(clause):
            item.result = _join_result(item.result, _capitalize(body_o[c_start:c_end].strip(" ,")))


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{3,}", fold(s or "")) if w not in _STOP}


_STOP = {"faire", "les", "des", "une", "sur", "pour", "avec", "mon", "mes", "dans", "aujourd", "hui", "minutes",
         "heures", "heure", "travailler", "ai", "pas", "j'ai", "fait", "suis", "etait", "prevu"}


def _match_intentions(res: ExtractionResult, intentions: list[dict]) -> None:
    """Relie chaque élément extrait à l'intention du matin la plus proche."""
    if not intentions:
        return
    used: set[int] = set()
    for item in res.items:
        best, best_score = None, 0.0
        for it in intentions:
            score = 0.0
            if item.category and it.get("category") and fold(item.category) == fold(it["category"]):
                score += 1.0
            a, b = _tokens(item.description), _tokens(it.get("description", ""))
            if a and b:
                score += len(a & b) / len(a | b)
            if item.dimension and item.dimension == it.get("dimension"):
                score += 0.2
            if it["id"] in used:
                score -= 0.3
            if score > best_score:
                best, best_score = it, score
        if best is not None and best_score >= 0.35:
            item.intention_id = best["id"]
            item.match_score = round(best_score, 2)
            used.add(best["id"])
            est = item.planned_minutes or best.get("estimated_minutes")
            if item.type == "non_realise":
                item.status = "non_realise"
            elif item.minutes and est and item.minutes < 0.75 * est:
                item.status = "partiel"
            else:
                item.status = "realise"
            if item.planned_minutes is None:
                item.planned_minutes = best.get("estimated_minutes")
        elif item.type == "non_realise":
            item.status = "non_realise"
