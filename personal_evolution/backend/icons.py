"""Bibliothèque d'icônes de PEI, dessinées et générées en Python.

Aucune icône externe et aucun emoji : chaque pictogramme est un tracé SVG
défini ici, servi au téléphone sous forme de sprite (/icons.svg) et inséré
directement dans le tableau de bord Shiny.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape

# Couleurs du drapeau togolais.
TOGO_GREEN = "#006A4E"
TOGO_YELLOW = "#FFCE00"
TOGO_RED = "#D21034"
TOGO_WHITE = "#FFFFFF"

ICONS: dict[str, str] = {
    "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9.5h13V10"/><path d="M10 19.5v-5h4v5"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    "moon": '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/>',
    "flag": '<path d="M5 21V4"/><path d="M5 4h12l-2.5 4L17 12H5"/>',
    "star": '<path d="M12 3.2l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.7l-5.4 3 1.2-6-4.5-4.2 6.1-.7z"/>',
    "star_fill": '<path fill="currentColor" stroke="none" d="M12 3.2l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.7l-5.4 3 1.2-6-4.5-4.2 6.1-.7z"/>',
    "chart": '<path d="M4 4v16h16"/><path d="M8 16v-4M12 16V8M16 16v-6M20 16V5"/>',
    "gauge": '<path d="M3.5 17a8.5 8.5 0 1 1 17 0"/><path d="M12 17l4-5.5"/><circle cx="12" cy="17" r="1.3" fill="currentColor"/>',
    "trend_up": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "trend_down": '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>',
    "book": '<path d="M4 19V5a2 2 0 0 1 2-2h14v14H6a2 2 0 0 0-2 2zm0 0a2 2 0 0 0 2 2h14"/><path d="M8.5 7.5h7"/>',
    "cross": '<path d="M12 3v18M7 8.5h10"/>',
    "pulse": '<path d="M3 12h4l2-5 4 10 2-5h6"/>',
    "briefcase": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M3 12.5h18"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8"/><path d="M18 14a6.5 6.5 0 0 1 3.5 6"/>',
    "music": '<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
    "download": '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.8"/><path d="M21 16l-5-5L5 20"/>',
    "video": '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3"/>',
    "file": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20.5 20.5 16 16"/>',
    "check": '<path d="M4.5 12.5l5 5L19.5 7"/>',
    "check_circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
    "half_circle": '<circle cx="12" cy="12" r="9"/><path fill="currentColor" d="M12 3a9 9 0 0 1 0 18z"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "x_circle": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "skip": '<path d="M5 5l9 7-9 7z"/><path d="M18 5v14"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6"/><path d="M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    "save": '<path d="M5 3h11l4 4v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 1-2z"/><path d="M8 3v5h7V3M8 21v-7h8v7"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="6.5"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    "shield": '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "bulb": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    "flask": '<path d="M9 3h6M10 3v6L4.5 18.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3"/><path d="M7 15h10"/>',
    "compass": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
    "arrow_left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "arrow_right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "chevron_right": '<path d="M9 6l6 6-6 6"/>',
    "chevron_left": '<path d="M15 6l-6 6 6 6"/>',
    "chevron_down": '<path d="M6 9l6 6 6-6"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "alert": '<path d="M12 3.5 2.5 20h19z"/><path d="M12 10v4.5M12 17.2v.3"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.7v.3"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7L11.5 6.8"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1.5-1.5"/>',
    "graduation": '<path d="M2.5 9 12 4.5 21.5 9 12 13.5z"/><path d="M6.5 11v5c3 2.5 8 2.5 11 0v-5M21.5 9v5"/>',
    "archive": '<rect x="3" y="4" width="18" height="4.5" rx="1"/><path d="M5 8.5V19a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19V8.5M10 12.5h4"/>',
    "grid": '<rect x="4" y="4" width="6.5" height="6.5" rx="1.2"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.2"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.2"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.2"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>',
    "refresh": '<path d="M20 11a8 8 0 0 0-14.5-4.5L3.5 9"/><path d="M3.5 4v5h5"/><path d="M4 13a8 8 0 0 0 14.5 4.5l2-2.5"/><path d="M20.5 20v-5h-5"/>',
    "play": '<path d="M7 4.5v15l12-7.5z"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5"/><path d="M9 2.5v3.5M15 2.5v3.5M9 18v3.5M15 18v3.5M2.5 9h3.5M2.5 15h3.5M18 9h3.5M18 15h3.5"/>',
    "heart": '<path d="M12 20s-7.5-4.6-9-9.3C2 7.3 4.3 4.5 7.3 4.5c2 0 3.6 1.1 4.7 2.8 1.1-1.7 2.7-2.8 4.7-2.8 3 0 5.3 2.8 4.3 6.2-1.5 4.7-9 9.3-9 9.3z"/>',
    "message": '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>',
    "sliders": '<path d="M5 4v16M12 4v16M19 4v16"/><circle cx="5" cy="14" r="2.2" fill="currentColor"/><circle cx="12" cy="8" r="2.2" fill="currentColor"/><circle cx="19" cy="15" r="2.2" fill="currentColor"/>',
    "bed": '<path d="M3 19V6M3 15h18v4M21 15v-3a3 3 0 0 0-3-3h-7v6"/><circle cx="7" cy="11" r="2"/>',
    "zap": '<path d="M13 2.5 4.5 13.5H12l-1 8 8.5-11H12z"/>',
    "smile": '<circle cx="12" cy="12" r="9"/><path d="M8 14.5a5 5 0 0 0 8 0"/><path d="M9 9.5v.5M15 9.5v.5"/>',
    "monitor": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8.5 20h7M12 16v4"/>',
    "droplet": '<path d="M12 3s6.5 7 6.5 11.5a6.5 6.5 0 0 1-13 0C5.5 10 12 3 12 3z"/>',
    "wifi": '<path d="M2.5 9a14 14 0 0 1 19 0M5.5 12.5a9.5 9.5 0 0 1 13 0M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="19.5" r="1" fill="currentColor"/>',
    "layers": '<path d="M12 3 2.5 8 12 13l9.5-5z"/><path d="M2.5 12.5 12 17.5l9.5-5M2.5 16.5 12 21.5l9.5-5"/>',
    "route": '<circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="6" r="2.5"/><path d="M8.5 18H16a3 3 0 0 0 0-6H8a3 3 0 0 1 0-6h7.5"/>',
    "hourglass": '<path d="M6 3h12M6 21h12M7 3c0 5 5 6 5 9s-5 4-5 9M17 3c0 5-5 6-5 9s5 4 5 9"/>',
    "scale": '<path d="M12 3v18M6 21h12M5 7h14"/><path d="M5 7l-3 7a3.5 3.5 0 0 0 6 0zM19 7l-3 7a3.5 3.5 0 0 0 6 0z"/>',
    "spark": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
}

ALIASES = {"dove": "cross", "spirituel": "cross", "physique": "pulse", "etudes": "book",
           "professionnel": "briefcase", "personnel": "user", "relationnel": "users", "loisirs": "music",
           "vision": "star"}


def _resolve(name: str) -> str:
    name = ALIASES.get(name, name)
    return name if name in ICONS else "info"


@lru_cache(maxsize=1)
def sprite() -> str:
    symbols = "".join(
        f'<symbol id="i-{name}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</symbol>'
        for name, body in ICONS.items()
    )
    aliases = "".join(
        f'<symbol id="i-{alias}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{ICONS[target]}</symbol>'
        for alias, target in ALIASES.items()
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" style="display:none">{symbols}{aliases}</svg>'


def svg(name: str, size: int = 20, color: str = "currentColor", cls: str = "pei-icon", title: str | None = None) -> str:
    """Icône SVG autonome, prête à insérer dans du HTML (tableau de bord Shiny)."""
    label = f"<title>{escape(title)}</title>" if title else ""
    return (
        f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="{str(not title).lower()}" '
        f'style="color:{color};vertical-align:middle">{label}{ICONS[_resolve(name)]}</svg>'
    )


def logo_svg(size: int = 64, rounded: bool = True) -> str:
    """Emblème PEI : bandes vertes et jaunes, canton rouge et étoile blanche du drapeau togolais."""
    stripes = "".join(
        f'<rect x="0" y="{i * 12.8:.1f}" width="64" height="12.8" fill="{TOGO_GREEN if i % 2 == 0 else TOGO_YELLOW}"/>'
        for i in range(5)
    )
    star = ("M19.2 9.5l2.9 6.2 6.8.8-5 4.6 1.3 6.7-6-3.3-6 3.3 1.3-6.7-5-4.6 6.8-.8z")
    rx = 14 if rounded else 0
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><clipPath id="pei-clip"><rect width="64" height="64" rx="{rx}"/></clipPath></defs>'
        f'<g clip-path="url(#pei-clip)">{stripes}<rect width="38.4" height="38.4" fill="{TOGO_RED}"/>'
        f'<path d="{star}" fill="{TOGO_WHITE}"/></g>'
        f'<path d="M30 55 L40 44 L47 49 L58 34" fill="none" stroke="{TOGO_WHITE}" stroke-width="3.2" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/></svg>'
    )


def _star_points(cx: float, cy: float, r_out: float, r_in: float) -> list[tuple[float, float]]:
    import math

    pts = []
    for k in range(10):
        r = r_out if k % 2 == 0 else r_in
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _inside(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


@lru_cache(maxsize=4)
def png_icon(size: int = 192, maskable: bool = False) -> bytes:
    """Icône PNG de l'application (écran d'accueil du téléphone), rastérisée en pur Python."""
    import struct
    import zlib

    def hex_rgb(h: str) -> tuple[int, int, int]:
        return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)

    green, yellow, red, white = (hex_rgb(c) for c in (TOGO_GREEN, TOGO_YELLOW, TOGO_RED, TOGO_WHITE))
    pad = 0.1 if maskable else 0.0
    canton = 0.6
    star = _star_points(0.3, 0.315, 0.2, 0.08)
    sx0, sx1 = min(p[0] for p in star), max(p[0] for p in star)
    sy0, sy1 = min(p[1] for p in star), max(p[1] for p in star)
    rows = []
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            acc = [0, 0, 0]
            for oy, ox in ((0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)):
                u = (px + ox) / size
                v = (py + oy) / size
                # zone utile, réduite pour les icônes adaptatives
                uu, vv = (u - pad) / (1 - 2 * pad), (v - pad) / (1 - 2 * pad)
                if maskable and not (0 <= uu <= 1 and 0 <= vv <= 1):
                    col = green
                elif uu < canton and vv < canton:
                    inside = sx0 <= uu <= sx1 and sy0 <= vv <= sy1 and _inside(uu, vv, star)
                    col = white if inside else red
                else:
                    col = green if int(min(max(vv, 0), 0.9999) * 5) % 2 == 0 else yellow
                acc[0] += col[0]
                acc[1] += col[1]
                acc[2] += col[2]
            row += bytes(c // 4 for c in acc)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
