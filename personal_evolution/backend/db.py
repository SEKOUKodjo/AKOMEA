"""Connexion SQLite, création du schéma et index plein texte de la mémoire."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base

engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def _sqlite_pragmas(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


def init_engine(url: str | None = None) -> Engine:
    """Crée le moteur, le schéma et l'index de recherche. Idempotent."""
    global engine
    settings.ensure_dirs()
    url = url or settings.database_url
    if engine is not None:
        engine.dispose()
    engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _sqlite_pragmas)
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(engine)
    from .services import memory

    memory.ensure_index(engine)
    return engine


def get_engine() -> Engine:
    return engine or init_engine()


def get_session() -> Iterator[Session]:
    """Dépendance FastAPI."""
    get_engine()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def raw(sql: str, **params):
    with get_engine().connect() as conn:
        return conn.execute(text(sql), params).fetchall()
