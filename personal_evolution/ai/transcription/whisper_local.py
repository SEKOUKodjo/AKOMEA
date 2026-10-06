"""Transcription audio entièrement locale.

Utilise faster-whisper si installé, sinon openai-whisper. Si aucun des deux
n'est disponible, l'audio original est conservé et la transcription reste
en attente : rien n'est envoyé sur Internet.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

_lock = threading.Lock()
_model_cache: dict[str, object] = {}


@dataclass
class Transcript:
    text: str
    language: str | None
    engine: str
    segments: list[dict]


def available_engine() -> str | None:
    try:
        import faster_whisper  # noqa: F401

        return "faster-whisper"
    except ImportError:
        pass
    try:
        import whisper  # noqa: F401

        return "openai-whisper"
    except ImportError:
        return None


def transcribe(path: Path | str, model_size: str = "small", language: str | None = "fr") -> Transcript:
    engine = available_engine()
    if engine is None:
        raise RuntimeError(
            "Aucun moteur Whisper local installé. Installez faster-whisper (pip install faster-whisper)."
        )
    path = str(path)
    with _lock:  # un seul modèle chargé, une transcription à la fois
        if engine == "faster-whisper":
            from faster_whisper import WhisperModel

            key = f"fw:{model_size}"
            model = _model_cache.get(key)
            if model is None:
                model = WhisperModel(model_size, device="auto", compute_type="int8")
                _model_cache[key] = model
            segments, info = model.transcribe(path, language=language, vad_filter=True)
            segs = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
            return Transcript(" ".join(s["text"] for s in segs).strip(), info.language, f"{engine}:{model_size}", segs)

        import whisper

        key = f"ow:{model_size}"
        model = _model_cache.get(key)
        if model is None:
            model = whisper.load_model(model_size)
            _model_cache[key] = model
        out = model.transcribe(path, language=language, fp16=False)
        segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
                for s in out.get("segments", [])]
        return Transcript(out.get("text", "").strip(), out.get("language"), f"{engine}:{model_size}", segs)
