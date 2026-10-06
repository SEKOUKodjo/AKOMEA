"""Audio, images, vidéos et documents."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ai.transcription import whisper_local

from .. import models as m
from ..schemas import MediaOut, MediaUpdate
from ..services import media as media_service
from .deps import get_session, not_found

router = APIRouter(tags=["multimedia"])


def _upload(background: BackgroundTasks, session: Session, file: UploadFile, day: date | None, moment: str | None,
            dimension: str | None, caption: str | None, kind: str | None, transcribe: bool) -> m.Media:
    try:
        media = media_service.save_upload(session, file, day=day or date.today(), moment=moment,
                                          dimension=dimension or None, caption=caption or None, kind=kind)
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    if transcribe and media.type in ("audio", "video"):
        background.add_task(media_service.run_transcription, media.id)
    return media


@router.post("/audio", response_model=MediaOut)
def upload_audio(background: BackgroundTasks, file: UploadFile = File(...), day: date | None = Form(None),
                 moment: str | None = Form(None), dimension: str | None = Form(None),
                 caption: str | None = Form(None), session: Session = Depends(get_session)):
    """Enregistre l'audio original puis lance la transcription locale en arrière plan."""
    return _upload(background, session, file, day, moment, dimension, caption, "audio", True)


@router.post("/media", response_model=MediaOut)
def upload_media(background: BackgroundTasks, file: UploadFile = File(...), day: date | None = Form(None),
                 moment: str | None = Form(None), dimension: str | None = Form(None),
                 caption: str | None = Form(None), transcribe: bool = Form(True),
                 session: Session = Depends(get_session)):
    return _upload(background, session, file, day, moment, dimension, caption, None, transcribe)


@router.get("/media", response_model=list[MediaOut])
def list_media(type: str | None = None, start: date | None = None, end: date | None = None,
               limit: int = Query(100, le=2000), session: Session = Depends(get_session)):
    q = session.query(m.Media).outerjoin(m.Day)
    if type:
        q = q.filter(m.Media.type == type)
    if start:
        q = q.filter(m.Day.date >= start)
    if end:
        q = q.filter(m.Day.date <= end)
    return q.order_by(m.Media.created_at.desc()).limit(limit).all()


@router.get("/media/{media_id}", response_model=MediaOut)
def get_media(media_id: int, session: Session = Depends(get_session)):
    media = session.get(m.Media, media_id)
    if media is None:
        raise not_found("Média")
    return media


@router.get("/media/{media_id}/file")
def media_file(media_id: int, session: Session = Depends(get_session)):
    media = session.get(m.Media, media_id)
    if media is None:
        raise not_found("Média")
    path = media_service.absolute_path(media)
    if not path.exists():
        raise not_found("Fichier")
    return FileResponse(path, media_type=media.mime_type, filename=media.original_name)


@router.patch("/media/{media_id}", response_model=MediaOut)
def update_media(media_id: int, body: MediaUpdate, session: Session = Depends(get_session)):
    media = session.get(m.Media, media_id)
    if media is None:
        raise not_found("Média")
    data = body.model_dump(exclude_unset=True)
    if "transcription" in data:
        media.transcription_engine = (media.transcription_engine or "") + "+correction"
        media.transcription_status = "termine"
    for k, v in data.items():
        setattr(media, k, v)
    session.commit()
    return media


@router.post("/media/{media_id}/transcribe", response_model=MediaOut)
def retry_transcription(media_id: int, background: BackgroundTasks, session: Session = Depends(get_session)):
    media = session.get(m.Media, media_id)
    if media is None:
        raise not_found("Média")
    media.transcription_status = "en_attente"
    session.commit()
    background.add_task(media_service.run_transcription, media.id)
    return media


@router.delete("/media/{media_id}")
def delete_media(media_id: int, delete_file: bool = False, session: Session = Depends(get_session)):
    media = session.get(m.Media, media_id)
    if media is None:
        raise not_found("Média")
    media_service.delete_media(session, media, delete_file)
    return {"ok": True}


@router.get("/transcription/status")
def transcription_status():
    engine = whisper_local.available_engine()
    return {"available": engine is not None, "engine": engine}
