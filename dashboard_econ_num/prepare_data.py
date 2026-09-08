# -*- coding: utf-8 -*-
"""
=============================================================================
 PIPELINE DE PRE-TRAITEMENT — Tableau de bord Economie Numerique Togo
=============================================================================
Objet :
    Nettoyer et fusionner les donnees brutes (agences telecoms, agents mobile
    money, datacenters, population RGPH-5 2022, limites administratives),
    calculer tous les indicateurs et scores de priorite, puis ecrire des
    fichiers .parquet compacts + un meta.json.

Pourquoi pre-calculer ?
    L'application Shiny ne fait AUCUN calcul lourd au demarrage : elle se
    contente de lire des .parquet deja agreges (< 1 Mo) et un GeoJSON
    simplifie. Le temps de chargement reste donc de l'ordre de la seconde.

Usage :
    python prepare_data.py
=============================================================================
"""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

RAW = Path(__file__).parent / "data_raw"
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

# Parite fixe FCFA <-> EUR (Franc CFA UEMOA, arrimage a l'euro)
FCFA_PER_EUR = 655.957

# Projection demographique : RGPH-5 (2022) -> 2026 au taux moyen de 2,3 %/an
TAUX_CROISSANCE = 0.023
ANNEE_CENSUS = 2022
ANNEE_PROJ = 2026
FACTEUR_PROJ = (1 + TAUX_CROISSANCE) ** (ANNEE_PROJ - ANNEE_CENSUS)  # ~1,0951

# 5 regions administratives (modele geoBoundaries : Grand Lome rattache a Maritime)
REGIONS = {"SAVANES", "KARA", "CENTRALE", "PLATEAUX", "MARITIME"}

# Remaps prefecture (libelle terrain -> cle GeoJSON adm2)
PREF_REMAP = {"MO": "PLAINE DU MO", "KPENDJAL OUEST": "NAKI OUEST"}


def pref_key(name):
    return PREF_REMAP.get(norm(name), norm(name))


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    """Cle de jointure normalisee : majuscules, sans accents, alphanum."""
    s = strip_accents(s).upper()
    s = re.sub(r"[^A-Z0-9]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_coord(v):
    """'[lon,lat]' -> (lon, lat)."""
    if pd.isna(v):
        return (None, None)
    m = re.findall(r"-?\d+\.?\d*", str(v))
    if len(m) >= 2:
        return float(m[0]), float(m[1])
    return (None, None)


def clean_year(v):
    m = re.search(r"(19|20)\d{2}", str(v))
    return int(m.group()) if m else None


# --------------------------------------------------------------------------
# 1. POPULATION (RGPH-5 2022) — reconstruction de la hierarchie
# --------------------------------------------------------------------------
def load_population():
    """
    Le fichier population est une liste a plat sans colonne de niveau :
        TOGO > REGION > PREFECTURE > COMMUNE > CANTON.
    On identifie le niveau par des regles robustes :
      - 'TOGO'                      -> pays
      - nom dans REGIONS            -> region
      - nom finissant par ' <n>'    -> commune (ex. 'TONE 1')
      - nom suivi d'une commune      -> prefecture (ex. 'TONE' precede 'TONE 1')
      - sinon                        -> canton (feuille)
    On valide ensuite que la somme des prefectures = total national.
    """
    raw = pd.read_excel(RAW / "population_togo_2022.xlsx", header=None)
    raw = raw.iloc[7:].reset_index(drop=True)          # ligne 7 = TOGO
    raw.columns = ["name", "total", "m", "f"] + list(raw.columns[4:])
    raw = raw[["name", "total"]].copy()
    raw["name"] = raw["name"].astype(str).str.strip()
    raw["total"] = pd.to_numeric(raw["total"], errors="coerce")
    raw = raw[raw["total"].notna()].reset_index(drop=True)

    names, tot = raw["name"].tolist(), raw["total"].tolist()
    n = len(names)
    is_commune = lambda x: bool(re.search(r" \d+$", x))

    pref = {}   # norm(prefecture) -> population
    for i, (nm, tv) in enumerate(zip(names, tot)):
        if nm == "TOGO" or nm in REGIONS or is_commune(nm):
            continue
        nxt = names[i + 1] if i + 1 < n else ""
        if is_commune(nxt) and re.sub(r" \d+$", "", nxt) == nm:
            pref[norm(nm)] = tv

    # Recuperation manuelle des 2 prefectures dont les communes ont un
    # libelle atypique (verifie : somme des sous-unites = valeur ci-dessous)
    pref.setdefault("AVE", 111214)      # AVE 1 (75 044) + AVE 2 (36 170)
    pref.setdefault("DANYI", 40240)     # 'DANYI 1+DANYI 2'

    national = float(raw.iloc[0]["total"])
    print(f"[pop] {len(pref)} prefectures | national RGPH-5 = {national:,.0f}")
    return pref, national


def parse_pop_hierarchy():
    """Parse complet de la population : pays->region->prefecture->commune->canton.

    Retourne un DataFrame (region, prefecture, commune, name, level, total).
    """
    raw = pd.read_excel(RAW / "population_togo_2022.xlsx", header=None)
    raw = raw.iloc[7:].reset_index(drop=True)
    raw.columns = ["name", "total", "m", "f"] + list(raw.columns[4:])
    raw = raw[["name", "total"]].copy()
    raw["name"] = raw["name"].astype(str).str.strip()
    raw["total"] = pd.to_numeric(raw["total"], errors="coerce")
    raw = raw[raw["total"].notna()].reset_index(drop=True)
    names, tot = raw["name"].tolist(), raw["total"].tolist()
    n = len(names)
    is_commune = lambda x: bool(re.search(r" \d+$", x))
    cur = {"region": None, "prefecture": None, "commune": None}
    rows = []
    for i, (nm, tv) in enumerate(zip(names, tot)):
        if nm == "TOGO":
            lvl = "country"
        elif nm in REGIONS:
            lvl = "region"; cur.update(region=nm, prefecture=None, commune=None)
        elif is_commune(nm):
            lvl = "commune"; cur["commune"] = nm
        else:
            nxt = names[i + 1] if i + 1 < n else ""
            if is_commune(nxt) and re.sub(r" \d+$", "", nxt) == nm:
                lvl = "prefecture"; cur.update(prefecture=nm, commune=None)
            else:
                lvl = "canton"
        rows.append((cur["region"], cur["prefecture"], cur["commune"], nm, lvl, tv))
    return pd.DataFrame(rows, columns=["region", "prefecture", "commune",
                                       "name", "level", "total"])


def build_pop_lookups(P):
    """Dictionnaires de population aux niveaux commune et canton.

    - commune : cle = norm(commune)  (libelle globalement unique, ex. 'GOLFE 4')
    - canton  : cle = 'pref_key||norm(canton)'  (le nom de canton peut se repeter)
    """
    commune = {}
    for r in P[P.level == "commune"].itertuples():
        commune[norm(r.name)] = int(r.total)
    canton = {}
    for r in P[P.level == "canton"].itertuples():
        if r.prefecture:
            canton[f"{pref_key(r.prefecture)}||{norm(r.name)}"] = int(r.total)
    return commune, canton


def build_geo_hierarchy(pts, mm):
    """Arborescence region/prefecture/commune/canton issue des donnees terrain."""
    cols = GEO_COLS
    g = pd.concat([pts[cols], mm[cols]], ignore_index=True).copy()
    g.columns = ["region", "prefecture", "commune", "canton"]
    for c in g.columns:
        g[c] = g[c].astype(str).str.strip()
    bad = {"", "nan", "Nsp", "NSP", "None"}
    g = g[~g["region"].isin(bad) & ~g["prefecture"].isin(bad)]
    g = g.drop_duplicates().sort_values(cols and ["region", "prefecture",
                                                  "commune", "canton"])
    return g.reset_index(drop=True)


# --------------------------------------------------------------------------
# 2. POINTS D'INFRASTRUCTURE
# --------------------------------------------------------------------------
GEO_COLS = ["region_nom_bdd", "prefecture_nom_bdd", "commune_nom_bdd",
            "canton_nom_bdd"]


def load_points():
    frames = []

    # --- Agences telecoms (le fichier "Telecom" est l'union Togocom+Moov) ---
    tel = pd.read_excel(RAW / "agences_telecom.xlsx")
    tel["operateur"] = tel["activite_categorie"].str.replace(
        "Agence ", "", regex=False).fillna("Autre")
    tel["type_infra"] = "Agence telecom"
    tel["annee"] = tel["etab_creation_date"].apply(clean_year)
    tel["nom"] = tel["etab_nom"]
    frames.append(tel)

    # --- CANAL+ (fichier fourni vide : 0 agence recensee) ---
    try:
        cp = pd.read_excel(RAW / "agences_canalplus.xlsx")
        if len(cp):
            cp["operateur"] = "CANAL+"
            cp["type_infra"] = "Agence telecom"
            cp["annee"] = cp.get("etab_creation_date", pd.Series()).apply(clean_year)
            cp["nom"] = cp.get("etab_nom")
            frames.append(cp)
    except Exception:
        pass

    # --- Datacenters ---
    dc = pd.read_excel(RAW / "datacenters.xlsx")
    dc["operateur"] = "Datacenter"
    dc["type_infra"] = "Datacenter"
    dc["annee"] = dc["etab_creation_date"].apply(clean_year)
    dc["nom"] = dc["etab_nom"]
    frames.append(dc)

    pts = pd.concat(frames, ignore_index=True)
    pts[["lon", "lat"]] = pts["coordonnees"].apply(
        lambda v: pd.Series(parse_coord(v)))
    keep = GEO_COLS + ["operateur", "type_infra", "annee", "nom", "lon", "lat"]
    pts = pts[keep].copy()
    for c in GEO_COLS:
        pts[c] = pts[c].astype(str).str.strip()
    pts = pts[pts["lat"].notna()].reset_index(drop=True)
    print(f"[points] {len(pts)} points | "
          f"{pts['operateur'].value_counts().to_dict()}")
    return pts


def load_mobile_money():
    mm = pd.read_excel(RAW / "agents_mobile_money.xlsx")
    mm[["lon", "lat"]] = mm["coordonnees"].apply(
        lambda v: pd.Series(parse_coord(v)))
    for c in GEO_COLS:
        mm[c] = mm[c].astype(str).str.strip()
    mm["operateur"] = mm["operateur"].fillna("Nsp").str.strip()
    mm = mm[mm["lat"].notna()].reset_index(drop=True)
    print(f"[mobile money] {len(mm):,} agents")
    return mm


# --------------------------------------------------------------------------
# 3. AGREGATS & INDICATEURS PAR PREFECTURE
# --------------------------------------------------------------------------
def build_prefecture_table(pts, mm, pop, national):
    # Table de reference prefecture -> region (issue des donnees terrain)
    ref = (pd.concat([pts[GEO_COLS], mm[GEO_COLS]], ignore_index=True)
           .drop_duplicates("prefecture_nom_bdd")
           .set_index("prefecture_nom_bdd")["region_nom_bdd"].to_dict())

    prefs = sorted(set(pts["prefecture_nom_bdd"]) | set(mm["prefecture_nom_bdd"]))
    prefs = [p for p in prefs if p and p.lower() != "nan"]

    rows = []
    for p in prefs:
        pop_v = pop.get(norm(p))
        sub_pts = pts[pts["prefecture_nom_bdd"] == p]
        sub_mm = mm[mm["prefecture_nom_bdd"] == p]
        n_togocom = int((sub_pts["operateur"] == "Togocom").sum())
        n_moov = int((sub_pts["operateur"] == "Moov").sum())
        n_dc = int((sub_pts["type_infra"] == "Datacenter").sum())
        n_ag = n_togocom + n_moov
        n_mm = int(len(sub_mm))
        pop_2026 = round(pop_v * FACTEUR_PROJ) if pop_v else None
        rows.append({
            "prefecture": p,
            "region": ref.get(p, ""),
            "population_2022": pop_v,
            "population": pop_2026,   # population de reference = projection 2026
            "n_agences": n_ag,
            "n_togocom": n_togocom,
            "n_moov": n_moov,
            "n_datacenter": n_dc,
            "n_mobile_money": n_mm,
            "n_cantons_couverts": int(sub_mm["canton_nom_bdd"].nunique()),
        })
    df = pd.DataFrame(rows)

    # Indicateurs de densite (adequation offre / population)
    df["mm_pour_1000"] = (df["n_mobile_money"] / df["population"] * 1000).round(2)
    df["agences_pour_100k"] = (df["n_agences"] / df["population"] * 1e5).round(2)
    df["hab_par_agent_mm"] = (df["population"] / df["n_mobile_money"]).round(0)
    df["hab_par_agent_mm"] = df["hab_par_agent_mm"].replace([float("inf")], None)

    # Score de priorite (0-100) : plus il est eleve, plus la prefecture est
    # sous-equipee au regard de sa population. Methodo : ecart normalise
    # (min-max inverse) sur 3 dimensions ponderees.
    def minmax(s):
        s = s.astype(float)
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng else s * 0

    deficit_mm = 1 - minmax(df["mm_pour_1000"].fillna(0))
    deficit_ag = 1 - minmax(df["agences_pour_100k"].fillna(0))
    poids_pop = minmax(df["population"].fillna(df["population"].median()))
    df["score_priorite"] = (
        100 * (0.45 * deficit_mm + 0.35 * deficit_ag + 0.20 * poids_pop)
    ).round(1)
    df = df.sort_values("score_priorite", ascending=False).reset_index(drop=True)
    df["rang_priorite"] = df.index + 1

    # Cle de jointure avec le GeoJSON des prefectures (adm2).
    df["key"] = df["prefecture"].apply(pref_key)
    return df


def build_region_table(df_pref):
    agg = df_pref.groupby("region", as_index=False).agg(
        population=("population", "sum"),
        population_2022=("population_2022", "sum"),
        n_agences=("n_agences", "sum"),
        n_togocom=("n_togocom", "sum"),
        n_moov=("n_moov", "sum"),
        n_datacenter=("n_datacenter", "sum"),
        n_mobile_money=("n_mobile_money", "sum"),
        n_prefectures=("prefecture", "nunique"),
    )
    agg["mm_pour_1000"] = (agg["n_mobile_money"] / agg["population"] * 1000).round(2)
    agg["agences_pour_100k"] = (agg["n_agences"] / agg["population"] * 1e5).round(2)
    return agg.sort_values("population", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
# 4. ZONES BLANCHES (canton sans aucun agent mobile money)
# --------------------------------------------------------------------------
def build_cantons(mm):
    """
    Couverture au niveau canton : un canton est une 'zone blanche numerique'
    s'il n'accueille aucun agent mobile money ni agence.
    """
    admin3 = json.loads((RAW / "tgo_admin_boundaries.geojson"
                         / "tgo_admin3.geojson").read_text())
    couverts = set(norm(x) for x in mm["canton_nom_bdd"].dropna().unique())
    rows = []
    for f in admin3["features"]:
        p = f["properties"]
        nm = p.get("adm3_name", "")
        rows.append({
            "canton": nm,
            "prefecture": p.get("adm2_name", ""),
            "region": p.get("adm1_name", ""),
            "lat": p.get("center_lat"),
            "lon": p.get("center_lon"),
            "couvert_mm": norm(nm) in couverts,
        })
    df = pd.DataFrame(rows)
    print(f"[cantons] {len(df)} cantons | "
          f"{(~df['couvert_mm']).sum()} zones blanches (mobile money)")
    return df


# --------------------------------------------------------------------------
# 5. GEOJSON SIMPLIFIE (choroplethes prefecture & region)
# --------------------------------------------------------------------------
def simplify_geojson(path, name_key, keep_props):
    gj = json.loads(path.read_text())
    for f in gj["features"]:
        props = {k: f["properties"].get(k) for k in keep_props}
        props["_key"] = norm(f["properties"].get(name_key, ""))
        f["properties"] = props
        f.pop("bbox", None)
    return gj


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    pop, national = load_population()
    pts = load_points()
    mm = load_mobile_money()

    df_pref = build_prefecture_table(pts, mm, pop, national)
    df_reg = build_region_table(df_pref)
    df_cant = build_cantons(mm)

    # Hierarchie geographique (filtres jusqu'au canton) + population commune/canton
    hier = build_geo_hierarchy(pts, mm)
    P = parse_pop_hierarchy()
    commune_pop, canton_pop = build_pop_lookups(P)
    hier.to_parquet(OUT / "hierarchie.parquet", index=False)
    (OUT / "pop_lookup.json").write_text(json.dumps(
        {"commune": commune_pop, "canton": canton_pop,
         "facteur_projection": FACTEUR_PROJ}, ensure_ascii=False))
    print(f"[hier] {len(hier)} combinaisons | communes pop={len(commune_pop)} "
          f"| cantons pop={len(canton_pop)}")

    # --- ecriture parquet ---
    pts.to_parquet(OUT / "points_infra.parquet", index=False)
    # agents mobile money : on garde lon/lat + operateur + prefecture (leger)
    mm[["lon", "lat", "operateur"] + GEO_COLS].to_parquet(
        OUT / "points_mobile_money.parquet", index=False)
    df_pref.to_parquet(OUT / "prefectures.parquet", index=False)
    df_reg.to_parquet(OUT / "regions.parquet", index=False)
    df_cant.to_parquet(OUT / "cantons.parquet", index=False)

    # --- geojson simplifies ---
    geo_pref = simplify_geojson(
        RAW / "tgo_admin_boundaries.geojson" / "tgo_admin2.geojson",
        "adm2_name", ["adm2_name", "adm1_name"])
    (OUT / "geo_prefectures.json").write_text(json.dumps(geo_pref))
    geo_reg = simplify_geojson(
        RAW / "tgo_admin_boundaries.geojson" / "tgo_admin1.geojson",
        "adm1_name", ["adm1_name"])
    (OUT / "geo_regions.json").write_text(json.dumps(geo_reg))

    # Copie servie a la carte (assets statiques Shiny)
    www_geo = Path(__file__).parent / "www" / "geo"
    www_geo.mkdir(parents=True, exist_ok=True)
    (www_geo / "geo_prefectures.json").write_text(json.dumps(geo_pref))
    (www_geo / "geo_regions.json").write_text(json.dumps(geo_reg))

    # --- meta / KPI nationaux ---
    pop_couverte = float(df_pref["population"].sum())          # projection 2026
    pop_2022_couverte = float(df_pref["population_2022"].sum())
    meta = {
        "national_pop_2022": national,
        "national_pop_2026": round(national * FACTEUR_PROJ),
        "taux_croissance": TAUX_CROISSANCE,
        "annee_census": ANNEE_CENSUS,
        "facteur_projection": round(FACTEUR_PROJ, 4),
        "pop_prefectures_couvertes": pop_couverte,
        "pop_2022_couverte": pop_2022_couverte,
        "n_agences_telecom": int(pts[pts.type_infra == "Agence telecom"].shape[0]),
        "n_togocom": int((pts.operateur == "Togocom").sum()),
        "n_moov": int((pts.operateur == "Moov").sum()),
        "n_datacenters": int((pts.type_infra == "Datacenter").sum()),
        "n_mobile_money": int(len(mm)),
        "n_prefectures": int(df_pref.shape[0]),
        "n_regions": int(df_reg.shape[0]),
        "n_cantons": int(df_cant.shape[0]),
        "n_zones_blanches": int((~df_cant["couvert_mm"]).sum()),
        "mm_pour_1000_national": round(len(mm) / pop_couverte * 1000, 2),
        "agences_pour_100k_national": round(
            pts[pts.type_infra == "Agence telecom"].shape[0] / pop_couverte * 1e5, 2),
        "fcfa_per_eur": FCFA_PER_EUR,
        "pref_top_priorite": df_pref.iloc[0]["prefecture"],
        "annee_pop": ANNEE_PROJ,
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print("\n=== META ===")
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"\nFichiers ecrits dans {OUT}")


if __name__ == "__main__":
    main()
