"""Extraction locale d'informations structurées, à partir de texte français ou anglais.

Moteur à règles, transparent et sans dépendance réseau. Il produit des
propositions ; l'utilisateur les valide ou les corrige avant tout stockage.

    "J'ai travaillé 1h30 sur Python et terminé les exercices de régression."
    "I worked 1h30 on Python and finished the regression exercises."
    -> Études / Python / 90 minutes / résultat : exercices de régression terminés

La langue du texte est détectée automatiquement ; les catégories et les
libellés renvoyés sont dans la langue de l'interface (out_lang).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field

from .lexicon import EMOTIONS, LEXICON
from .lexicon_en import CATEGORY_EN, DIMENSION_LABELS_EN, EMOTIONS_EN, LEXICON_EN

ENGINE = "pei-regles-fr"
VERSION = "1.1"

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


# Règles propres à chaque langue


@dataclass
class Rules:
    lang: str
    engine: str
    number_words: dict
    duration_re: re.Pattern
    lexicon: list
    emotions: dict
    fillers: re.Pattern
    split_intentions: re.Pattern
    high: re.Pattern
    low: re.Pattern
    clauses: re.Pattern
    trailing: re.Pattern
    neg: re.Pattern
    reason: re.Pattern
    planned: re.Pattern
    result_verb: re.Pattern
    learn: re.Pattern
    difficulty: re.Pattern
    gratitude: re.Pattern
    event: re.Pattern
    past: re.Pattern
    stop: set
    join_word: str
    compiled: list = field(default_factory=list)

    def __post_init__(self):
        self.compiled = [(re.compile(rf"(?<![a-z]){pat}"), dim, cat, w) for pat, dim, cat, w in self.lexicon]


def _num_alternation(words: dict) -> str:
    return "|".join(sorted((re.escape(k) for k in words), key=len, reverse=True))


# Français

NUMBER_WORDS = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8,
    "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16,
    "vingt": 20, "vingt cinq": 25, "trente": 30, "quarante": 40, "quarante cinq": 45, "cinquante": 50,
    "soixante": 60, "quatre vingt": 80, "quatre vingt dix": 90,
}
NUM = rf"(?:\d+(?:[.,]\d+)?|{_num_alternation(NUMBER_WORDS)})"
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

FR = Rules(
    lang="fr", engine="pei-regles-fr", number_words=NUMBER_WORDS, duration_re=DURATION_RE,
    lexicon=LEXICON, emotions=EMOTIONS,
    fillers=re.compile(
        r"^(?:\s|\bet\b|\bpuis\b|\bensuite\b|\baussi\b|\benfin\b|\bd.abord\b|\bdonc\b|\bmais\b|"
        r"aujourd.?hui|ce matin|ce soir|cet apres.midi|demain|"
        r"je (?:veux|voudrais|vais|compte|dois|souhaite|prevois de|pense|aimerais)|j.aimerais|"
        r"j.ai l.intention de|il faut que je|mon objectif (?:est|sera) de|objectifs?\s*:?|"
        r"au programme\s*:?|j.ai prevu de|je me fixe de|"
        r"\bde\b|\bd'|\bdu\b|:|-)+"),
    split_intentions=re.compile(r"[,;.!?\n]+|\s+et\s+|\s+puis\s+|\s+ensuite\s+|\s+ainsi que\s+|\s+plus\s+"),
    high=re.compile(r"absolument|surtout|prioritaire|priorite|important|imperativement|sans faute"),
    low=re.compile(r"si possible|si j.ai le temps|eventuellement|peut.etre|si je peux|bonus"),
    clauses=re.compile(r",|\s+et\s+|\s+puis\s+|\s+ensuite\s+|\s+mais\s+"),
    trailing=re.compile(r",|\s+et\s+"),
    neg=re.compile(
        r"n.ai pas|ne suis pas|n.ai rien|pas eu le temps|pas pu|n.ai pu|pas reussi|rate|annule|abandonne|"
        r"laisse tomber|zappe|oublie|reporte|pas fait|n.est pas|n.etait pas"),
    reason=re.compile(r"\b(?:parce qu.?|car|a cause d.?|faute d.?|vu qu.?|puisqu.?|etant donne qu.?)\s*"),
    planned=re.compile(r"(?:avais|etait|j.ai) prevu|je voulais|je comptais|je devais|objectif (?:de|etait)|initialement"),
    result_verb=re.compile(
        r"^(?:(?:j.ai|je suis|on a)\s+)?(?:enfin\s+|finalement\s+|bien\s+)?"
        r"(?:termine|fini|acheve|complete|boucle|reussi|realise|resolu|valide|soumis|envoye|publie|redige|ecrit)\b"),
    learn=re.compile(r"j.ai (?:appris|compris|decouvert|retenu|realise que)|j.ai enfin compris|nouvelle notion"),
    difficulty=re.compile(r"difficile|difficulte|bloque|galere|du mal a|pas compris|complique|obstacle|probleme"),
    gratitude=re.compile(r"merci|reconnaissant|gratitude|rends grace|benediction"),
    event=re.compile(r"ce qui m.a marque|marquant|m.a marque|evenement|inoubliable"),
    past=re.compile(r"j.ai|je suis|on a|nous avons|j.etais|fait|termine|lu|travaille|couru|marche|prie|ecoute|regarde"),
    stop={"faire", "les", "des", "une", "sur", "pour", "avec", "mon", "mes", "dans", "aujourd", "hui", "minutes",
          "heures", "heure", "travailler", "ai", "pas", "j'ai", "fait", "suis", "etait", "prevu"},
    join_word="et",
)

# Anglais

NUMBER_WORDS_EN = {
    "one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "twenty five": 25,
    "thirty": 30, "forty": 40, "forty five": 45, "fifty": 50, "sixty": 60, "ninety": 90,
}
NUM_EN = rf"(?:\d+(?:[.,]\d+)?|{_num_alternation(NUMBER_WORDS_EN)})"
_H_EN = r"(?:hours?|hrs?|h)"
_M_EN = r"(?:minutes?|mins?)"

DURATION_RE_EN = re.compile(
    r"(?<![\w])(?:"
    rf"(?P<hm>\d{{1,2}})\s*h\s*(?P<hm_m>\d{{1,2}})(?:\s*{_M_EN})?"
    rf"|(?P<hd>{NUM_EN})\s+{_H_EN}\s+and\s+a\s+(?P<frac>half|quarter)"
    rf"|(?P<oah>{NUM_EN})\s+and\s+a\s+half\s+{_H_EN}"
    rf"|(?P<hx>{NUM_EN})\s+hours?\s+(?:and\s+)?(?P<hx_m>{NUM_EN})(?:\s+{_M_EN})?(?=\W|$)"
    r"|(?P<half>(?:a\s+)?half\s+(?:an\s+)?hour)"
    r"|(?P<q3>three\s+quarters?\s+of\s+an\s+hour)"
    r"|(?P<q1>(?:a\s+)?quarter\s+(?:of\s+an\s+)?hour)"
    rf"|(?P<h>{NUM_EN})\s*{_H_EN}(?![a-z])"
    rf"|(?P<m>{NUM_EN})\s*{_M_EN}(?![a-z])"
    r")"
)

EN = Rules(
    lang="en", engine="pei-rules-en", number_words=NUMBER_WORDS_EN, duration_re=DURATION_RE_EN,
    lexicon=LEXICON_EN, emotions=EMOTIONS_EN,
    fillers=re.compile(
        r"^(?:\s|\band\b|\bthen\b|\balso\b|\bfinally\b|\bfirst\b|\bso\b|\bbut\b|"
        r"today|this morning|this evening|this afternoon|tonight|tomorrow|"
        r"i (?:absolutely |really |definitely )?(?:want|would like|will|am going|plan|need|have|hope|intend|must|should)"
        r"(?: to)?|i.d like to|i.ll|"
        r"i.m going to|my goal (?:is|will be) to|goals?\s*:?|plan\s*:|on the agenda\s*:?|\bto\b|:|-)+"),
    split_intentions=re.compile(r"[,;.!?\n]+|\s+and\s+|\s+then\s+|\s+plus\s+|\s+as well as\s+"),
    high=re.compile(r"absolutely|\bmust\b|really need|priority|important|without fail|above all"),
    low=re.compile(r"if possible|if i have time|if i have the time|maybe|perhaps|if i can|optional|bonus"),
    clauses=re.compile(r",|\s+and\s+|\s+then\s+|\s+but\s+"),
    trailing=re.compile(r",|\s+and\s+"),
    neg=re.compile(
        r"didn.?t|did not|couldn.?t|could not|wasn.?t able|was not able|no time|not able|failed to|skipped|"
        r"cancell?ed|gave up|give up|forgot|postponed|haven.?t|didnt|never got"),
    reason=re.compile(r"\b(?:because(?: of)?|since|due to|as i was|as i had)\s*"),
    planned=re.compile(r"had planned|i planned|planned to|i wanted to|was supposed to|i intended|my goal was|initially"),
    result_verb=re.compile(
        r"^(?:(?:i|we)\s+)?(?:finally\s+|also\s+|successfully\s+)?"
        r"(?:finished|completed|done with|wrapped up|solved|submitted|sent|published|wrote|achieved|got through)\b"),
    learn=re.compile(r"i (?:learned|learnt|understood|discovered|realized that|realised that)|finally understood|new concept"),
    difficulty=re.compile(r"difficult|hard time|struggl|stuck|blocked|didn.?t understand|complicated|obstacle|problem"),
    gratitude=re.compile(r"thank|grateful|gratitude|blessed|blessing"),
    event=re.compile(r"stood out|memorable|highlight of|unforgettable|what struck me|struck me"),
    past=re.compile(r"\bi\b|\bwe\b|\bdid\b|\bwas\b|\bwere\b|\bhad\b|worked|\bread\b|\bran\b|walked|prayed|listened|"
                    r"watched|studied|finished|went|played|called|wrote|spent|exercised"),
    stop={"the", "and", "for", "with", "my", "on", "of", "today", "minutes", "hours", "hour", "work", "did", "was",
          "planned", "want", "do", "had", "have", "some", "this", "that", "from"},
    join_word="and",
)

RULES = {"fr": FR, "en": EN}

_FR_MARKERS = {"je", "j", "le", "la", "les", "des", "du", "de", "et", "pour", "sur", "avec", "aujourd", "ai", "pas",
               "une", "un", "mon", "ma", "mes", "est", "suis", "a", "au", "ce", "veux", "fait", "parce", "que"}
_EN_MARKERS = {"i", "the", "to", "and", "of", "for", "on", "with", "today", "my", "have", "had", "was", "did",
               "didn", "want", "will", "an", "is", "because", "worked", "read", "minutes", "hours", "hour"}


def detect_language(text: str) -> str:
    """Langue du texte (fr ou en), par comptage de mots outils."""
    words = re.findall(r"[a-z]+", fold(text or ""))
    fr = sum(w in _FR_MARKERS for w in words)
    en = sum(w in _EN_MARKERS for w in words)
    return "en" if en > fr else "fr"


def _rules(text: str, lang: str | None) -> Rules:
    return RULES.get(lang or detect_language(text), FR)


def category_label(cat: str | None, out_lang: str) -> str | None:
    """Libellé de catégorie dans la langue de l'interface."""
    if cat is None or out_lang != "en":
        return cat
    return CATEGORY_EN.get(cat, cat)


_CATEGORY_FR = {v: k for k, v in CATEGORY_EN.items()}


def category_display(cat: str | None, lang: str) -> str | None:
    """Catégorie enregistrée dans une langue, affichée dans la langue de l'interface (dans les deux sens)."""
    if not cat:
        return cat
    return CATEGORY_EN.get(cat, cat) if lang == "en" else _CATEGORY_FR.get(cat, cat)


def dimension_label_for(dim: str | None, out_lang: str) -> str | None:
    if dim is None:
        return None
    return (DIMENSION_LABELS_EN if out_lang == "en" else DIMENSION_LABELS).get(dim)


# Durées


def _num(token: str, rules: Rules = FR) -> float:
    token = token.strip().replace("-", " ")
    token = re.sub(r"\s+", " ", token)
    if token in rules.number_words:
        return float(rules.number_words[token])
    return float(token.replace(",", "."))


def find_durations(folded: str, rules: Rules = FR) -> list[tuple[int, int, int]]:
    """Renvoie [(début, fin, minutes)] pour chaque durée trouvée."""
    found = []
    for mt in rules.duration_re.finditer(folded):
        g = mt.groupdict()
        minutes: float | None = None
        if g["hm"]:
            minutes = int(g["hm"]) * 60 + int(g["hm_m"])
        elif g["hd"]:
            minutes = _num(g["hd"], rules) * 60 + (15 if g["frac"] in ("quart", "quarter") else 30)
        elif g.get("oah"):
            minutes = _num(g["oah"], rules) * 60 + 30
        elif g["hx"]:
            extra = _num(g["hx_m"], rules)
            if extra >= 60:
                continue
            minutes = _num(g["hx"], rules) * 60 + extra
        elif g["half"]:
            minutes = 30
        elif g["q3"]:
            minutes = 45
        elif g["q1"]:
            minutes = 15
        elif g["h"]:
            minutes = _num(g["h"], rules) * 60
        elif g["m"]:
            minutes = _num(g["m"], rules)
        if minutes is not None and 0 < minutes <= 24 * 60:
            found.append((mt.start(), mt.end(), int(round(minutes))))
    return found


def parse_minutes(text: str, lang: str | None = None) -> int | None:
    """Convertit une durée isolée ("1h30", "une heure quinze", "an hour and a half") en minutes."""
    folded = fold(text)
    rules = RULES[lang] if lang in RULES else None
    for r in ([rules] if rules else [FR, EN]):
        d = find_durations(folded, r)
        if d:
            return d[0][2]
    return None


def _mask(folded: str, spans: list[tuple[int, int, int]]) -> str:
    chars = list(folded)
    for start, end, _ in spans:
        for i in range(start, end):
            chars[i] = "§"
    return "".join(chars)


# Classification


def classify(folded: str, rules: Rules = FR) -> tuple[str | None, str | None, float]:
    """Retourne (dimension, catégorie, confiance) du mot clé le plus spécifique."""
    best = None
    for rx, dim, cat, weight in rules.compiled:
        if rx.search(folded):
            if best is None or weight > best[2]:
                best = (dim, cat, weight)
    if best is None:
        return None, None, 0.0
    return best[0], best[1], min(1.0, 0.4 + best[2] / 10)


# Découpage


def _segments(folded_masked: str, pattern: re.Pattern) -> list[tuple[int, int]]:
    spans, pos = [], 0
    for mt in pattern.finditer(folded_masked):
        if mt.start() > pos:
            spans.append((pos, mt.start()))
        pos = mt.end()
    if pos < len(folded_masked):
        spans.append((pos, len(folded_masked)))
    return spans


def _clean(original: str, folded: str, rules: Rules = FR) -> tuple[str, str]:
    """Retire les formules d'introduction ; renvoie (texte original nettoyé, version pliée)."""
    mt = rules.fillers.match(folded)
    cut = mt.end() if mt else 0
    o, f = original[cut:].strip(" ,.;:"), folded[cut:].strip(" ,.;:")
    return o, f


def _capitalize(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1].upper() + s[1:] if s else s


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
    language: str = "fr"

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _make_item(kind: str, original: str, folded: str, durations, start: int, end: int, rules: Rules = FR) -> Item | None:
    o, f = _clean(original[start:end], folded[start:end], rules)
    if len(f.replace("§", "").strip()) < 2:
        return None
    dim, cat, conf = classify(f, rules)
    mins = [d[2] for d in durations if d[0] >= start and d[1] <= end]
    item = Item(type=kind, description=_capitalize(o), dimension=dim, category=cat,
                minutes=mins[0] if mins else None, confidence=round(conf, 2))
    raw = folded[start:end]  # la priorité se lit avant le nettoyage ("I absolutely must...")
    if rules.high.search(raw):
        item.priority = 1
    elif rules.low.search(raw):
        item.priority = 3
    return item


def _localize(res: ExtractionResult, out_lang: str) -> ExtractionResult:
    """Catégories et libellés dans la langue de l'interface."""
    for it in res.items:
        it.category = category_label(it.category, out_lang)
        it.dimension_label = dimension_label_for(it.dimension, out_lang)
    return res


def extract_intentions(text: str, lang: str | None = None, out_lang: str = "fr") -> ExtractionResult:
    """Matin : texte libre -> liste d'intentions proposées."""
    rules = _rules(text, lang)
    res = ExtractionResult(engine=rules.engine, language=rules.lang)
    if not text or not text.strip():
        return res
    folded = fold(text)
    durations = find_durations(folded, rules)
    masked = _mask(folded, durations)
    for start, end in _segments(masked, rules.split_intentions):
        item = _make_item("intention", text, folded, durations, start, end, rules)
        if item is None:
            continue
        # Un fragment sans catégorie ni durée prolonge le précédent ("lire et résumer").
        if item.category is None and item.minutes is None and res.items:
            prev = res.items[-1]
            prev.description = f"{prev.description} {rules.join_word} {item.description[:1].lower() + item.description[1:]}"
            continue
        res.items.append(item)
    for it in res.items:
        it.status = "prevu"
        if it.dimension is None:
            res.warnings.append(("Unrecognised dimension for: {d}" if out_lang == "en"
                                 else "Dimension non reconnue pour : {d}").format(d=it.description))
    return _localize(res, out_lang)


# Bilan du soir


_SENTENCES = re.compile(r"[.!?\n;]+")


def _strip_reason(original: str, folded: str, rules: Rules = FR) -> tuple[str, str, str | None]:
    mt = rules.reason.search(folded)
    if not mt:
        return original, folded, None
    reason = original[mt.end():].strip(" ,.;")
    return original[: mt.start()], folded[: mt.start()], reason or None


def extract_review(text: str, intentions: list[dict] | None = None, lang: str | None = None,
                   out_lang: str = "fr") -> ExtractionResult:
    """Soir : bilan libre -> activités, non réalisations, résultats, réflexions.

    intentions : [{"id", "description", "category", "dimension", "estimated_minutes"}]
    """
    rules = _rules(text, lang)
    res = ExtractionResult(engine=rules.engine, language=rules.lang)
    if not text or not text.strip():
        return res
    intentions = intentions or []
    folded_all = fold(text)

    for s_start, s_end in _segments(folded_all, _SENTENCES):
        s_orig, s_fold = text[s_start:s_end], folded_all[s_start:s_end]
        if not s_fold.strip():
            continue
        if rules.learn.search(s_fold):
            res.reflections.append({"kind": "apprentissage", "content": _capitalize(s_orig),
                                    "dimension": classify(s_fold, rules)[0]})
        if rules.gratitude.search(s_fold):
            res.reflections.append({"kind": "gratitude", "content": _capitalize(s_orig), "dimension": None})
        if rules.event.search(s_fold):
            res.reflections.append({"kind": "evenement", "content": _capitalize(s_orig),
                                    "dimension": classify(s_fold, rules)[0]})

        body_o, body_f, reason = _strip_reason(s_orig, s_fold, rules)
        durations = find_durations(body_f, rules)
        dim, cat, conf = classify(body_f, rules)

        # Prévu contre réalisé dans une même phrase.
        if rules.planned.search(body_f) and len(durations) >= 2 and cat:
            item = Item(type="activite", description=_capitalize(body_o), dimension=dim, category=cat,
                        planned_minutes=durations[0][2], minutes=durations[1][2], reason=reason,
                        confidence=round(conf, 2))
            res.items.append(item)
            # Les propositions suivantes de la phrase peuvent porter un résultat.
            _attach_trailing_results(body_o, body_f, durations, item, rules)
            continue

        if rules.difficulty.search(body_f) and not rules.neg.search(body_f):
            res.reflections.append({"kind": "difficulte", "content": _capitalize(s_orig), "dimension": dim})

        masked = _mask(body_f, durations)
        last: Item | None = None
        for c_start, c_end in _segments(masked, rules.clauses):
            c_fold = body_f[c_start:c_end].strip()
            if not c_fold:
                continue
            if rules.learn.search(c_fold):
                continue  # déjà enregistré comme apprentissage
            if rules.gratitude.search(c_fold) and not any(d[0] >= c_start and d[1] <= c_end for d in durations):
                continue  # déjà enregistré comme gratitude
            if rules.result_verb.search(c_fold.lstrip(" ,")) and last is not None:
                last.result = _join_result(last.result, _capitalize(body_o[c_start:c_end].strip(" ,")))
                continue
            negative = bool(rules.neg.search(c_fold))
            kind = "non_realise" if negative else "activite"
            item = _make_item(kind, body_o, body_f, durations, c_start, c_end, rules)
            if item is None:
                continue
            if rules.result_verb.search(c_fold) and item.category is None:
                previous = next((i for i in reversed(res.items) if i.type == "activite"), None)
                if previous is not None:
                    previous.result = _join_result(previous.result, item.description)
                    continue
                item.type, item.result = "resultat", item.description
            if item.category is None and item.minutes is None and item.type != "resultat":
                continue  # proposition sans information exploitable, conservée dans la source brute
            if not negative and not rules.past.search(c_fold) and item.minutes is None and item.type != "resultat":
                continue
            if negative:
                item.reason = reason
                item.minutes = None
            res.items.append(item)
            last = item
        if reason and not any(i.reason == reason for i in res.items):
            res.reflections.append({"kind": "difficulte", "content": _capitalize(reason), "dimension": dim})

    for word, (emotion, polarity) in rules.emotions.items():
        if re.search(rf"(?<![a-z]){re.escape(word)}", folded_all):
            res.emotions.append({"word": word, "emotion": emotion, "polarity": polarity})

    _localize(res, out_lang)
    _match_intentions(res, intentions, rules)
    return res


def _join_result(prev: str | None, new: str) -> str:
    return f"{prev} ; {new}" if prev else new


def _attach_trailing_results(body_o: str, body_f: str, durations, item: Item, rules: Rules = FR) -> None:
    masked = _mask(body_f, durations)
    for c_start, c_end in _segments(masked, rules.trailing):
        clause = body_f[c_start:c_end].strip()
        if rules.result_verb.search(clause):
            item.result = _join_result(item.result, _capitalize(body_o[c_start:c_end].strip(" ,")))


def _tokens(s: str, rules: Rules = FR) -> set[str]:
    stop = FR.stop | EN.stop
    return {w for w in re.findall(r"[a-z0-9]{3,}", fold(s or "")) if w not in stop}


def _same_category(a: str | None, b: str | None) -> bool:
    """Même catégorie, même si l'une est écrite en français et l'autre en anglais."""
    if not a or not b:
        return False
    fa, fb = fold(a), fold(b)
    if fa == fb:
        return True
    reverse = {fold(v): fold(k) for k, v in CATEGORY_EN.items()}
    return reverse.get(fa, fa) == reverse.get(fb, fb)


def _match_intentions(res: ExtractionResult, intentions: list[dict], rules: Rules = FR) -> None:
    """Relie chaque élément extrait à l'intention du matin la plus proche."""
    if not intentions:
        return
    used: set[int] = set()
    for item in res.items:
        best, best_score = None, 0.0
        for it in intentions:
            score = 0.0
            if _same_category(item.category, it.get("category")):
                score += 1.0
            a, b = _tokens(item.description, rules), _tokens(it.get("description", ""), rules)
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
