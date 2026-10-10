"""Commandes de PEI.

    python run.py serve                 API + interface téléphone sur le port 8000
    python run.py dashboard             tableau de bord Shiny sur le port 8001
    python run.py all                   les deux à la fois
    python run.py demo --db data/demo.db  base de démonstration
    python run.py backup                sauvegarde locale (base et médias)
    python run.py export --days 90      export Excel des données et des indicateurs
    python run.py reindex               reconstruit l'index de la mémoire
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _apply_db(args) -> None:
    if getattr(args, "db", None):
        os.environ["PEI_DB_PATH"] = str(Path(args.db).resolve())
        from backend.config import configure

        configure(db_path=Path(args.db).resolve())


def _banner(port: int) -> None:
    from backend.api.statistics import local_ips

    print("\nPersonal Evolution Intelligence")
    print(f"  Sur ce PC        : http://127.0.0.1:{port}")
    for ip in local_ips():
        print(f"  Sur le téléphone : http://{ip}:{port}   (même réseau Wi-Fi)")
    print(f"  Documentation API: http://127.0.0.1:{port}/docs\n")


def serve(args) -> None:
    import uvicorn

    _apply_db(args)
    _banner(args.port)
    kwargs = {}
    if args.cert and args.key:
        # HTTPS local : permet l'enregistrement direct au micro depuis le navigateur du téléphone.
        kwargs.update(ssl_certfile=args.cert, ssl_keyfile=args.key)
    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=args.reload, **kwargs)


def dashboard(args) -> None:
    _apply_db(args)
    from shiny import run_app

    print(f"\nTableau de bord PEI : http://127.0.0.1:{args.port}\n")
    run_app("dashboard.app:app", host=args.host, port=args.port, app_dir=str(ROOT))


def run_all(args) -> None:
    _apply_db(args)
    env = os.environ.copy()
    dash = subprocess.Popen([sys.executable, str(ROOT / "run.py"), "dashboard", "--host", args.host,
                             "--port", str(args.dashboard_port)], env=env, cwd=ROOT)
    try:
        serve(args)
    finally:
        dash.terminate()


def demo(args) -> None:
    _apply_db(args)
    from backend.config import settings
    from backend.db import init_engine, session_scope
    from backend.services import demo as demo_service

    if settings.database_path.exists() and not args.force:
        sys.exit(f"La base {settings.database_path} existe déjà. Utilisez --force pour la remplacer.")
    if settings.database_path.exists():
        settings.database_path.unlink()
        for suffix in ("-wal", "-shm"):
            Path(str(settings.database_path) + suffix).unlink(missing_ok=True)
    init_engine()
    with session_scope() as session:
        out = demo_service.seed(session, n_days=args.days)
    print(f"Base de démonstration créée : {settings.database_path} ({out['intentions']} intentions)")


def backup(args) -> None:
    _apply_db(args)
    from backend.db import init_engine
    from backend.services import backup as backup_service

    init_engine()
    path = backup_service.create_backup(Path(args.to) if args.to else None, include_media=not args.no_media)
    print(f"Sauvegarde créée : {path}")


def export(args) -> None:
    _apply_db(args)
    from datetime import date, timedelta

    from backend.db import init_engine, session_scope
    from backend.services import export_excel

    init_engine()
    end = date.fromisoformat(args.end) if args.end else (date.today() if args.days or args.start else None)
    start = date.fromisoformat(args.start) if args.start else (end - timedelta(days=args.days - 1) if args.days else None)
    with session_scope() as session:
        content = export_excel.export_bytes(session, start, end)
    out = Path(args.out or export_excel.filename(start, end)).resolve()
    out.write_bytes(content)
    print(f"Export Excel créé : {out}")


def reindex(args) -> None:
    _apply_db(args)
    from backend.db import init_engine, session_scope
    from backend.services import memory

    init_engine()
    with session_scope() as session:
        print(f"{memory.rebuild(session)} éléments indexés")


def main() -> None:
    p = argparse.ArgumentParser(description="Personal Evolution Intelligence")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--db")
    s.add_argument("--reload", action="store_true")
    s.add_argument("--cert", help="certificat TLS local (HTTPS)")
    s.add_argument("--key", help="clé TLS locale")
    s.set_defaults(func=serve)

    d = sub.add_parser("dashboard")
    d.add_argument("--host", default="127.0.0.1")
    d.add_argument("--port", type=int, default=int(os.environ.get("PEI_DASHBOARD_PORT", "8001")))
    d.add_argument("--db")
    d.set_defaults(func=dashboard)

    a = sub.add_parser("all")
    a.add_argument("--host", default="0.0.0.0")
    a.add_argument("--port", type=int, default=8000)
    a.add_argument("--dashboard-port", type=int, default=8001)
    a.add_argument("--db")
    a.add_argument("--reload", action="store_true")
    a.add_argument("--cert")
    a.add_argument("--key")
    a.set_defaults(func=run_all)

    dm = sub.add_parser("demo")
    dm.add_argument("--db", default=str(ROOT / "data" / "demo.db"))
    dm.add_argument("--days", type=int, default=150)
    dm.add_argument("--force", action="store_true")
    dm.set_defaults(func=demo)

    b = sub.add_parser("backup")
    b.add_argument("--db")
    b.add_argument("--to", help="dossier cible, par exemple un disque externe")
    b.add_argument("--no-media", action="store_true")
    b.set_defaults(func=backup)

    x = sub.add_parser("export", help="export Excel des données et des indicateurs")
    x.add_argument("--db")
    x.add_argument("--out", help="fichier .xlsx de sortie")
    x.add_argument("--days", type=int, help="les N derniers jours")
    x.add_argument("--start", help="date de début AAAA-MM-JJ")
    x.add_argument("--end", help="date de fin AAAA-MM-JJ")
    x.set_defaults(func=export)

    r = sub.add_parser("reindex")
    r.add_argument("--db")
    r.set_defaults(func=reindex)

    args = p.parse_args()
    os.chdir(ROOT)
    args.func(args)


if __name__ == "__main__":
    main()
