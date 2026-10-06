"""Stockage des fichiers multimédias et transcription en arrière plan."""
from __future__ import annotations

import hashlib
import mimetypes
import re
from datetime import date, datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ai.transcription import whisper_local

from .. import models as m
from ..config import settings
from ..db import session_scope
from . import days as day_service

_EXT_TYPES = {
    "audio": {".mp3", ".m4a", ".wav", ".ogg", ".oga", ".opus", ".aac", ".flac", ".webm", ".amr", ".3gp"},
    "video": {".mp4", ".mov", ".mkv", ".avi", ".webm", ".3gp", ".m4v"},
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp"},
}


def guess_type(filename: str, content_type: str | None) -> str:
    if content_type:
        major = content_type.split("/")[0]
        if major in ("audio", "video", "image"):
            return major
    ext = Path(filename).suffix.lower()
    for kind, exts in _EXT_TYPES.items():
        if ext in exts:
            return kind
    return "document"


def _safe_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._]+", "_", Path(name).stem)[:60] or "fichier"
    return stem + Path(name).suffix.lower()[:8]


def save_upload(session: Session, upload: UploadFile, *, day: date | None, moment: str | None,
                dimension: str | None, caption: str | None, kind: str | None = None) -> m.Media:
    """Écrit le fichier original dans storage/ et ses métadonnées dans SQLite."""
    filename = upload.filename or "fichier"
    media_type = kind or guess_type(filename, upload.content_type)
    folder = settings.media_dir(media_type) / (day or date.today()).strftime("%Y/%m")
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = folder / f"{stamp}_{_safe_name(filename)}"

    digest = hashlib.sha256()
    size = 0
    limit = settings.max_upload_mb * 1024 * 1024
    with target.open("wb") as out:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                out.close()
                target.unlink(missing_ok=True)
                raise ValueError(f"Fichier trop volumineux (limite {settings.max_upload_mb} Mo)")
            digest.update(chunk)
            out.write(chunk)

    day_obj = day_service.get_or_create(session, day) if day else None
    media = m.Media(
        day_id=day_obj.id if day_obj else None, type=media_type, moment=moment, dimension=dimension,
        file_path=str(target.relative_to(settings.storage_dir)), original_name=filename,
        mime_type=upload.content_type or mimetypes.guess_type(filename)[0], size_bytes=size,
        sha256=digest.hexdigest(), caption=caption,
        transcription_status="en_attente" if media_type in ("audio", "video") else None,
    )
    session.add(media)
    session.flush()
    if media_type in ("audio", "video"):
        source = m.Source(day_id=media.day_id, kind=media_type, moment=moment, media_id=media.id)
        session.add(source)
    session.commit()
    return media


def absolute_path(media: m.Media) -> Path:
    return settings.storage_dir / media.file_path


def run_transcription(media_id: int) -> None:
    """Tâche de fond : transcrit l'audio et range le texte, sans toucher au fichier original."""
    with session_scope() as session:
        media = session.get(m.Media, media_id)
        if media is None:
            return
        if whisper_local.available_engine() is None:
            media.transcription_status = "indisponible"
            media.transcription_error = "Aucun moteur Whisper local installé (pip install faster-whisper)."
            return
        media.transcription_status = "en_cours"
        path = absolute_path(media)
    try:
        result = whisper_local.transcribe(path, settings.whisper_model, settings.whisper_language)
    except Exception as exc:  # noqa: BLE001
        with session_scope() as session:
            media = session.get(m.Media, media_id)
            media.transcription_status = "erreur"
            media.transcription_error = str(exc)[:1000]
        return
    with session_scope() as session:
        media = session.get(m.Media, media_id)
        media.transcription = result.text
        media.transcription_engine = result.engine
        media.transcription_status = "termine"
        media.transcription_error = None
        source = session.query(m.Source).filter_by(media_id=media_id).first()
        if source is not None and not source.raw_text:
            source.raw_text = result.text


def delete_media(session: Session, media: m.Media, delete_file: bool = False) -> None:
    if delete_file:
        absolute_path(media).unlink(missing_ok=True)
    session.query(m.Source).filter_by(media_id=media.id).update({"media_id": None})
    session.delete(media)
    session.commit()


