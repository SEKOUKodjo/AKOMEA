"""Authentification locale : compte unique, mot de passe haché, sessions par cookie.

* Mot de passe : PBKDF2 HMAC SHA 256, sel aléatoire, 240 000 itérations.
* Session : jeton aléatoire remis dans un cookie HttpOnly ; seule son empreinte est en base.
* Protection : 5 essais ratés bloquent la connexion pendant 5 minutes.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from .. import models as m
from ..config import settings

COOKIE = "pei_session"
ITERATIONS = 240_000
MAX_ATTEMPTS = 5
LOCK_MINUTES = 5
USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{3,40}$")


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.status = status


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iterations, salt_b64, digest_b64 = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iterations))
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


def check_password_strength(password: str) -> None:
    if len(password) < 8:
        raise AuthError("Le mot de passe doit contenir au moins 8 caractères.", 400)
    if password.isdigit() or password.isalpha():
        raise AuthError("Le mot de passe doit mêler lettres et chiffres.", 400)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def is_configured(session: Session) -> bool:
    return session.query(m.User).count() > 0


def create_user(session: Session, username: str, password: str, display_name: str | None = None) -> m.User:
    """Création du compte. Un seul compte : PEI est un système personnel."""
    if is_configured(session):
        raise AuthError("Un compte existe déjà.", 409)
    username = username.strip()
    if not USERNAME_RE.match(username):
        raise AuthError("Identifiant : 3 à 40 caractères, lettres, chiffres, point ou souligné.", 400)
    check_password_strength(password)
    user = m.User(username=username, display_name=(display_name or "").strip() or username,
                  password_hash=hash_password(password))
    session.add(user)
    session.commit()
    return user


def login(session: Session, username: str, password: str, user_agent: str | None = None) -> tuple[m.User, str]:
    user = check_credentials(session, username, password)
    now = m.now()
    token = secrets.token_urlsafe(32)
    session.add(m.AuthSession(user_id=user.id, token_hash=_token_hash(token), user_agent=(user_agent or "")[:300],
                              expires_at=now + timedelta(days=settings.session_days)))
    session.query(m.AuthSession).filter(m.AuthSession.expires_at < now).delete()
    session.commit()
    return user, token


def check_credentials(session: Session, username: str, password: str) -> m.User:
    """Vérifie identifiant et mot de passe, avec blocage après plusieurs échecs."""
    user = session.query(m.User).filter(m.User.username == username.strip()).first()
    now = m.now()
    if user is None:
        verify_password(password, hash_password("leurre"))  # même durée de calcul qu'un vrai essai
        raise AuthError("Identifiant ou mot de passe incorrect.")
    if user.locked_until and user.locked_until > now:
        minutes = max(1, int((user.locked_until - now).total_seconds() // 60) + 1)
        raise AuthError(f"Trop d'essais. Réessaie dans {minutes} minute{'s' if minutes > 1 else ''}.", 429)
    if not verify_password(password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= MAX_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            user.failed_attempts = 0
        session.commit()
        raise AuthError("Identifiant ou mot de passe incorrect.")
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    session.commit()
    return user


def user_for_token(session: Session, token: str | None) -> m.User | None:
    if not token:
        return None
    auth = session.query(m.AuthSession).filter(m.AuthSession.token_hash == _token_hash(token)).first()
    now = m.now()
    if auth is None or auth.expires_at < now:
        return None
    if (now - auth.last_seen_at) > timedelta(minutes=5):
        auth.last_seen_at = now
        session.commit()
    return auth.user


def logout(session: Session, token: str | None) -> None:
    if token:
        session.query(m.AuthSession).filter(m.AuthSession.token_hash == _token_hash(token)).delete()
        session.commit()


def change_password(session: Session, user: m.User, current: str, new: str, keep_token: str | None) -> None:
    if not verify_password(current, user.password_hash):
        raise AuthError("Mot de passe actuel incorrect.", 400)
    check_password_strength(new)
    user.password_hash = hash_password(new)
    # Les autres appareils sont déconnectés.
    keep = _token_hash(keep_token) if keep_token else None
    session.query(m.AuthSession).filter(m.AuthSession.user_id == user.id, m.AuthSession.token_hash != keep).delete()
    session.commit()


def reset_password(session: Session, username: str, new: str) -> None:
    """Réinitialisation depuis le PC (ligne de commande), en cas d'oubli."""
    user = session.query(m.User).filter(m.User.username == username).first()
    if user is None:
        raise AuthError("Compte introuvable.", 404)
    check_password_strength(new)
    user.password_hash = hash_password(new)
    user.failed_attempts, user.locked_until = 0, None
    session.query(m.AuthSession).filter(m.AuthSession.user_id == user.id).delete()
    session.commit()


def token_from_request(cookie: str | None, authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return cookie
