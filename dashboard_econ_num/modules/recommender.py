# -*- coding: utf-8 -*-
"""
Modele de recommandations / d'estimation des investissements.

Principe
--------
Pour un territoire (prefecture, region ou national) et un objectif de densite
de service choisi par l'utilisateur, on calcule le nombre de points a creer
pour combler l'ecart, puis le budget correspondant en FCFA et en EUR.

    besoin_mm  = max(0, objectif_mm_pour_1000 * pop/1000   - agents_actuels)
    besoin_ag  = max(0, objectif_ag_pour_100k * pop/100000 - agences_actuelles)
    cout_total = besoin_mm * cout_unitaire_mm + besoin_ag * cout_unitaire_ag
    cout_eur   = cout_total / 655.957   (parite fixe FCFA/EUR)

Les couts unitaires sont des ordres de grandeur parametrables (kit + float +
formation pour un point mobile money ; amenagement d'une agence telecom).
"""
import math

FCFA_PER_EUR = 655.957

# Couts unitaires par defaut (FCFA)
COUT_MM = 250_000       # creation / equipement d'un point agent mobile money
COUT_AGENCE = 15_000_000  # ouverture d'une agence telecom de proximite


def _ceil(x):
    return int(math.ceil(x - 1e-9)) if x > 0 else 0


def compute(pop, n_mm, n_ag, objectif_mm=3.0, objectif_ag=1.5,
            cout_mm=COUT_MM, cout_ag=COUT_AGENCE):
    """Retourne un dict d'estimation pour un territoire."""
    if not pop or pop <= 0:
        pop = 0
    cible_mm = objectif_mm * pop / 1000.0
    cible_ag = objectif_ag * pop / 1e5
    besoin_mm = _ceil(cible_mm - n_mm)
    besoin_ag = _ceil(cible_ag - n_ag)
    cout_fcfa = besoin_mm * cout_mm + besoin_ag * cout_ag
    return {
        "population": int(pop),
        "mm_actuel": int(n_mm),
        "ag_actuel": int(n_ag),
        "mm_pour_1000_actuel": round(n_mm / pop * 1000, 2) if pop else 0,
        "ag_pour_100k_actuel": round(n_ag / pop * 1e5, 2) if pop else 0,
        "objectif_mm": objectif_mm,
        "objectif_ag": objectif_ag,
        "besoin_mm": besoin_mm,
        "besoin_ag": besoin_ag,
        "cout_fcfa": cout_fcfa,
        "cout_eur": round(cout_fcfa / FCFA_PER_EUR, 0),
        "cout_mm_fcfa": besoin_mm * cout_mm,
        "cout_ag_fcfa": besoin_ag * cout_ag,
    }


def fmt_fcfa(v):
    return f"{v:,.0f}".replace(",", " ") + " FCFA"


def fmt_eur(v):
    return f"{v:,.0f}".replace(",", " ") + " €"


def fmt_int(v):
    return f"{v:,.0f}".replace(",", " ")
