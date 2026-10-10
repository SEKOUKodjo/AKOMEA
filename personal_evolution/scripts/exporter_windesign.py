"""Exporte le schéma de PEI en script SQL (MySQL) pour la rétroconception dans WinDesign.

    python scripts/exporter_windesign.py

Produit docs/windesign/pei_windesign_mysql.sql. Chaque clé étrangère porte le nom
de l'association Merise (FK_PREVOIR, FK_DECOMPOSER...) et chaque table et colonne
porte un commentaire en français, afin que WinDesign reconstitue un MCD lisible.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy.dialects import mysql  # noqa: E402

from backend.models import Base  # noqa: E402
from scripts.generer_mcd import ASSOS, DESC, ENTITIES  # noqa: E402

OUT = ROOT / "docs" / "windesign" / "pei_windesign_mysql.sql"
DIALECT = mysql.dialect()


def q(text: str) -> str:
    return text.replace("'", "''")


def column_sql(table: str, col) -> str:
    typ = col.type.compile(dialect=DIALECT)
    if typ == "JSON":
        typ = "TEXT"  # meilleure compatibilité avec les anciennes versions de WinDesign
    parts = [f"  {col.name} {typ}"]
    if col.primary_key:
        parts.append("NOT NULL AUTO_INCREMENT")
    elif not col.nullable:
        parts.append("NOT NULL")
    else:
        parts.append("NULL")
    desc = DESC.get(table, {}).get(col.name)
    if desc:
        parts.append(f"COMMENT '{q(desc)}'")
    return " ".join(parts)


def build() -> str:
    lines = [
        "-- Personal Evolution Intelligence (PEI)",
        "-- Script SQL pour la rétroconception dans WinDesign (SGBD cible : MySQL)",
        f"-- Généré le {date.today():%d/%m/%Y} à partir de backend/models.py",
        "-- 15 tables, 17 associations. Chaque clé étrangère porte le nom de l'association du MCD.",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]
    for table, (entity, role) in ENTITIES.items():
        t = Base.metadata.tables[table]
        cols = [column_sql(table, c) for c in t.columns]
        cols.append("  PRIMARY KEY (id)")
        for c in t.columns:
            if c.unique:
                cols.append(f"  UNIQUE KEY UK_{table.upper()}_{c.name.upper()} ({c.name})")
        lines.append(f"-- Entité {entity} : {role}")
        lines.append(f"CREATE TABLE {table} (")
        lines.append(",\n".join(cols))
        lines.append(f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{q(entity + ' : ' + role)}';")
        lines.append("")

    lines.append("-- Associations du MCD (une clé étrangère par association)")
    for a in ASSOS:
        table, column = a.fk.split(".")
        ref = a.a if table == a.b else a.b
        on_delete = "CASCADE" if "1,1" in (a.card_a, a.card_b) else "SET NULL"
        lines.append(f"-- {a.name} : {ENTITIES[a.a][0]} ({a.card_a}) / {ENTITIES[a.b][0]} ({a.card_b}). {a.meaning}")
        lines.append(f"ALTER TABLE {table} ADD CONSTRAINT FK_{a.name} FOREIGN KEY ({column}) "
                     f"REFERENCES {ref} (id) ON DELETE {on_delete};")
        if a.name == "CONCERNER":
            lines.append("-- Remarque : dans l'application, ce lien est polymorphe (subject_type, subject_id) ;")
            lines.append("-- il est déclaré ici vers INTENTION pour que WinDesign affiche l'association du MCD.")
        lines.append("")
    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)} écrit")


if __name__ == "__main__":
    main()
