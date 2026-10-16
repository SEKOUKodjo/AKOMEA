from __future__ import annotations

from datetime import date, timedelta

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models as m
from ..config import settings
from ..db import get_session
from ..services import auth


def current_user(request: Request, pei_session: str | None = Cookie(default=None),
                 authorization: str | None = Header(default=None),
                 session: Session = Depends(get_session)) -> m.User:
    """Exige une session valide (cookie pei_session ou en tête Authorization: Bearer)."""
    token = auth.token_from_request(pei_session, authorization)
    user = auth.user_for_token(session, token)
    if user is None:
        raise HTTPException(status_code=401, detail="Connexion requise")
    request.state.user = user
    return user


def not_found(what: str = "Élément") -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} introuvable")


def deadline(day: date) -> date:
    """Dernier jour où la journée peut encore être renseignée."""
    return day + timedelta(days=settings.backfill_days)


def is_editable(day: date, today: date | None = None) -> bool:
    today = today or date.today()
    return day <= today <= deadline(day)


def ensure_editable(day: date | None) -> None:
    """Refuse toute saisie sur une journée future ou passée depuis plus de N jours (4 par défaut)."""
    day = day or date.today()
    today = date.today()
    if day > today:
        raise HTTPException(status_code=403, detail="On ne peut pas renseigner une journée future.")
    if not is_editable(day, today):
        raise HTTPException(
            status_code=403,
            detail=(f"La journée du {day:%d/%m/%Y} est verrouillée : une journée ne peut être renseignée que "
                    f"jusqu'à {settings.backfill_days} jours après (au plus tard le {deadline(day):%d/%m/%Y})."),
        )


def ensure_day_id_editable(session: Session, day_id: int) -> None:
    day = session.get(m.Day, day_id)
    if day is not None:
        ensure_editable(day.date)
