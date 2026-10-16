"""Compte, connexion et photo de profil."""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, File, Header, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models as m
from ..config import settings
from .. import i18n
from ..db import get_session
from ..services import auth, profile
from .deps import current_user

router = APIRouter(prefix="/api", tags=["compte"])


class SetupIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=200)
    display_name: str | None = Field(None, max_length=120)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)


class PreferencesIn(BaseModel):
    language: str = Field(pattern="^(fr|en)$")


class PasswordIn(BaseModel):
    current: str
    new: str = Field(min_length=8, max_length=200)


def _user_out(user: m.User) -> dict:
    return {"username": user.username, "display_name": user.display_name, "language": user.language or "fr",
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None}


def _set_cookie(response: Response, request: Request, token: str, language: str | None = None) -> None:
    response.set_cookie(auth.COOKIE, token, max_age=settings.session_days * 86400, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https", path="/")
    if language:
        response.set_cookie(i18n.COOKIE, language, max_age=365 * 86400, samesite="lax", path="/")


@router.get("/auth/status")
def status(pei_session: str | None = Cookie(default=None), authorization: str | None = Header(default=None),
           session: Session = Depends(get_session)):
    """Public : indique si un compte existe et si l'appareil est connecté."""
    user = auth.user_for_token(session, auth.token_from_request(pei_session, authorization))
    return {"configured": auth.is_configured(session), "authenticated": user is not None,
            "user": _user_out(user) if user else None, "backfill_days": settings.backfill_days,
            "language": (user.language if user else None) or i18n.get_lang(), "languages": i18n.LANG_NAMES}


@router.post("/auth/setup")
def setup(body: SetupIn, request: Request, response: Response, session: Session = Depends(get_session)):
    """Création du compte, possible une seule fois (premier lancement)."""
    try:
        created = auth.create_user(session, body.username, body.password, body.display_name)
        created.language = i18n.get_lang()
        session.commit()
        user, token = auth.login(session, body.username, body.password, request.headers.get("user-agent"))
    except auth.AuthError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    _set_cookie(response, request, token, user.language)
    return {"ok": True, "user": _user_out(user)}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, session: Session = Depends(get_session)):
    try:
        user, token = auth.login(session, body.username, body.password, request.headers.get("user-agent"))
    except auth.AuthError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    _set_cookie(response, request, token, user.language)
    return {"ok": True, "user": _user_out(user), "token": token}


@router.post("/auth/logout")
def logout(response: Response, pei_session: str | None = Cookie(default=None),
           authorization: str | None = Header(default=None), session: Session = Depends(get_session)):
    auth.logout(session, auth.token_from_request(pei_session, authorization))
    response.delete_cookie(auth.COOKIE, path="/")
    return {"ok": True}


@router.patch("/auth/preferences")
def preferences(body: PreferencesIn, response: Response, user: m.User = Depends(current_user),
                session: Session = Depends(get_session)):
    """Langue de l'interface, mémorisée dans le compte."""
    user = session.merge(user)
    user.language = body.language
    session.commit()
    response.set_cookie(i18n.COOKIE, body.language, max_age=365 * 86400, samesite="lax", path="/")
    return {"ok": True, "user": _user_out(user)}


@router.post("/auth/password")
def change_password(body: PasswordIn, user: m.User = Depends(current_user),
                    pei_session: str | None = Cookie(default=None), session: Session = Depends(get_session)):
    try:
        auth.change_password(session, session.merge(user), body.current, body.new, pei_session)
    except auth.AuthError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    return {"ok": True}


@router.post("/profil/photo")
def upload_photo(file: UploadFile = File(...), _user: m.User = Depends(current_user)):
    try:
        path = profile.save_photo(file)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "file": path.name}


@router.delete("/profil/photo")
def reset_photo(_user: m.User = Depends(current_user)):
    profile.remove_photo()
    return {"ok": True}
