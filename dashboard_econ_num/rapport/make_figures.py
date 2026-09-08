# -*- coding: utf-8 -*-
"""Genere les figures analytiques (couleurs drapeau togolais) des rapports."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).parent.parent
DATA = BASE / "data"
FIG = Path(__file__).parent / "figures"
FIG.mkdir(exist_ok=True)

GREEN_DARK, GREEN, YELLOW, RED, GREY = "#0B6E4F", "#008751", "#FFCE00", "#D21034", "#4c5a55"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": "#cfd8d4",
                     "axes.grid": True, "grid.color": "#eef2f0",
                     "figure.autolayout": True})

PREF = pd.read_parquet(DATA / "prefectures.parquet")
REG = pd.read_parquet(DATA / "regions.parquet")
CANT = pd.read_parquet(DATA / "cantons.parquet")
MM = pd.read_parquet(DATA / "points_mobile_money.parquet")
META = json.loads((DATA / "meta.json").read_text())


def save(fig, name):
    p = FIG / name
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("saved", p.name)


# 1. Agents mobile money par region
d = REG.sort_values("n_mobile_money", ascending=False)
fig, ax = plt.subplots(figsize=(7, 3.6))
bars = ax.bar(d["region"], d["n_mobile_money"],
              color=[GREEN, YELLOW, RED, "#5aa17f", "#e0a800"])
ax.set_ylabel("Agents mobile money")
ax.set_title("Agents mobile money par region", color=GREEN_DARK, fontweight="bold")
for b in bars:
    ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
            f"{int(b.get_height()):,}".replace(",", " "), ha="center", va="bottom", fontsize=9)
save(fig, "fig_mm_region.png")

# 2. Repartition agences par operateur (donut)
fig, ax = plt.subplots(figsize=(4.6, 4.6))
vals = [META["n_togocom"], META["n_moov"], META["n_datacenters"]]
ax.pie(vals, labels=[f"Togocom ({vals[0]})", f"Moov ({vals[1]})", f"Datacenters ({vals[2]})"],
       colors=[GREEN, YELLOW, RED], autopct="%1.0f%%", pctdistance=0.8,
       wedgeprops=dict(width=0.42, edgecolor="w"))
ax.set_title("Infrastructures par operateur", color=GREEN_DARK, fontweight="bold")
save(fig, "fig_operateurs.png")

# 3. Densite mm/1000 : 10 mieux vs 10 moins servies
top = PREF.sort_values("mm_pour_1000", ascending=False).head(10)
bot = PREF.sort_values("mm_pour_1000", ascending=True).head(10)
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4))
axes[0].barh(top["prefecture"][::-1], top["mm_pour_1000"][::-1], color=GREEN)
axes[0].set_title("10 prefectures les mieux servies", color=GREEN_DARK, fontweight="bold")
axes[0].set_xlabel("Agents / 1 000 hab.")
axes[1].barh(bot["prefecture"][::-1], bot["mm_pour_1000"][::-1], color=RED)
axes[1].set_title("10 prefectures les moins servies", color=RED, fontweight="bold")
axes[1].set_xlabel("Agents / 1 000 hab.")
for ax in axes:
    ax.axvline(META["mm_pour_1000_national"], color=GREY, ls="--", lw=1)
save(fig, "fig_densite.png")

# 4. Zones blanches par region
g = CANT.groupby("region")["couvert_mm"].agg(total="count", couv="sum")
g["blancs"] = g["total"] - g["couv"]
g = g.sort_values("blancs", ascending=False)
fig, ax = plt.subplots(figsize=(7, 3.6))
ax.bar(g.index, g["couv"], color=GREEN, label="Couverts")
ax.bar(g.index, g["blancs"], bottom=g["couv"], color=RED, label="Zones blanches")
for i, (c, b) in enumerate(zip(g["couv"], g["blancs"])):
    ax.text(i, c + b, str(int(b)), ha="center", va="bottom", fontsize=9, color=RED)
ax.set_ylabel("Nombre de cantons")
ax.set_title("Cantons couverts et zones blanches par region", color=GREEN_DARK, fontweight="bold")
ax.legend()
save(fig, "fig_zones_blanches.png")

# 5. Score de priorite (top 15)
d = PREF.sort_values("score_priorite", ascending=False).head(15)
colors = [RED if v >= 66 else (YELLOW if v >= 45 else GREEN) for v in d["score_priorite"]]
fig, ax = plt.subplots(figsize=(7.5, 4.6))
ax.barh(d["prefecture"][::-1], d["score_priorite"][::-1], color=colors[::-1])
ax.set_xlabel("Score de priorite (0-100)")
ax.set_title("Prefectures prioritaires pour l'investissement numerique",
             color=GREEN_DARK, fontweight="bold")
save(fig, "fig_priorites.png")

# 6. Population 2022 vs 2026 par region
fig, ax = plt.subplots(figsize=(7, 3.6))
d = REG.sort_values("population", ascending=False)
x = range(len(d))
ax.bar([i - 0.2 for i in x], d["population_2022"], width=0.4, color=GREY, label="RGPH-5 2022")
ax.bar([i + 0.2 for i in x], d["population"], width=0.4, color=GREEN, label="Projection 2026")
ax.set_xticks(list(x)); ax.set_xticklabels(d["region"])
ax.set_ylabel("Population")
ax.set_title("Population 2022 vs projection 2026 (taux 2,3 %/an)",
             color=GREEN_DARK, fontweight="bold")
ax.legend()
save(fig, "fig_population.png")

print("Figures OK ->", FIG)
