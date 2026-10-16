"""Point d'entrée FastAPI de Personal Evolution Intelligence.

Lancement : python run.py serve   (ou uvicorn backend.main:app --host 0.0.0.0 --port 8000)
Le téléphone ouvre ensuite http://<adresse du PC>:8000 sur le même Wi-Fi.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import i18n, icons
from .api import account, daily, media, planning, statistics
from .api.deps import current_user
from .config import BASE_DIR
from .db import init_engine
from .services import profile

FRONTEND = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_engine()
    yield


app = FastAPI(
    title="Personal Evolution Intelligence",
    description="Mémoire personnelle longitudinale : Intention, Action, Résultat. Entièrement locale.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1024)


class LanguageMiddleware:
    """Fixe la langue de chaque requête : en tête X-PEI-Lang, cookie pei_lang, puis langue du navigateur."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            cookies = {}
            for part in headers.get("cookie", "").split(";"):
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    cookies[k] = v
            lang = (headers.get("x-pei-lang") or cookies.get(i18n.COOKIE)
                    or i18n.from_accept_language(headers.get("accept-language")))
            with i18n.use(lang):
                await self.inner(scope, receive, send)
        else:
            await self.inner(scope, receive, send)


app.add_middleware(LanguageMiddleware)

# Toutes les données exigent une session ouverte ; seules la connexion et la photo sont publiques.
protected = [Depends(current_user)]
for module in (daily, media, planning, statistics):
    app.include_router(module.router, prefix="/api", dependencies=protected)
app.include_router(account.router)


@app.get("/api/ping", tags=["systeme"])
def ping():
    return {"ok": True}


@app.get("/profil/photo", include_in_schema=False)
def profile_photo():
    """Photo affichée sur la page de connexion et dans l'en tête (publique, comme sur un écran de verrouillage)."""
    data, mime = profile.photo_bytes()
    return Response(data, media_type=mime, headers={"Cache-Control": "no-cache"})


@app.get("/icons.svg", include_in_schema=False)
def icon_sprite():
    return Response(icons.sprite(), media_type="image/svg+xml", headers={"Cache-Control": "max-age=86400"})


@app.get("/icons/logo.svg", include_in_schema=False)
def logo():
    return Response(icons.logo_svg(256), media_type="image/svg+xml")


@app.get("/icons/icon-{size}.png", include_in_schema=False)
def app_icon(size: int, maskable: bool = False):
    size = size if size in (48, 72, 96, 144, 180, 192, 256, 384, 512) else 192
    return Response(icons.png_icon(size, maskable), media_type="image/png", headers={"Cache-Control": "max-age=604800"})


@app.get("/service-worker.js", include_in_schema=False)
def service_worker():
    # Servi à la racine pour couvrir toute l'application.
    return FileResponse(FRONTEND / "service-worker.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})


@app.get("/manifest.json", include_in_schema=False)
def manifest():
    return FileResponse(FRONTEND / "manifest.json", media_type="application/manifest+json")


@app.get("/", include_in_schema=False)
def index():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html.replace("<!--ICON_SPRITE-->", icons.sprite()), headers={"Cache-Control": "no-cache"})


app.mount("/src", StaticFiles(directory=FRONTEND / "src"), name="src")
