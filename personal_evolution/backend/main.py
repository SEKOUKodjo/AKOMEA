"""Point d'entrée FastAPI de Personal Evolution Intelligence.

Lancement : python run.py serve   (ou uvicorn backend.main:app --host 0.0.0.0 --port 8000)
Le téléphone ouvre ensuite http://<adresse du PC>:8000 sur le même Wi-Fi.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import icons
from .api import daily, media, planning, statistics
from .api.deps import require_pin
from .config import BASE_DIR, settings
from .db import init_engine

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

protected = [Depends(require_pin)]
for module in (daily, media, planning, statistics):
    app.include_router(module.router, prefix="/api", dependencies=protected)


@app.get("/api/ping", tags=["systeme"])
def ping():
    return {"ok": True, "pin_required": bool(settings.pin)}


@app.get("/api/auth/check", tags=["systeme"])
def auth_check(x_pei_pin: str | None = Header(default=None)):
    require_pin(x_pei_pin)
    return {"ok": True}


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
