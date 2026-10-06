from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from ..config import settings
from ..db import get_session  # noqa: F401  (réexport pour les routes)


def require_pin(x_pei_pin: str | None = Header(default=None)) -> None:
    """Authentification locale facultative par code PIN (variable PEI_PIN)."""
    if not settings.pin:
        return
    if not x_pei_pin or not hmac.compare_digest(x_pei_pin, settings.pin):
        raise HTTPException(status_code=401, detail="Code PIN requis")


def not_found(what: str = "Élément") -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} introuvable")
