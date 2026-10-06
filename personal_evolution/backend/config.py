"""Configuration locale de PEI.

Toutes les valeurs peuvent être surchargées par des variables d'environnement,
ce qui permet de séparer clairement les données du code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _path(env: str, default: Path) -> Path:
    value = os.environ.get(env)
    return Path(value).expanduser().resolve() if value else default


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: _path("PEI_DATA_DIR", BASE_DIR / "data"))
    storage_dir: Path = field(default_factory=lambda: _path("PEI_STORAGE_DIR", BASE_DIR / "storage"))
    backup_dir: Path = field(default_factory=lambda: _path("PEI_BACKUP_DIR", BASE_DIR / "backups"))
    db_path: Path | None = field(default_factory=lambda: _path("PEI_DB_PATH", Path()) if os.environ.get("PEI_DB_PATH") else None)
    # Code PIN facultatif. Vide = pas d'authentification (réseau local de confiance).
    pin: str | None = field(default_factory=lambda: os.environ.get("PEI_PIN") or None)
    whisper_model: str = field(default_factory=lambda: os.environ.get("PEI_WHISPER_MODEL", "small"))
    whisper_language: str = field(default_factory=lambda: os.environ.get("PEI_WHISPER_LANG", "fr"))
    dashboard_port: int = field(default_factory=lambda: int(os.environ.get("PEI_DASHBOARD_PORT", "8001")))
    max_upload_mb: int = field(default_factory=lambda: int(os.environ.get("PEI_MAX_UPLOAD_MB", "500")))

    @property
    def database_path(self) -> Path:
        return self.db_path or (self.data_dir / "personal.db")

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    def media_dir(self, kind: str) -> Path:
        folder = {"audio": "audio", "video": "video", "image": "images"}.get(kind, "documents")
        path = self.storage_dir / folder
        path.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.storage_dir, self.backup_dir, self.database_path.parent):
            p.mkdir(parents=True, exist_ok=True)
        for kind in ("audio", "video", "image", "document"):
            self.media_dir(kind)


settings = Settings()


def configure(**overrides) -> Settings:
    """Remplace la configuration courante (utile pour les tests et la démo)."""
    global settings
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings
