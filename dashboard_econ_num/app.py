# -*- coding: utf-8 -*-
"""
=============================================================================
  Tableau de bord — Acces aux telecommunications & services numeriques au Togo
  Data Challenge Environnement / Economie Numerique — Togo AI Lab
  Auteur : Maurice Kodjo SEKOU — Shiny for Python + Highcharts / Highmaps
=============================================================================
Chargement optimise : l'application lit uniquement des .parquet pre-agreges
(voir prepare_data.py). Aucun calcul lourd au demarrage.
"""
import json
from pathlib import Path

import pandas as pd
from shiny import App, reactive, render, ui

from modules import theme as T
from modules import recommender as R

# --------------------------------------------------------------------------
# DONNEES (pre-calculees)
# --------------------------------------------------------------------------
DATA = Path(__file__).parent / "data"
PREF = pd.read_parquet(DATA / "prefectures.parquet")
REG = pd.read_parquet(DATA / "regions.parquet")
CANT = pd.read_parquet(DATA / "cantons.parquet")
PTS = pd.read_parquet(DATA / "points_infra.parquet")
MM = pd.read_parquet(DATA / "points_mobile_money.parquet")
META = json.loads((DATA / "meta.json").read_text())

REGIONS = ["Toutes"] + sorted(PREF["region"].dropna().unique().tolist())
FCFA = R.FCFA_PER_EUR


def nf(v, dec=0):
    """Format nombre a la francaise (espace comme separateur de milliers)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return (f"{v:,.{dec}f}").replace(",", " ").replace(".", ",")


# ==========================================================================
#  INTERFACE
# ==========================================================================
NAV = [
    ("accueil", "🏠 Accueil"),
    ("infra", "🏢 Infrastructures"),
    ("services", "📶 Services numeriques"),
    ("couverture", "🛰️ Zones blanches"),
    ("priorites", "📊 Priorites"),
    ("reco", "💡 Recommandations"),
    ("carte", "🗺️ Carte"),
    ("auteur", "👤 Auteur"),
]


def topbar():
    navbtns = "".join(
        f'<button class="navlink{" active" if v=="accueil" else ""}" '
        f'id="nav_{v}" onclick="selTab(\'{v}\',this)">{lbl}</button>'
        for v, lbl in NAV)
    return ui.HTML(f"""
    <div class="topbar">
      <div class="gov-banner">
        <div class="ph logo-ph">Logo<br/>Togo AI Lab</div>
        <div class="gov-titles">
          <div class="t1">REPUBLIQUE TOGOLAISE</div>
          <div class="t2">TRAVAIL &nbsp;-&nbsp; LIBERTE &nbsp;-&nbsp; PATRIE</div>
          <div class="t3">MINISTERE DE L'ECONOMIE NUMERIQUE ET DE LA TRANSFORMATION DIGITALE</div>
          <div class="t4">Tableau de bord d'aide a la decision — Acces aux telecommunications &amp; services numeriques</div>
        </div>
        <div class="ph crest-ph">Armoiries</div>
      </div>
      <div class="flag-band"></div>
      <div class="appbar">
        <div class="brand">📡 SAD Economie Numerique</div>
        {navbtns}
      </div>
    </div>
    <script>
    function selTab(v, el){{
      Shiny.setInputValue('active_tab', v, {{priority:'event'}});
      document.querySelectorAll('.appbar .navlink').forEach(function(b){{
         b.classList.remove('active'); }});
      if(el) el.classList.add('active');
    }}
    // Ajuste dynamiquement le decalage du contenu a la hauteur reelle de la
    // barre fixe (qui peut occuper 1 ou 2 lignes selon la largeur d'ecran).
    function fitTop(){{
      var tb=document.querySelector('.topbar'); if(!tb) return;
      var h=tb.offsetHeight;
      document.querySelectorAll('.app-body').forEach(function(e){{
         e.style.paddingTop=(h+14)+'px'; }});
      document.querySelectorAll('.sidebar').forEach(function(e){{
         e.style.top=(h+10)+'px'; }});
    }}
    window.addEventListener('resize', fitTop);
    document.addEventListener('shiny:connected', function(){{
       setTimeout(fitTop,60); setTimeout(fitTop,400); }});
    </script>
    """)


def sidebar():
    return ui.div(
        ui.h4("🔎 NIVEAU D'ANALYSE"),
        ui.input_select("f_region", "Region", REGIONS, selected="Toutes"),
        ui.input_select("f_pref", "Prefecture", ["Toutes"], selected="Toutes"),
        ui.input_action_button("reset", "Tout le Togo", class_="btn",
                               style=f"width:100%;background:{T.YELLOW};"
                                     f"border:none;font-weight:800;color:{T.INK};"
                                     "margin-top:6px;border-radius:8px;padding:8px;"),
        ui.hr(),
        ui.p(ui.HTML("<b>Sources</b><br/>geodata.gouv.tg · RGPH-5 (2022) · "
                     "geoBoundaries"), style="font-size:11px;color:#6b7b76;"),
        ui.p(ui.HTML(f"Population projetee <b>{META['annee_pop']}</b> "
                     f"(taux {META['taux_croissance']*100:.1f}%/an)"),
             style="font-size:11px;color:#6b7b76;"),
        class_="sidebar")


def panel(title, *body):
    return ui.div(ui.div(ui.HTML(title), class_="ph-head"), *body, class_="panel")


app_ui = ui.page_fluid(
    T.head_deps(),
    topbar(),
    ui.div(
        sidebar(),
        ui.div(
            ui.navset_hidden(
                ui.nav_panel(None, ui.output_ui("tab_accueil"), value="accueil"),
                ui.nav_panel(None, ui.output_ui("tab_infra"), value="infra"),
                ui.nav_panel(None, ui.output_ui("tab_services"), value="services"),
                ui.nav_panel(None, ui.output_ui("tab_couverture"), value="couverture"),
                ui.nav_panel(None, ui.output_ui("tab_priorites"), value="priorites"),
                ui.nav_panel(None, ui.output_ui("tab_reco"), value="reco"),
                ui.nav_panel(None, ui.output_ui("tab_carte"), value="carte"),
                ui.nav_panel(None, ui.output_ui("tab_auteur"), value="auteur"),
                id="tab", selected="accueil",
            ),
            class_="content"),
        class_="app-body"),
    title="SAD Economie Numerique — Togo",
)


# ==========================================================================
#  SERVEUR
# ==========================================================================
def server(input, output, session):

    # ------- navigation (barre fixe) -------
    @reactive.effect
    @reactive.event(input.active_tab)
    async def _switch():
        ui.update_navset("tab", selected=input.active_tab())
        await session.send_custom_message("reflow", {})

    # ------- filtres -------
    @reactive.effect
    @reactive.event(input.f_region)
    def _upd_pref():
        reg = input.f_region()
        if reg == "Toutes":
            opts = ["Toutes"] + sorted(PREF["prefecture"].tolist())
        else:
            opts = ["Toutes"] + sorted(
                PREF[PREF.region == reg]["prefecture"].tolist())
        ui.update_select("f_pref", choices=opts, selected="Toutes")

    @reactive.effect
    @reactive.event(input.reset)
    def _reset():
        ui.update_select("f_region", selected="Toutes")
        ui.update_select("f_pref", choices=["Toutes"], selected="Toutes")

    @reactive.calc
    def scope():
        """DataFrame prefectures filtre selon la selection."""
        df = PREF
        if input.f_region() != "Toutes":
            df = df[df.region == input.f_region()]
        if input.f_pref() != "Toutes":
            df = df[df.prefecture == input.f_pref()]
        return df

    @reactive.calc
    def scope_label():
        if input.f_pref() != "Toutes":
            return f"Prefecture : {input.f_pref()}"
        if input.f_region() != "Toutes":
            return f"Region : {input.f_region()}"
        return "Tout le Togo"

    # ==================================================================
    #  ONGLET ACCUEIL
    # ==================================================================
    @render.ui
    def tab_accueil():
        d = scope()
        pop = int(d["population"].sum())
        n_ag = int(d["n_agences"].sum())
        n_mm = int(d["n_mobile_money"].sum())
        n_dc = int(d["n_datacenter"].sum())
        mm1000 = round(n_mm / pop * 1000, 2) if pop else 0
        ag100k = round(n_ag / pop * 1e5, 2) if pop else 0

        kpis = ui.HTML(f"""
        <div class="kpi-row">
          <div class="kpi green"><div class="v">{nf(n_mm)}</div>
            <div class="l">Agents mobile money</div><div class="s">Points de service</div></div>
          <div class="kpi green2"><div class="v">{nf(n_ag)}</div>
            <div class="l">Agences telecoms</div><div class="s">Togocom + Moov</div></div>
          <div class="kpi yellow"><div class="v">{nf(mm1000,2)}</div>
            <div class="l">Agents / 1 000 hab.</div><div class="s">Inclusion financiere</div></div>
          <div class="kpi grey"><div class="v">{nf(n_dc)}</div>
            <div class="l">Datacenters</div><div class="s">Centres de donnees</div></div>
          <div class="kpi green"><div class="v">{nf(pop)}</div>
            <div class="l">Population {META['annee_pop']}</div><div class="s">Estimation</div></div>
          <div class="kpi red"><div class="v">{nf(META['n_zones_blanches'])}</div>
            <div class="l">Zones blanches</div><div class="s">Cantons sans agent</div></div>
        </div>""")

        return ui.TagList(
            ui.div(ui.HTML(f"<span class='badge' style='background:{T.GREEN_DARK}'>"
                           f"{scope_label()}</span>"), style="margin-bottom:10px;"),
            kpis,
            ui.div(
                panel("📶 Agents mobile money par region", ui.output_ui("acc_mm_region")),
                panel("🏢 Agences telecoms par operateur", ui.output_ui("acc_ag_op")),
                class_="grid-2"),
            ui.div(
                panel("⚖️ Adequation offre / population (agents pour 1 000 hab.)",
                      ui.output_ui("acc_adequation")),
                panel("🗺️ Densite mobile money par prefecture", ui.output_ui("acc_map")),
                class_="grid-2"),
        )

    @render.ui
    def acc_mm_region():
        d = REG.sort_values("n_mobile_money", ascending=False)
        return T.highchart({
            "chart": {"type": "column"},
            "title": {"text": None},
            "xAxis": {"categories": d["region"].tolist()},
            "yAxis": {"title": {"text": "Agents"}},
            "tooltip": {"pointFormat": "<b>{point.y:,.0f}</b> agents"},
            "plotOptions": {"column": {"colorByPoint": True, "borderRadius": 3}},
            "series": [{"name": "Agents mobile money", "data": d["n_mobile_money"].tolist()}],
        }, height=300)

    @render.ui
    def acc_ag_op():
        d = scope()
        return T.highchart({
            "chart": {"type": "pie"},
            "title": {"text": None},
            "tooltip": {"pointFormat": "<b>{point.y}</b> ({point.percentage:.0f} %)"},
            "plotOptions": {"pie": {"innerSize": "55%", "dataLabels":
                {"format": "{point.name}: {point.y}"}}},
            "series": [{"name": "Agences", "colorByPoint": True, "data": [
                {"name": "Togocom", "y": int(d["n_togocom"].sum()), "color": T.GREEN},
                {"name": "Moov", "y": int(d["n_moov"].sum()), "color": T.YELLOW},
                {"name": "Datacenters", "y": int(d["n_datacenter"].sum()), "color": T.RED},
            ]}],
        }, height=300)

    @render.ui
    def acc_adequation():
        d = scope().sort_values("mm_pour_1000", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "bar"},
            "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist()},
            "yAxis": {"title": {"text": "Agents / 1 000 hab."},
                      "plotLines": [{"value": META["mm_pour_1000_national"],
                                     "color": T.RED, "width": 2, "dashStyle": "Dash",
                                     "label": {"text": "Moyenne nationale",
                                               "style": {"color": T.RED}}}]},
            "tooltip": {"pointFormat": "<b>{point.y:.2f}</b> / 1 000 hab."},
            "plotOptions": {"bar": {"color": T.GREEN, "borderRadius": 2}},
            "series": [{"name": "Agents / 1 000 hab.", "data": d["mm_pour_1000"].round(2).tolist()}],
        }, height=380)

    @render.ui
    def acc_map():
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.mm_pour_1000)}
                for r in PREF.itertuples()]
        return T.highmap(vals, title="", subtitle="Agents pour 1 000 hab.",
                         value_suffix=" / 1000", height=380)

    # ==================================================================
    #  ONGLET INFRASTRUCTURES
    # ==================================================================
    @render.ui
    def tab_infra():
        return ui.TagList(
            ui.div(ui.HTML(f"<span class='badge' style='background:{T.GREEN_DARK}'>"
                           f"Repartition spatiale des infrastructures — {scope_label()}"
                           "</span>"), style="margin-bottom:10px;"),
            panel("🗺️ Localisation des agences telecoms &amp; datacenters",
                  ui.output_ui("infra_map")),
            ui.div(
                panel("🏢 Agences par prefecture (Top 15)", ui.output_ui("infra_bar")),
                panel("📅 Anciennete des agences (annee de creation)",
                      ui.output_ui("infra_timeline")),
                class_="grid-2"),
            panel("🖥️ Concentration des centres de donnees",
                  ui.output_ui("infra_dc_note")),
        )

    @render.ui
    def infra_map():
        reg = input.f_region()
        pts = PTS
        if reg != "Toutes":
            pts = pts[pts.region_nom_bdd == reg]
        colors = {"Togocom": T.GREEN, "Moov": T.YELLOW, "Datacenter": T.RED}
        points = [{"name": f"{r.nom} ({r.operateur})", "lon": float(r.lon),
                   "lat": float(r.lat), "color": colors.get(r.operateur, T.GREEN_DARK)}
                  for r in pts.itertuples() if pd.notna(r.lon)]
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.n_agences)}
                for r in PREF.itertuples()]
        return T.highmap(vals, title="", subtitle="Fond : nb d'agences — points : sites",
                         points=points, value_suffix=" agences", height=520)

    @render.ui
    def infra_bar():
        d = PTS[PTS.type_infra == "Agence telecom"]
        if input.f_region() != "Toutes":
            d = d[d.region_nom_bdd == input.f_region()]
        g = (d.groupby(["prefecture_nom_bdd", "operateur"]).size()
             .unstack(fill_value=0))
        for op in ["Togocom", "Moov"]:
            if op not in g:
                g[op] = 0
        g["tot"] = g.sum(axis=1)
        g = g.sort_values("tot", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": g.index.tolist()},
            "yAxis": {"title": {"text": "Nombre d'agences"}, "stackLabels": {"enabled": True}},
            "plotOptions": {"series": {"stacking": "normal", "borderRadius": 2}},
            "tooltip": {"shared": True},
            "series": [{"name": "Togocom", "data": g["Togocom"].tolist(), "color": T.GREEN},
                       {"name": "Moov", "data": g["Moov"].tolist(), "color": T.YELLOW}],
        }, height=420)

    @render.ui
    def infra_timeline():
        d = PTS[(PTS.type_infra == "Agence telecom") & PTS.annee.notna()]
        if input.f_region() != "Toutes":
            d = d[d.region_nom_bdd == input.f_region()]
        g = d.groupby("annee").size().sort_index()
        g = g.cumsum()
        return T.highchart({
            "chart": {"type": "area"}, "title": {"text": None},
            "xAxis": {"categories": [int(x) for x in g.index.tolist()]},
            "yAxis": {"title": {"text": "Agences cumulees"}},
            "tooltip": {"pointFormat": "<b>{point.y}</b> agences (cumul)"},
            "plotOptions": {"area": {"color": T.GREEN, "fillColor": "rgba(0,135,81,.18)",
                                     "marker": {"enabled": False}}},
            "series": [{"name": "Agences (cumul)", "data": g.tolist()}],
        }, height=420)

    @render.ui
    def infra_dc_note():
        d = PTS[PTS.type_infra == "Datacenter"]
        rows = "".join(
            f"<tr><td>{r.nom}</td><td>{r.prefecture_nom_bdd}</td>"
            f"<td>{r.commune_nom_bdd}</td><td>{int(r.annee) if pd.notna(r.annee) else '—'}</td></tr>"
            for r in d.itertuples())
        return ui.HTML(
            f"<p style='color:#6b7b76;font-size:13px'>Les <b>{len(d)} datacenters</b> "
            "recenses sont tous situes dans le <b>Grand Lome (prefecture du Golfe)</b> — "
            "une concentration extreme qui constitue un risque de resilience et un frein "
            "a la deconcentration numerique du territoire.</p>"
            f"<table class='reco'><tr><th>Etablissement</th><th>Prefecture</th>"
            f"<th>Commune</th><th>Annee</th></tr>{rows}</table>")

    # ==================================================================
    #  ONGLET SERVICES NUMERIQUES (mobile money)
    # ==================================================================
    @render.ui
    def tab_services():
        return ui.TagList(
            ui.div(ui.HTML(f"<span class='badge' style='background:{T.GREEN_DARK}'>"
                           f"Couverture des services numeriques — {scope_label()}</span>"),
                   style="margin-bottom:10px;"),
            ui.div(
                panel("🗺️ Densite d'agents mobile money (pour 1 000 hab.)",
                      ui.output_ui("srv_map")),
                panel("🥧 Repartition des agents par operateur",
                      ui.output_ui("srv_op")),
                class_="grid-2"),
            ui.div(
                panel("🔝 Prefectures les mieux servies", ui.output_ui("srv_top")),
                panel("🔻 Prefectures les moins servies", ui.output_ui("srv_bottom")),
                class_="grid-2"),
            panel("👥 Habitants par agent (accessibilite) — plus la barre est haute, "
                  "moins le service est accessible", ui.output_ui("srv_hab")),
        )

    @render.ui
    def srv_map():
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.mm_pour_1000)}
                for r in PREF.itertuples()]
        return T.highmap(vals, title="", subtitle="Agents / 1 000 hab.",
                         value_suffix=" / 1000", height=420)

    @render.ui
    def srv_op():
        g = MM.groupby("operateur").size().sort_values(ascending=False)
        data = [{"name": k, "y": int(v)} for k, v in g.items()]
        return T.highchart({
            "chart": {"type": "pie"}, "title": {"text": None},
            "tooltip": {"pointFormat": "<b>{point.y:,.0f}</b> ({point.percentage:.1f} %)"},
            "plotOptions": {"pie": {"innerSize": "50%", "colorByPoint": True,
                            "dataLabels": {"format": "{point.name}: {point.percentage:.0f} %"}}},
            "series": [{"name": "Agents", "data": data}],
        }, height=420)

    @render.ui
    def srv_top():
        d = scope().sort_values("mm_pour_1000", ascending=False).head(10)
        return _rank_bar(d, "mm_pour_1000", "Agents / 1 000 hab.", T.GREEN)

    @render.ui
    def srv_bottom():
        d = scope().sort_values("mm_pour_1000", ascending=True).head(10)
        return _rank_bar(d, "mm_pour_1000", "Agents / 1 000 hab.", T.RED)

    def _rank_bar(d, col, label, color):
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist()},
            "yAxis": {"title": {"text": label}},
            "tooltip": {"pointFormat": "<b>{point.y:.2f}</b>"},
            "plotOptions": {"bar": {"color": color, "borderRadius": 2}},
            "series": [{"name": label, "data": d[col].round(2).tolist()}],
        }, height=360)

    @render.ui
    def srv_hab():
        d = scope().dropna(subset=["hab_par_agent_mm"]).sort_values(
            "hab_par_agent_mm", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "column"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist(), "labels": {"rotation": -45}},
            "yAxis": {"title": {"text": "Habitants / agent"}},
            "tooltip": {"pointFormat": "<b>{point.y:,.0f}</b> hab. par agent"},
            "plotOptions": {"column": {"color": T.RED, "borderRadius": 2}},
            "series": [{"name": "Habitants / agent", "data": d["hab_par_agent_mm"].tolist()}],
        }, height=340)

    # ==================================================================
    #  ONGLET COUVERTURE & ZONES BLANCHES
    # ==================================================================
    @render.ui
    def tab_couverture():
        tot = len(CANT)
        blancs = int((~CANT.couvert_mm).sum())
        taux = round((tot - blancs) / tot * 100, 1)
        return ui.TagList(
            ui.HTML(f"""<div class="kpi-row">
              <div class="kpi green"><div class="v">{nf(tot-blancs)}</div>
                <div class="l">Cantons couverts</div><div class="s">au moins 1 agent</div></div>
              <div class="kpi red"><div class="v">{nf(blancs)}</div>
                <div class="l">Zones blanches</div><div class="s">aucun agent mobile money</div></div>
              <div class="kpi yellow"><div class="v">{nf(taux,1)} %</div>
                <div class="l">Taux de couverture</div><div class="s">cantons desservis</div></div>
              <div class="kpi grey"><div class="v">{nf(tot)}</div>
                <div class="l">Cantons (total)</div><div class="s">decoupage adm3</div></div>
            </div>"""),
            ui.div(
                panel("🛰️ Zones blanches par region", ui.output_ui("cov_bar")),
                panel("🗺️ Cartographie des zones blanches", ui.output_ui("cov_map")),
                class_="grid-2"),
            panel("📋 Liste des cantons non desservis (zones blanches)",
                  ui.output_ui("cov_table")),
        )

    @render.ui
    def cov_bar():
        g = CANT.groupby("region")["couvert_mm"].agg(
            total="count", couverts="sum")
        g["blancs"] = g["total"] - g["couverts"]
        g = g.sort_values("blancs", ascending=False)
        return T.highchart({
            "chart": {"type": "column"}, "title": {"text": None},
            "xAxis": {"categories": g.index.tolist()},
            "yAxis": {"title": {"text": "Nombre de cantons"}, "stackLabels": {"enabled": True}},
            "plotOptions": {"column": {"stacking": "normal", "borderRadius": 2}},
            "tooltip": {"shared": True},
            "series": [
                {"name": "Couverts", "data": g["couverts"].astype(int).tolist(), "color": T.GREEN},
                {"name": "Zones blanches", "data": g["blancs"].astype(int).tolist(), "color": T.RED}],
        }, height=380)

    @render.ui
    def cov_map():
        d = CANT[(~CANT.couvert_mm) & CANT.lon.notna()]
        if input.f_region() != "Toutes":
            d = d[d.region == input.f_region()]
        points = [{"name": f"{r.canton} ({r.prefecture})", "lon": float(r.lon),
                   "lat": float(r.lat), "color": T.RED} for r in d.itertuples()]
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.n_mobile_money)}
                for r in PREF.itertuples()]
        return T.highmap(vals, title="", subtitle="Points rouges = cantons sans agent",
                         points=points, value_suffix=" agents", height=380)

    @render.ui
    def cov_table():
        d = CANT[~CANT.couvert_mm].copy()
        if input.f_region() != "Toutes":
            d = d[d.region == input.f_region()]
        d = d.sort_values(["region", "prefecture", "canton"])
        rows = "".join(f"<tr><td>{r.canton}</td><td>{r.prefecture}</td>"
                       f"<td>{r.region}</td></tr>" for r in d.itertuples())
        return ui.HTML(f"<div style='max-height:340px;overflow:auto'>"
                       f"<table class='reco'><tr><th>Canton</th><th>Prefecture</th>"
                       f"<th>Region</th></tr>{rows}</table></div>")

    # ==================================================================
    #  ONGLET PRIORITES
    # ==================================================================
    @render.ui
    def tab_priorites():
        return ui.TagList(
            ui.div(ui.HTML(f"<span class='badge' style='background:{T.RED}'>"
                   "Score de priorite = deficit d'offre pondere par la population"
                   " (0 a 100)</span>"), style="margin-bottom:10px;"),
            ui.div(
                panel("📊 Classement des prefectures prioritaires",
                      ui.output_ui("prio_bar")),
                panel("🗺️ Carte des priorites", ui.output_ui("prio_map")),
                class_="grid-2"),
            panel("📋 Tableau de priorisation", ui.output_ui("prio_table")),
        )

    @render.ui
    def prio_bar():
        d = scope().sort_values("score_priorite", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist()},
            "yAxis": {"title": {"text": "Score de priorite"}, "max": 100},
            "tooltip": {"pointFormat": "Score : <b>{point.y:.1f}</b>/100"},
            "plotOptions": {"bar": {"colorByPoint": True, "borderRadius": 2}},
            "colorAxis": False,
            "series": [{"name": "Score", "data": [
                {"y": float(v), "color": T.RED if v >= 66 else (T.YELLOW if v >= 45 else T.GREEN)}
                for v in d["score_priorite"]]}],
        }, height=440)

    @render.ui
    def prio_map():
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.score_priorite)}
                for r in PREF.itertuples()]
        return T.highmap(vals, title="", subtitle="Score de priorite (0-100)",
                         scale=T.PRIORITY_SCALE, value_suffix=" /100", height=440)

    @render.ui
    def prio_table():
        d = scope().sort_values("rang_priorite").copy()
        rows = ""
        for r in d.itertuples():
            col = T.RED if r.score_priorite >= 66 else (T.YELLOW if r.score_priorite >= 45 else T.GREEN)
            rows += (f"<tr><td>{r.rang_priorite}</td><td><b>{r.prefecture}</b></td>"
                     f"<td>{r.region}</td><td>{nf(r.population)}</td>"
                     f"<td>{nf(r.n_mobile_money)}</td><td>{nf(r.mm_pour_1000,2)}</td>"
                     f"<td>{nf(r.n_agences)}</td>"
                     f"<td><span class='badge' style='background:{col}'>"
                     f"{nf(r.score_priorite,1)}</span></td></tr>")
        return ui.HTML(f"<div style='max-height:420px;overflow:auto'>"
                       "<table class='reco'><tr><th>Rang</th><th>Prefecture</th>"
                       "<th>Region</th><th>Population</th><th>Agents MM</th>"
                       "<th>MM/1000</th><th>Agences</th><th>Score</th></tr>"
                       f"{rows}</table></div>")

    # ==================================================================
    #  ONGLET RECOMMANDATIONS (interactif)
    # ==================================================================
    @render.ui
    def tab_reco():
        return ui.TagList(
            ui.div(ui.HTML(f"<span class='badge' style='background:{T.GREEN_DARK}'>"
                   "Simulateur d'investissement — choisissez un territoire et un objectif"
                   "</span>"), style="margin-bottom:10px;"),
            panel("🎛️ Parametres de simulation",
                ui.div(
                    ui.input_select("r_pref", "Territoire (prefecture)",
                                    ["Tout le Togo"] + sorted(PREF["prefecture"].tolist())),
                    ui.input_slider("r_obj_mm", "Objectif : agents mobile money / 1 000 hab.",
                                    1.0, 8.0, 3.0, step=0.5),
                    ui.input_slider("r_obj_ag", "Objectif : agences telecoms / 100 000 hab.",
                                    0.5, 5.0, 1.5, step=0.5),
                    ui.input_numeric("r_cout_mm", "Cout unitaire agent MM (FCFA)",
                                     R.COUT_MM, step=50000),
                    ui.input_numeric("r_cout_ag", "Cout unitaire agence (FCFA)",
                                     R.COUT_AGENCE, step=1000000),
                    style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;")),
            ui.output_ui("reco_result"),
            panel("💰 Budget d'investissement par prefecture prioritaire (objectif choisi)",
                  ui.output_ui("reco_chart")),
            panel("📋 Plan d'investissement detaille", ui.output_ui("reco_table")),
        )

    @reactive.calc
    def reco_params():
        return (input.r_obj_mm(), input.r_obj_ag(),
                input.r_cout_mm() or R.COUT_MM, input.r_cout_ag() or R.COUT_AGENCE)

    @render.ui
    def reco_result():
        obj_mm, obj_ag, c_mm, c_ag = reco_params()
        sel = input.r_pref()
        if sel == "Tout le Togo":
            pop = int(PREF["population"].sum()); n_mm = int(PREF["n_mobile_money"].sum())
            n_ag = int(PREF["n_agences"].sum()); titre = "Tout le Togo"
        else:
            r = PREF[PREF.prefecture == sel].iloc[0]
            pop, n_mm, n_ag = int(r.population), int(r.n_mobile_money), int(r.n_agences)
            titre = f"Prefecture : {sel}"
        e = R.compute(pop, n_mm, n_ag, obj_mm, obj_ag, c_mm, c_ag)
        return ui.HTML(f"""
        <div class="reco-card">
          <h3 style="margin:0 0 8px;color:{T.GREEN_DARK}">🎯 {titre}</h3>
          <p style="margin:0 0 10px;font-size:13px;color:#41524c">
            Population {META['annee_pop']} : <b>{nf(pop)}</b> hab. —
            offre actuelle : <b>{nf(n_mm)}</b> agents MM ({e['mm_pour_1000_actuel']} /1000),
            <b>{nf(n_ag)}</b> agences ({e['ag_pour_100k_actuel']} /100k).</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:12px">
            <div class="reco-card" style="border-color:{T.GREEN}">
              <div class="reco-num">+{nf(e['besoin_mm'])}</div>
              <div>agents mobile money a creer<br/><small>pour atteindre {obj_mm} /1000 hab.</small></div></div>
            <div class="reco-card" style="border-color:{T.YELLOW}">
              <div class="reco-num">+{nf(e['besoin_ag'])}</div>
              <div>agences telecoms a ouvrir<br/><small>pour atteindre {obj_ag} /100k hab.</small></div></div>
          </div>
          <div class="invest-box">
            <div class="b fcfa"><div>Investissement total</div>
              <div class="amt">{R.fmt_fcfa(e['cout_fcfa'])}</div></div>
            <div class="b eur"><div>Equivalent euros</div>
              <div class="amt">{R.fmt_eur(e['cout_eur'])}</div>
              <div style="font-size:11px;opacity:.8">parite 1 € = {FCFA} FCFA</div></div>
          </div>
        </div>""")

    @reactive.calc
    def reco_plan():
        obj_mm, obj_ag, c_mm, c_ag = reco_params()
        recs = []
        for r in PREF.itertuples():
            e = R.compute(int(r.population), int(r.n_mobile_money), int(r.n_agences),
                          obj_mm, obj_ag, c_mm, c_ag)
            e["prefecture"] = r.prefecture; e["region"] = r.region
            e["rang"] = int(r.rang_priorite)
            recs.append(e)
        return pd.DataFrame(recs)

    @render.ui
    def reco_chart():
        d = reco_plan().sort_values("cout_fcfa", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist()},
            "yAxis": {"title": {"text": "Investissement (millions FCFA)"}},
            "tooltip": {"pointFormatter": None,
                        "pointFormat": "<b>{point.y:,.0f}</b> M FCFA"},
            "plotOptions": {"bar": {"color": T.GREEN_DARK, "borderRadius": 2}},
            "series": [{"name": "Investissement (M FCFA)",
                        "data": (d["cout_fcfa"] / 1e6).round(1).tolist()}],
        }, height=440)

    @render.ui
    def reco_table():
        d = reco_plan().sort_values("rang")
        tot_f = d["cout_fcfa"].sum(); tot_e = d["cout_eur"].sum()
        rows = "".join(
            f"<tr><td>{int(r.rang)}</td><td><b>{r.prefecture}</b></td><td>{r.region}</td>"
            f"<td>+{nf(r.besoin_mm)}</td><td>+{nf(r.besoin_ag)}</td>"
            f"<td>{R.fmt_fcfa(r.cout_fcfa)}</td><td>{R.fmt_eur(r.cout_eur)}</td></tr>"
            for r in d.itertuples())
        return ui.HTML(
            f"<p style='font-size:13px'>Budget national pour l'objectif choisi : "
            f"<b style='color:{T.GREEN_DARK}'>{R.fmt_fcfa(tot_f)}</b> "
            f"(≈ {R.fmt_eur(tot_e)}).</p>"
            "<div style='max-height:380px;overflow:auto'><table class='reco'>"
            "<tr><th>Rang</th><th>Prefecture</th><th>Region</th><th>+Agents MM</th>"
            "<th>+Agences</th><th>Investissement FCFA</th><th>≈ EUR</th></tr>"
            f"{rows}</table></div>")

    # ==================================================================
    #  ONGLET CARTE
    # ==================================================================
    @render.ui
    def tab_carte():
        return ui.TagList(
            panel("🗺️ Carte nationale interactive",
                ui.div(
                    ui.input_select("c_ind", "Indicateur", {
                        "mm_pour_1000": "Agents mobile money / 1 000 hab.",
                        "agences_pour_100k": "Agences telecoms / 100 000 hab.",
                        "score_priorite": "Score de priorite",
                        "population": "Population 2026",
                        "n_mobile_money": "Nombre d'agents mobile money",
                    }, selected="mm_pour_1000"),
                    ui.input_checkbox("c_pts", "Afficher les infrastructures (points)", False),
                    style="display:flex;gap:18px;align-items:end;margin-bottom:8px;flex-wrap:wrap"),
                ui.output_ui("carte_map")),
        )

    @render.ui
    def carte_map():
        ind = input.c_ind()
        labels = {"mm_pour_1000": " /1000", "agences_pour_100k": " /100k",
                  "score_priorite": " /100", "population": " hab.", "n_mobile_money": " agents"}
        scale = T.PRIORITY_SCALE if ind == "score_priorite" else T.GREEN_SCALE
        vals = [{"key": r.key, "name": r.prefecture, "value": float(getattr(r, ind))}
                for r in PREF.itertuples()]
        points = None
        if input.c_pts():
            colors = {"Togocom": T.GREEN, "Moov": T.YELLOW, "Datacenter": T.RED}
            points = [{"name": f"{r.nom} ({r.operateur})", "lon": float(r.lon),
                       "lat": float(r.lat), "color": colors.get(r.operateur, T.GREEN_DARK)}
                      for r in PTS.itertuples() if pd.notna(r.lon)]
        return T.highmap(vals, title="", subtitle=labels.get(ind, ""),
                         scale=scale, points=points,
                         value_suffix=labels.get(ind, ""), height=560)

    # ==================================================================
    #  ONGLET AUTEUR
    # ==================================================================
    @render.ui
    def tab_auteur():
        return ui.div(
            ui.div(
                panel("👤 Profil",
                    ui.HTML("""
                    <div class="photo-ph" style="height:220px">
                       <div style="font-size:34px">📷</div>
                       Emplacement photo de profil<br/>(a inserer)</div>
                    <h3 style="text-align:center;color:#0B6E4F;margin:12px 0 2px">
                       Maurice Kodjo SEKOU</h3>
                    <p style="text-align:center;color:#D21034;font-weight:700;margin:0">
                       Analyste Statisticien</p>
                    <p style="text-align:center;font-size:13px">sekoukodjo4@gmail.com</p>
                    <div style="text-align:center">
                      <span class="badge" style="background:#0B6E4F;margin:2px">Statistique</span>
                      <span class="badge" style="background:#008751;margin:2px">Python</span>
                      <span class="badge" style="background:#FFCE00;color:#1c2b27;margin:2px">R / Shiny</span>
                      <span class="badge" style="background:#D21034;margin:2px">SIG</span>
                      <span class="badge" style="background:#4c5a55;margin:2px">Machine Learning</span>
                    </div>""")),
                ui.div(
                    panel("ℹ️ A propos de ce projet",
                        ui.HTML(f"""<p style="font-size:14px;line-height:1.6">
                        Ce tableau de bord, developpe dans le cadre du
                        <b>Data Challenge — Economie Numerique</b> du <b>Togo AI Lab</b>,
                        dresse un diagnostic de l'acces aux telecommunications et services
                        numeriques au Togo. Il cartographie les infrastructures
                        (agences telecoms, datacenters), analyse la couverture des services
                        (mobile money) au regard de la population, identifie les
                        <b>zones blanches</b> et propose des <b>recommandations
                        d'investissement interactives</b>.</p>
                        <p style="font-size:13px;color:#41524c">Population de reference :
                        projection <b>{META['annee_pop']}</b> a partir du RGPH-5 (2022),
                        taux de croissance moyen {META['taux_croissance']*100:.1f} %/an.</p>""")),
                    ui.div(
                        panel("⚙️ Sous le capot", ui.HTML(
                            "<ul style='font-size:13px;line-height:1.7'>"
                            "<li>Pretraitement Python : nettoyage, fusion, indicateurs</li>"
                            "<li>Projection demographique 2026 (taux 2,3 %)</li>"
                            "<li>Score de priorite + simulation de couts</li>"
                            "<li>Donnees pre-agregees en .parquet (chargement rapide)</li>"
                            "<li>Shiny for Python · Highcharts · Highmaps</li></ul>")),
                        panel("🗄️ Sources de donnees", ui.HTML(
                            "<ul style='font-size:13px;line-height:1.7'>"
                            "<li>geodata.gouv.tg — agences telecoms, mobile money, datacenters</li>"
                            "<li>RGPH-5 (2022) — population</li>"
                            "<li>geoBoundaries — limites administratives</li></ul>")),
                        class_="grid-2")),
                class_="author-wrap"),
        )


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
