"""Photo de profil affichée sur la page de connexion et dans l'en tête.

Pour mettre ta propre photo, deux possibilités :
* depuis l'application : Réglages, puis Changer la photo ;
* à la main : déposer un fichier photo.jpg (ou .png, .webp) dans data/profil/.
Sans photo personnelle, l'image frontend/profil/photo_par_defaut.png est utilisée.
"""
from __future__ import annotations

import io
from pathlib import Path

from fastapi import UploadFile

from ..config import BASE_DIR, settings
from ..i18n import tr

DEFAULT_PHOTO = BASE_DIR / "frontend" / "profil" / "photo_par_defaut.png"
NAMES = ("photo.jpg", "photo.jpeg", "photo.png", "photo.webp")
MAX_MB = 15


def photo_path() -> Path:
    for name in NAMES:
        p = settings.profile_dir / name
        if p.exists():
            return p
    return DEFAULT_PHOTO


def is_custom() -> bool:
    return photo_path() != DEFAULT_PHOTO


def save_photo(upload: UploadFile) -> Path:
    from PIL import Image, ImageOps, UnidentifiedImageError

    data = upload.file.read(MAX_MB * 1024 * 1024 + 1)
    if len(data) > MAX_MB * 1024 * 1024:
        raise ValueError(tr("Photo trop lourde (limite {n} Mo).", n=MAX_MB))
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)  # respecte l'orientation prise par le téléphone
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(tr("Ce fichier n'est pas une image lisible.")) from exc
    # Recadrage carré centré, puis réduction : la photo est affichée en rond.
    side = min(img.size)
    left, top = (img.width - side) // 2, (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((min(side, 800),) * 2)
    remove_photo()
    settings.profile_dir.mkdir(parents=True, exist_ok=True)
    target = settings.profile_dir / "photo.jpg"
    img.convert("RGB").save(target, "JPEG", quality=88)
    return target


def remove_photo() -> None:
    for name in NAMES:
        (settings.profile_dir / name).unlink(missing_ok=True)


def photo_bytes() -> tuple[bytes, str]:
    p = photo_path()
    mime = {".png": "image/png", ".webp": "image/webp"}.get(p.suffix.lower(), "image/jpeg")
    return p.read_bytes(), mime


def generate_default(path: Path = DEFAULT_PHOTO) -> None:
    """Image de remplacement : silhouette sur fond vert, aux couleurs du Togo."""
    from PIL import Image, ImageDraw, ImageFilter

    size = 600
    img = Image.new("RGB", (size, size), "#006A4E")
    draw = ImageDraw.Draw(img)
    for y in range(size):  # léger dégradé vertical
        shade = int(30 * y / size)
        draw.line([(0, y), (size, y)], fill=(0, 106 - shade // 2, 78 - shade // 2))
    sil = Image.new("L", (size, size), 0)
    sd = ImageDraw.Draw(sil)
    sd.ellipse((200, 120, 400, 330), fill=255)                 # tête
    sd.ellipse((95, 370, 505, 760), fill=255)                  # épaules
    sil = sil.filter(ImageFilter.GaussianBlur(1.2))
    img.paste(Image.new("RGB", (size, size), "#E8F2EE"), (0, 0), sil)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, size - 26, size, size), fill="#FFCE00")  # liseré jaune
    draw.rectangle((0, size - 26, size // 3, size), fill="#D21034")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
