"""Traduction français / anglais.

Le texte français sert de clé ; le dictionnaire anglais se trouve dans
backend/locales/en.py. Une clé absente du dictionnaire reste en français, ce qui
ne casse jamais l'affichage. La langue courante est portée par une variable de
contexte, fixée à chaque requête (préférence du compte, cookie pei_lang ou
en tête Accept-Language).

    tr("Journée verrouillée")                 -> "Locked day" en anglais
    tr("Encore {n} jours", n=3)               -> "{n} days left" formaté
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .locales.en import EN

LANGS = ("fr", "en")
DEFAULT = "fr"
LANG_NAMES = {"fr": "Français", "en": "English"}
COOKIE = "pei_lang"

_current: ContextVar[str] = ContextVar("pei_lang", default=DEFAULT)


def normalize(lang: str | None) -> str:
    if not lang:
        return DEFAULT
    code = lang.strip().lower()[:2]
    return code if code in LANGS else DEFAULT


def from_accept_language(header: str | None) -> str | None:
    """Première langue prise en charge dans l'en tête Accept-Language du navigateur."""
    if not header:
        return None
    for part in header.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return None


def get_lang() -> str:
    return _current.get()


def set_lang(lang: str | None):
    return _current.set(normalize(lang))


@contextmanager
def use(lang: str | None) -> Iterator[str]:
    token = _current.set(normalize(lang))
    try:
        yield _current.get()
    finally:
        _current.reset(token)


def tr(text: str, lang: str | None = None, **kwargs) -> str:
    """Traduit un texte français dans la langue courante, puis remplace les {variables}."""
    code = normalize(lang) if lang else _current.get()
    out = EN.get(text, text) if code == "en" else text
    return out.format(**kwargs) if kwargs else out


def num(value, digits: int = 1, lang: str | None = None) -> str:
    """Nombre décimal avec la virgule en français et le point en anglais."""
    if value is None:
        return ""
    s = f"{value:.{digits}f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    code = normalize(lang) if lang else _current.get()
    return s.replace(".", ",") if code == "fr" else s


WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
WEEKDAYS_SHORT = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def weekday(i: int, short: bool = False) -> str:
    return tr((WEEKDAYS_SHORT if short else WEEKDAYS)[i])
