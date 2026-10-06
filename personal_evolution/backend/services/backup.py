"""Sauvegardes locales : base SQLite (copie cohérente) et fichiers multimédias."""
from __future__ import annotations

import json
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from ..config import settings


def create_backup(target_dir: Path | None = None, include_media: bool = True) -> Path:
    target_dir = Path(target_dir or settings.backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = target_dir / f"pei_sauvegarde_{stamp}.zip"
    snapshot = target_dir / f".snapshot_{stamp}.db"
    # API de sauvegarde SQLite : copie cohérente même si le serveur tourne.
    src = sqlite3.connect(settings.database_path)
    dst = sqlite3.connect(snapshot)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    n_files = 0
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(snapshot, "data/personal.db")
        if include_media and settings.storage_dir.exists():
            for f in settings.storage_dir.rglob("*"):
                if f.is_file() and f.name != ".gitkeep":
                    zf.write(f, Path("storage") / f.relative_to(settings.storage_dir))
                    n_files += 1
        zf.writestr("manifest.json", json.dumps({
            "created_at": datetime.now().isoformat(timespec="seconds"), "media_files": n_files,
            "database": str(settings.database_path.name), "application": "Personal Evolution Intelligence",
        }, ensure_ascii=False, indent=2))
    snapshot.unlink(missing_ok=True)
    return archive


def list_backups() -> list[dict]:
    if not settings.backup_dir.exists():
        return []
    return [{"name": p.name, "size_mb": round(p.stat().st_size / 1e6, 2),
             "created_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")}
            for p in sorted(settings.backup_dir.glob("pei_sauvegarde_*.zip"), reverse=True)]


def prune(keep: int = 14) -> int:
    files = sorted(settings.backup_dir.glob("pei_sauvegarde_*.zip"), reverse=True)
    for f in files[keep:]:
        f.unlink()
    return max(0, len(files) - keep)
