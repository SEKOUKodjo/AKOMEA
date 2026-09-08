# -*- coding: utf-8 -*-
"""
=============================================================================
  Tableau de bord bilingue (FR/EN) — Acces aux telecommunications & services
  numeriques au Togo. Data Challenge Economie Numerique — Togo AI Lab.
  Auteur : Maurice Kodjo SEKOU — Shiny for Python + Highcharts / Highmaps.
  Aucune emoji : icones Font Awesome integrees (faicons).
=============================================================================
"""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
from shiny import App, reactive, render, ui

from modules import theme as T
from modules import recommender as R
from modules import i18n as I
from modules.theme import ic

# --------------------------------------------------------------------------
# DONNEES (pre-calculees)
# --------------------------------------------------------------------------
DATA = Path(__file__).parent / "data"
PREF = pd.read_parquet(DATA / "prefectures.parquet")
REG = pd.read_parquet(DATA / "regions.parquet")
CANT = pd.read_parquet(DATA / "cantons.parquet")
PTS = pd.read_parquet(DATA / "points_infra.parquet")
MM = pd.read_parquet(DATA / "points_mobile_money.parquet")
HIER = pd.read_parquet(DATA / "hierarchie.parquet")
META = json.loads((DATA / "meta.json").read_text())
POP_LOOKUP = json.loads((DATA / "pop_lookup.json").read_text())
COMMUNE_POP = POP_LOOKUP["commune"]
CANTON_POP = POP_LOOKUP["canton"]
FACTEUR = POP_LOOKUP["facteur_projection"]

FCFA = R.FCFA_PER_EUR
LEVELS = ["region", "prefecture", "commune", "canton"]
COLS = {"region": "region_nom_bdd", "prefecture": "prefecture_nom_bdd",
        "commune": "commune_nom_bdd", "canton": "canton_nom_bdd"}
PREF_REMAP = {"MO": "PLAINE DU MO", "KPENDJAL OUEST": "NAKI OUEST"}

# Icones par onglet / indicateur (aucune emoji)
NAV_ICONS = {"accueil": "house", "infra": "building", "services": "money-bill-wave",
             "couverture": "satellite-dish", "priorites": "ranking-star",
             "reco": "lightbulb", "carte": "map", "auteur": "user"}


def nf(v, dec=0):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return (f"{v:,.{dec}f}").replace(",", " ").replace(".", ",")


def _norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s))
                if unicodedata.category(c) != "Mn").upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]", " ", s)).strip()


def _pkey(x):
    return PREF_REMAP.get(_norm(x), _norm(x))


def geo_filter(df, sel):
    m = pd.Series(True, index=df.index)
    for lvl in LEVELS:
        if sel.get(lvl, "Toutes") != "Toutes":
            m = m & (df[COLS[lvl]] == sel[lvl])
    return df[m]


def unit_population(sel):
    if sel.get("canton", "Toutes") != "Toutes":
        v = CANTON_POP.get(f"{_pkey(sel['prefecture'])}||{_norm(sel['canton'])}")
        return round(v * FACTEUR) if v else None
    if sel.get("commune", "Toutes") != "Toutes":
        v = COMMUNE_POP.get(_norm(sel["commune"]))
        return round(v * FACTEUR) if v else None
    if sel.get("prefecture", "Toutes") != "Toutes":
        r = PREF[PREF.prefecture == sel["prefecture"]]
        return int(r["population"].iloc[0]) if len(r) else None
    if sel.get("region", "Toutes") != "Toutes":
        r = REG[REG.region == sel["region"]]
        return int(r["population"].iloc[0]) if len(r) else None
    return int(PREF["population"].sum())


def unit_label(sel, lang):
    for lvl in reversed(LEVELS):
        if sel.get(lvl, "Toutes") != "Toutes":
            return I.t(lang, f"scope_{lvl}", v=sel[lvl])
    return I.t(lang, "scope_all")


def cascade_opts(col, filters):
    d = HIER
    for c, v in filters.items():
        if v and v != "Toutes":
            d = d[d[c] == v]
    vals = sorted(x for x in d[col].dropna().unique()
                  if x and str(x) not in ("nan", "Nsp"))
    return ["Toutes"] + vals


def choices_for(col, filters, lang):
    """Dict {valeur: libelle} avec 'Toutes' localise, valeurs canoniques."""
    return {o: (I.t(lang, "all") if o == "Toutes" else o)
            for o in cascade_opts(col, filters)}


def unit_counts(sel):
    mm = geo_filter(MM, sel)
    pt = geo_filter(PTS, sel)
    return (unit_population(sel), int(len(mm)),
            int((pt.type_infra == "Agence telecom").sum()),
            int((pt.type_infra == "Datacenter").sum()))


def cant_filter(sel):
    d = CANT
    if sel.get("region", "Toutes") != "Toutes":
        d = d[d.region.apply(_norm) == _norm(sel["region"])]
    if sel.get("prefecture", "Toutes") != "Toutes":
        d = d[d.prefecture.apply(_pkey) == _pkey(sel["prefecture"])]
    if sel.get("canton", "Toutes") != "Toutes":
        d = d[d.canton.apply(_norm) == _norm(sel["canton"])]
    return d


# ==========================================================================
#  INTERFACE (structure statique ; textes rendus dynamiquement selon la langue)
# ==========================================================================
app_ui = ui.page_fluid(
    T.head_deps(),
    ui.div(ui.input_radio_buttons("lang", None, {"fr": "FR", "en": "EN"},
                                  selected="fr", inline=True), class_="lang-switch"),
    ui.output_ui("topbar"),
    ui.div(
        ui.div(
            ui.output_ui("side_title"),
            ui.input_select("f_region", "Region",
                            {"Toutes": "Toutes"}, selected="Toutes"),
            ui.input_select("f_pref", "Prefecture", {"Toutes": "Toutes"}, selected="Toutes"),
            ui.input_select("f_commune", "Commune", {"Toutes": "Toutes"}, selected="Toutes"),
            ui.input_select("f_canton", "Canton", {"Toutes": "Toutes"}, selected="Toutes"),
            ui.input_action_button("reset", "Tout le Togo", class_="btn",
                                   style=f"width:100%;background:{T.YELLOW};border:none;"
                                   f"font-weight:800;color:{T.INK};margin-top:6px;"
                                   "border-radius:8px;padding:8px;"),
            ui.hr(),
            ui.output_ui("side_footer"),
            class_="sidebar"),
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
    title="Observatoire de l'Economie Numerique — Togo",
)


# ==========================================================================
#  SERVEUR
# ==========================================================================
def server(input, output, session):

    def L():
        return input.lang()

    def t(key, **f):
        return I.t(input.lang(), key, **f)

    def cur_tab():
        try:
            return input.active_tab()
        except Exception:
            return "accueil"

    # ---------------- bandeau + navigation (barre fixe) ----------------
    @render.ui
    def topbar():
        lang = L()
        active = cur_tab()
        navbtns = "".join(
            f'<button class="navlink{" active" if v==active else ""}" '
            f'id="nav_{v}" onclick="selTab(\'{v}\',this)">{ic(NAV_ICONS[v])}'
            f'<span style="margin-left:6px">{I.t(lang,"nav_"+v)}</span></button>'
            for v in NAV_ICONS)
        return ui.HTML(f"""
        <div class="topbar">
          <div class="gov-banner">
            <div class="ph logo-ph">{I.t(lang,'logo_ph')}</div>
            <div class="gov-titles">
              <div class="t1">{I.t(lang,'republic')}</div>
              <div class="t2">{I.t(lang,'motto')}</div>
              <div class="t3">{I.t(lang,'ministry')}</div>
              <div class="t4">{I.t(lang,'banner_sub')}</div>
            </div>
            <div class="ph crest-ph">{I.t(lang,'crest_ph')}</div>
          </div>
          <div class="flag-band"></div>
          <div class="appbar">
            <div class="brand">{ic('tower-broadcast')}<span style="margin-left:8px">
              {I.t(lang,'brand')}</span></div>
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
        function fitTop(){{
          var tb=document.querySelector('.topbar'); if(!tb) return;
          var h=tb.offsetHeight;
          document.querySelectorAll('.app-body').forEach(function(e){{
             e.style.paddingTop=(h+14)+'px'; }});
          document.querySelectorAll('.sidebar').forEach(function(e){{
             e.style.top=(h+10)+'px'; }});
        }}
        window.addEventListener('resize', fitTop);
        setTimeout(fitTop,60); setTimeout(fitTop,400);
        </script>""")

    @render.ui
    def side_title():
        return ui.HTML(f'<h4>{ic("magnifying-glass")}<span style="margin-left:6px">'
                       f'{t("side_title")}</span></h4>')

    @render.ui
    def side_footer():
        return ui.TagList(
            ui.p(ui.HTML(f"<b>{t('sources')}</b><br/>{t('sources_list')}"),
                 style="font-size:11px;color:#6b7b76;"),
            ui.p(ui.HTML(t("pop_note", y=META["annee_pop"],
                           r=f"{META['taux_croissance']*100:.1f}")),
                 style="font-size:11px;color:#6b7b76;"))

    # ---------------- navigation switch ----------------
    @reactive.effect
    @reactive.event(input.active_tab)
    async def _switch():
        ui.update_navset("tab", selected=input.active_tab())
        await session.send_custom_message("reflow", {})

    # ---------------- cascade des filtres (sidebar) ----------------
    @reactive.effect
    @reactive.event(input.f_region)
    def _c_region():
        ui.update_select("f_pref", choices=choices_for(
            "prefecture", {"region": input.f_region()}, L()), selected="Toutes")
        ui.update_select("f_commune", choices=choices_for("commune", {}, L()), selected="Toutes")
        ui.update_select("f_canton", choices=choices_for("canton", {}, L()), selected="Toutes")

    @reactive.effect
    @reactive.event(input.f_pref)
    def _c_pref():
        ui.update_select("f_commune", choices=choices_for(
            "commune", {"region": input.f_region(), "prefecture": input.f_pref()},
            L()), selected="Toutes")
        ui.update_select("f_canton", choices=choices_for("canton", {}, L()), selected="Toutes")

    @reactive.effect
    @reactive.event(input.f_commune)
    def _c_commune():
        ui.update_select("f_canton", choices=choices_for(
            "canton", {"region": input.f_region(), "prefecture": input.f_pref(),
                       "commune": input.f_commune()}, L()), selected="Toutes")

    @reactive.effect
    @reactive.event(input.reset)
    def _reset():
        ui.update_select("f_region", selected="Toutes")
        for k in ("f_pref", "f_commune", "f_canton"):
            ui.update_select(k, choices={"Toutes": t("all")}, selected="Toutes")

    # ---------------- changement de langue : libelles + choix ----------------
    @reactive.effect
    @reactive.event(input.lang)
    def _relang():
        lang = input.lang()
        with reactive.isolate():
            sr, sp = input.f_region(), input.f_pref()
            sc, sk = input.f_commune(), input.f_canton()
        ui.update_select("f_region", label=I.t(lang, "region"),
                         choices=choices_for("region", {}, lang), selected=sr)
        ui.update_select("f_pref", label=I.t(lang, "prefecture"),
                         choices=choices_for("prefecture", {"region": sr}, lang), selected=sp)
        ui.update_select("f_commune", label=I.t(lang, "commune"),
                         choices=choices_for("commune", {"region": sr, "prefecture": sp}, lang),
                         selected=sc)
        ui.update_select("f_canton", label=I.t(lang, "canton"),
                         choices=choices_for("canton", {"region": sr, "prefecture": sp,
                                                        "commune": sc}, lang), selected=sk)
        ui.update_action_button("reset", label=I.t(lang, "reset"))

    @reactive.calc
    def sel():
        return {"region": input.f_region(), "prefecture": input.f_pref(),
                "commune": input.f_commune(), "canton": input.f_canton()}

    @reactive.calc
    def scope():
        df = PREF
        if input.f_region() != "Toutes":
            df = df[df.region == input.f_region()]
        if input.f_pref() != "Toutes":
            df = df[df.prefecture == input.f_pref()]
        return df

    def badge(txt, color=None):
        color = color or T.GREEN_DARK
        return ui.div(ui.HTML(f"<span class='badge' style='background:{color}'>{txt}</span>"),
                      style="margin-bottom:10px;")

    def panel(icon, key, *body):
        head = ui.div(ui.HTML(f"{ic(icon)}<span style='margin-left:8px'>{t(key)}</span>"),
                      class_="ph-head")
        return ui.div(head, *body, class_="panel")

    # couleurs / libelles des couches d'infrastructure sur les cartes
    INFRA_GROUPS = [("Togocom", T.GREEN, "opt_togocom"),
                    ("Moov", T.YELLOW, "opt_moov"),
                    ("Datacenter", T.RED, "opt_dc")]

    def infra_series(pts, which):
        """Couches de points (une par type) selon le type choisi ('all' ou un type)."""
        out = []
        for op, color, key in INFRA_GROUPS:
            if which not in ("all", op):
                continue
            d = pts[pts.operateur == op] if op != "Datacenter" else pts[pts.type_infra == "Datacenter"]
            data = [{"name": r.nom, "lon": float(r.lon), "lat": float(r.lat)}
                    for r in d.itertuples() if pd.notna(r.lon)]
            if data:
                out.append({"name": t(key), "color": color, "data": data})
        return out

    def map_controls(type_id, label_id, choices):
        return ui.div(
            ui.input_select(type_id, t("map_type"), choices, selected="all"),
            ui.input_checkbox(label_id, t("map_labels"), False),
            style="display:flex;gap:18px;align-items:end;margin-bottom:8px;flex-wrap:wrap;")

    def infra_choices():
        return {"all": t("opt_all_infra"), "Togocom": t("opt_togocom"),
                "Moov": t("opt_moov"), "Datacenter": t("opt_dc")}

    def legend_strip(series):
        """Legende HTML claire (pastille coloree + nom + effectif) au-dessus de la carte."""
        if not series:
            return ui.HTML(f"<div style='margin:2px 0 8px;font-size:12px;color:#6b7b76'>"
                           f"{t('map_none')}</div>")
        items = "".join(
            f"<span style='display:inline-flex;align-items:center;margin-right:18px;"
            f"font-size:12.5px;font-weight:600'><span style='width:13px;height:13px;"
            f"border-radius:50%;background:{s['color']};display:inline-block;margin-right:6px;"
            f"border:1px solid #fff;box-shadow:0 0 0 1px #cbd5d0'></span>{s['name']} "
            f"({nf(len(s['data']))})</span>" for s in series)
        return ui.HTML(f"<div style='margin:2px 0 8px'>{items}</div>")

    # ==================================================================
    #  ACCUEIL
    # ==================================================================
    @render.ui
    def tab_accueil():
        s = sel()
        pop, n_mm, n_ag, n_dc = unit_counts(s)
        mm1000 = round(n_mm / pop * 1000, 2) if pop else None
        pop_txt = nf(pop) if pop else t("na")

        def card(cls, icon, value, label, sub):
            return (f'<div class="kpi {cls}"><span class="kpi-ic ic">{icon}</span>'
                    f'<div class="v">{value}</div><div class="l">{label}</div>'
                    f'<div class="s">{sub}</div></div>')
        kpis = ui.HTML('<div class="kpi-row">' + "".join([
            card("green", ic("money-bill-wave"), nf(n_mm), t("kpi_mm"), t("kpi_mm_s")),
            card("green2", ic("building"), nf(n_ag), t("kpi_ag"), t("kpi_ag_s")),
            card("yellow", ic("scale-balanced"),
                 nf(mm1000, 2) if mm1000 is not None else t("na"), t("kpi_ratio"), t("kpi_ratio_s")),
            card("grey", ic("server"), nf(n_dc), t("kpi_dc"), t("kpi_dc_s")),
            card("green", ic("users"), pop_txt, t("kpi_pop", y=META["annee_pop"]), t("kpi_pop_s")),
            card("red", ic("tower-cell"), nf(META["n_zones_blanches"]), t("kpi_zb"), t("kpi_zb_s")),
        ]) + "</div>")

        return ui.TagList(
            badge(unit_label(s, L())), kpis,
            ui.div(panel("money-bill-wave", "p_mm_region", ui.output_ui("acc_mm_region")),
                   panel("building", "p_ag_op", ui.output_ui("acc_ag_op")), class_="grid-2"),
            ui.div(panel("scale-balanced", "p_adequation", ui.output_ui("acc_adequation")),
                   panel("map", "p_densite_pref", ui.output_ui("acc_map")), class_="grid-2"),
        )

    @render.ui
    def acc_mm_region():
        d = REG.sort_values("n_mobile_money", ascending=False)
        return T.highchart({
            "chart": {"type": "column"}, "title": {"text": None},
            "xAxis": {"categories": d["region"].tolist()},
            "yAxis": {"title": {"text": t("ax_agents")}},
            "tooltip": {"pointFormat": "<b>{point.y:,.0f}</b>"},
            "plotOptions": {"column": {"colorByPoint": True, "borderRadius": 3}},
            "series": [{"name": t("s_mm"), "data": d["n_mobile_money"].tolist()}],
        }, height=300)

    @render.ui
    def acc_ag_op():
        d = geo_filter(PTS, sel())
        return T.highchart({
            "chart": {"type": "pie"}, "title": {"text": None},
            "tooltip": {"pointFormat": "<b>{point.y}</b> ({point.percentage:.0f} %)"},
            "plotOptions": {"pie": {"innerSize": "55%", "dataLabels":
                {"format": "{point.name}: {point.y}"}}},
            "series": [{"name": t("th_agences"), "colorByPoint": True, "data": [
                {"name": "Togocom", "y": int((d.operateur == "Togocom").sum()), "color": T.GREEN},
                {"name": "Moov", "y": int((d.operateur == "Moov").sum()), "color": T.YELLOW},
                {"name": t("kpi_dc"), "y": int((d.type_infra == "Datacenter").sum()), "color": T.RED},
            ]}],
        }, height=300)

    @render.ui
    def acc_adequation():
        d = scope().sort_values("mm_pour_1000", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist()},
            "yAxis": {"title": {"text": t("ax_mm1000")},
                      "plotLines": [{"value": META["mm_pour_1000_national"], "color": T.RED,
                                     "width": 2, "dashStyle": "Dash",
                                     "label": {"text": t("nat_avg"), "style": {"color": T.RED}}}]},
            "tooltip": {"pointFormat": "<b>{point.y:.2f}</b>"},
            "plotOptions": {"bar": {"color": T.GREEN, "borderRadius": 2}},
            "series": [{"name": t("ax_mm1000"), "data": d["mm_pour_1000"].round(2).tolist()}],
        }, height=380)

    @render.ui
    def acc_map():
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.mm_pour_1000)}
                for r in PREF.itertuples()]
        return T.highmap(vals, subtitle=t("ax_mm1000"), value_suffix=" / 1000", height=380)

    # ==================================================================
    #  INFRASTRUCTURES
    # ==================================================================
    @render.ui
    def tab_infra():
        return ui.TagList(
            badge(t("infra_badge", s=unit_label(sel(), L()))),
            panel("map-location-dot", "p_infra_map",
                  map_controls("infra_type", "infra_labels", infra_choices()),
                  ui.output_ui("infra_map")),
            ui.div(panel("building", "p_infra_bar", ui.output_ui("infra_bar")),
                   panel("clock-rotate-left", "p_infra_time", ui.output_ui("infra_timeline")),
                   class_="grid-2"),
            panel("server", "p_infra_dc", ui.output_ui("infra_dc_note")),
        )

    @render.ui
    def infra_map():
        pts = geo_filter(PTS, sel())
        series = infra_series(pts, input.infra_type())
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.n_agences)}
                for r in PREF.itertuples()]
        return ui.TagList(legend_strip(series), T.highmap(
            vals, subtitle=t("map_fond"), point_series=series,
            show_labels=input.infra_labels(), fond_name=t("map_fond"),
            value_suffix=" " + t("th_agences").lower(), height=500))

    @render.ui
    def infra_bar():
        d = geo_filter(PTS, sel())
        d = d[d.type_infra == "Agence telecom"]
        g = d.groupby(["prefecture_nom_bdd", "operateur"]).size().unstack(fill_value=0)
        for op in ["Togocom", "Moov"]:
            if op not in g:
                g[op] = 0
        g["tot"] = g.sum(axis=1)
        g = g.sort_values("tot", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": g.index.tolist()},
            "yAxis": {"title": {"text": t("ax_nb_agences")}, "stackLabels": {"enabled": True}},
            "plotOptions": {"series": {"stacking": "normal", "borderRadius": 2}},
            "tooltip": {"shared": True},
            "series": [{"name": "Togocom", "data": g["Togocom"].tolist(), "color": T.GREEN},
                       {"name": "Moov", "data": g["Moov"].tolist(), "color": T.YELLOW}],
        }, height=420)

    @render.ui
    def infra_timeline():
        d = geo_filter(PTS, sel())
        d = d[(d.type_infra == "Agence telecom") & d.annee.notna()]
        g = d.groupby("annee").size().sort_index().cumsum()
        return T.highchart({
            "chart": {"type": "area"}, "title": {"text": None},
            "xAxis": {"categories": [int(x) for x in g.index.tolist()]},
            "yAxis": {"title": {"text": t("s_cumul_ag")}},
            "tooltip": {"pointFormat": "<b>{point.y}</b>"},
            "plotOptions": {"area": {"color": T.GREEN, "fillColor": "rgba(0,135,81,.18)",
                                     "marker": {"enabled": False}}},
            "series": [{"name": t("s_cumul_ag"), "data": g.tolist()}],
        }, height=420)

    @render.ui
    def infra_dc_note():
        d = PTS[PTS.type_infra == "Datacenter"]
        rows = "".join(
            f"<tr><td>{r.nom}</td><td>{r.prefecture_nom_bdd}</td><td>{r.commune_nom_bdd}</td>"
            f"<td>{int(r.annee) if pd.notna(r.annee) else '—'}</td></tr>" for r in d.itertuples())
        return ui.HTML(
            f"<p style='color:#6b7b76;font-size:13px'>{t('infra_dc_note', n=len(d))}</p>"
            f"<table class='reco'><tr><th>{t('th_etab')}</th><th>{t('th_prefecture')}</th>"
            f"<th>{t('th_commune')}</th><th>{t('th_annee')}</th></tr>{rows}</table>")

    # ==================================================================
    #  SERVICES NUMERIQUES
    # ==================================================================
    @render.ui
    def tab_services():
        return ui.TagList(
            badge(t("srv_badge", s=unit_label(sel(), L()))),
            ui.div(panel("map", "p_srv_map", ui.output_ui("srv_map")),
                   panel("chart-pie", "p_srv_op", ui.output_ui("srv_op")), class_="grid-2"),
            ui.div(panel("arrow-trend-up", "p_srv_top", ui.output_ui("srv_top")),
                   panel("arrow-trend-down", "p_srv_bottom", ui.output_ui("srv_bottom")),
                   class_="grid-2"),
            panel("users", "p_srv_hab", ui.output_ui("srv_hab")),
        )

    @render.ui
    def srv_map():
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.mm_pour_1000)}
                for r in PREF.itertuples()]
        return T.highmap(vals, subtitle=t("ax_mm1000"), value_suffix=" / 1000", height=420)

    @render.ui
    def srv_op():
        g = geo_filter(MM, sel()).groupby("operateur").size().sort_values(ascending=False)
        return T.highchart({
            "chart": {"type": "pie"}, "title": {"text": None},
            "tooltip": {"pointFormat": "<b>{point.y:,.0f}</b> ({point.percentage:.1f} %)"},
            "plotOptions": {"pie": {"innerSize": "50%", "colorByPoint": True,
                            "dataLabels": {"format": "{point.name}: {point.percentage:.0f} %"}}},
            "series": [{"name": t("ax_agents"), "data": [{"name": k, "y": int(v)} for k, v in g.items()]}],
        }, height=420)

    def _rank_bar(d, color):
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist()},
            "yAxis": {"title": {"text": t("ax_mm1000")}},
            "tooltip": {"pointFormat": "<b>{point.y:.2f}</b>"},
            "plotOptions": {"bar": {"color": color, "borderRadius": 2}},
            "series": [{"name": t("ax_mm1000"), "data": d["mm_pour_1000"].round(2).tolist()}],
        }, height=360)

    @render.ui
    def srv_top():
        return _rank_bar(scope().sort_values("mm_pour_1000", ascending=False).head(10), T.GREEN)

    @render.ui
    def srv_bottom():
        return _rank_bar(scope().sort_values("mm_pour_1000", ascending=True).head(10), T.RED)

    @render.ui
    def srv_hab():
        d = scope().dropna(subset=["hab_par_agent_mm"]).sort_values(
            "hab_par_agent_mm", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "column"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist(), "labels": {"rotation": -45}},
            "yAxis": {"title": {"text": t("ax_hab_agent")}},
            "tooltip": {"pointFormat": "<b>{point.y:,.0f}</b>"},
            "plotOptions": {"column": {"color": T.RED, "borderRadius": 2}},
            "series": [{"name": t("s_hab_agent"), "data": d["hab_par_agent_mm"].tolist()}],
        }, height=340)

    # ==================================================================
    #  ZONES BLANCHES
    # ==================================================================
    @render.ui
    def tab_couverture():
        tot = len(CANT); blancs = int((~CANT.couvert_mm).sum())
        taux = round((tot - blancs) / tot * 100, 1)

        def card(cls, icon, value, label, sub):
            return (f'<div class="kpi {cls}"><span class="kpi-ic ic">{icon}</span>'
                    f'<div class="v">{value}</div><div class="l">{label}</div>'
                    f'<div class="s">{sub}</div></div>')
        kpis = ui.HTML('<div class="kpi-row">' + "".join([
            card("green", ic("circle-check"), nf(tot - blancs), t("cov_couverts"), t("cov_couverts_s")),
            card("red", ic("tower-cell"), nf(blancs), t("kpi_zb"), t("cov_blancs_s")),
            card("yellow", ic("percent"), nf(taux, 1) + " %", t("cov_taux"), t("cov_taux_s")),
            card("grey", ic("layer-group"), nf(tot), t("cov_total"), t("cov_total_s")),
        ]) + "</div>")
        return ui.TagList(
            kpis,
            ui.div(panel("chart-column", "p_cov_bar", ui.output_ui("cov_bar")),
                   panel("map-location-dot", "p_cov_map",
                         ui.div(ui.input_checkbox("cov_labels", t("map_labels"), False),
                                style="margin-bottom:6px;"),
                         ui.output_ui("cov_map")), class_="grid-2"),
            panel("list", "p_cov_table", ui.output_ui("cov_table")),
        )

    @render.ui
    def cov_bar():
        g = CANT.groupby("region")["couvert_mm"].agg(total="count", couverts="sum")
        g["blancs"] = g["total"] - g["couverts"]
        g = g.sort_values("blancs", ascending=False)
        return T.highchart({
            "chart": {"type": "column"}, "title": {"text": None},
            "xAxis": {"categories": g.index.tolist()},
            "yAxis": {"title": {"text": t("ax_nb_cantons")}, "stackLabels": {"enabled": True}},
            "plotOptions": {"column": {"stacking": "normal", "borderRadius": 2}},
            "tooltip": {"shared": True},
            "series": [{"name": t("covered"), "data": g["couverts"].astype(int).tolist(), "color": T.GREEN},
                       {"name": t("s_wz"), "data": g["blancs"].astype(int).tolist(), "color": T.RED}],
        }, height=380)

    @render.ui
    def cov_map():
        d = cant_filter(sel())
        d = d[(~d.couvert_mm) & d.lon.notna()]
        data = [{"name": f"{r.canton} ({r.prefecture})", "lon": float(r.lon),
                 "lat": float(r.lat)} for r in d.itertuples()]
        series = [{"name": t("s_wzc"), "color": T.RED, "data": data}] if data else []
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.n_mobile_money)}
                for r in PREF.itertuples()]
        return ui.TagList(legend_strip(series), T.highmap(
            vals, subtitle=t("cov_map_sub"), point_series=series,
            show_labels=input.cov_labels(), fond_name=t("th_mm"),
            value_suffix=" " + t("th_mm").lower(), height=360))

    @render.ui
    def cov_table():
        d = cant_filter(sel())
        d = d[~d.couvert_mm].sort_values(["region", "prefecture", "canton"])
        rows = "".join(f"<tr><td>{r.canton}</td><td>{r.prefecture}</td><td>{r.region}</td></tr>"
                       for r in d.itertuples())
        return ui.HTML(f"<div style='max-height:340px;overflow:auto'><table class='reco'>"
                       f"<tr><th>{t('th_canton')}</th><th>{t('th_prefecture')}</th>"
                       f"<th>{t('th_region')}</th></tr>{rows}</table></div>")

    # ==================================================================
    #  PRIORITES
    # ==================================================================
    @render.ui
    def tab_priorites():
        return ui.TagList(
            badge(t("prio_badge"), T.RED),
            ui.div(panel("ranking-star", "p_prio_bar", ui.output_ui("prio_bar")),
                   panel("map", "p_prio_map", ui.output_ui("prio_map")), class_="grid-2"),
            panel("table-list", "p_prio_table", ui.output_ui("prio_table")),
        )

    @render.ui
    def prio_bar():
        d = scope().sort_values("score_priorite", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist()},
            "yAxis": {"title": {"text": t("ax_score")}, "max": 100},
            "tooltip": {"pointFormat": "<b>{point.y:.1f}</b>/100"},
            "plotOptions": {"bar": {"borderRadius": 2}},
            "series": [{"name": t("th_score"), "data": [
                {"y": float(v), "color": T.RED if v >= 66 else (T.YELLOW if v >= 45 else T.GREEN)}
                for v in d["score_priorite"]]}],
        }, height=440)

    @render.ui
    def prio_map():
        vals = [{"key": r.key, "name": r.prefecture, "value": float(r.score_priorite)}
                for r in PREF.itertuples()]
        return T.highmap(vals, subtitle=t("ax_score"), scale=T.PRIORITY_SCALE,
                         value_suffix=" /100", height=440)

    @render.ui
    def prio_table():
        d = scope().sort_values("rang_priorite")
        rows = ""
        for r in d.itertuples():
            col = T.RED if r.score_priorite >= 66 else (T.YELLOW if r.score_priorite >= 45 else T.GREEN)
            rows += (f"<tr><td>{r.rang_priorite}</td><td><b>{r.prefecture}</b></td>"
                     f"<td>{r.region}</td><td>{nf(r.population)}</td><td>{nf(r.n_mobile_money)}</td>"
                     f"<td>{nf(r.mm_pour_1000,2)}</td><td>{nf(r.n_agences)}</td>"
                     f"<td><span class='badge' style='background:{col}'>{nf(r.score_priorite,1)}</span></td></tr>")
        return ui.HTML(f"<div style='max-height:420px;overflow:auto'><table class='reco'>"
                       f"<tr><th>{t('th_rank')}</th><th>{t('th_prefecture')}</th>"
                       f"<th>{t('th_region')}</th><th>{t('th_pop')}</th><th>{t('th_mm')}</th>"
                       f"<th>MM/1000</th><th>{t('th_agences')}</th><th>{t('th_score')}</th></tr>"
                       f"{rows}</table></div>")

    # ==================================================================
    #  RECOMMANDATIONS
    # ==================================================================
    @render.ui
    def tab_reco():
        lang = L()
        return ui.TagList(
            badge(t("reco_badge")),
            panel("sliders", "p_reco_geo", ui.div(
                ui.input_select("r_region", I.t(lang, "region"),
                                choices_for("region", {}, lang), selected="Toutes"),
                ui.input_select("r_pref", I.t(lang, "prefecture"), {"Toutes": t("all")}, selected="Toutes"),
                ui.input_select("r_commune", I.t(lang, "commune"), {"Toutes": t("all")}, selected="Toutes"),
                ui.input_select("r_canton", I.t(lang, "canton"), {"Toutes": t("all")}, selected="Toutes"),
                style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;")),
            panel("bullseye", "p_reco_obj", ui.div(
                ui.input_slider("r_obj_mm", t("obj_mm"), 1.0, 8.0, 3.0, step=0.5),
                ui.input_slider("r_obj_ag", t("obj_ag"), 0.5, 5.0, 1.5, step=0.5),
                ui.input_numeric("r_cout_mm", t("cost_mm"), R.COUT_MM, step=50000),
                ui.input_numeric("r_cout_ag", t("cost_ag"), R.COUT_AGENCE, step=1000000),
                style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;")),
            ui.output_ui("reco_result"),
            panel("money-bill-trend-up", "p_reco_chart", ui.output_ui("reco_chart")),
            panel("table-list", "p_reco_table", ui.output_ui("reco_table")),
        )

    @reactive.effect
    @reactive.event(input.r_region)
    def _rc_region():
        ui.update_select("r_pref", choices=choices_for(
            "prefecture", {"region": input.r_region()}, L()), selected="Toutes")
        ui.update_select("r_commune", choices=choices_for("commune", {}, L()), selected="Toutes")
        ui.update_select("r_canton", choices=choices_for("canton", {}, L()), selected="Toutes")

    @reactive.effect
    @reactive.event(input.r_pref)
    def _rc_pref():
        ui.update_select("r_commune", choices=choices_for(
            "commune", {"region": input.r_region(), "prefecture": input.r_pref()},
            L()), selected="Toutes")
        ui.update_select("r_canton", choices=choices_for("canton", {}, L()), selected="Toutes")

    @reactive.effect
    @reactive.event(input.r_commune)
    def _rc_commune():
        ui.update_select("r_canton", choices=choices_for(
            "canton", {"region": input.r_region(), "prefecture": input.r_pref(),
                       "commune": input.r_commune()}, L()), selected="Toutes")

    @reactive.calc
    def rsel():
        return {"region": input.r_region(), "prefecture": input.r_pref(),
                "commune": input.r_commune(), "canton": input.r_canton()}

    @reactive.calc
    def reco_params():
        return (input.r_obj_mm(), input.r_obj_ag(),
                input.r_cout_mm() or R.COUT_MM, input.r_cout_ag() or R.COUT_AGENCE)

    @render.ui
    def reco_result():
        obj_mm, obj_ag, c_mm, c_ag = reco_params()
        s = rsel()
        pop, n_mm, n_ag, _ = unit_counts(s)
        titre = unit_label(s, L())
        if not pop:
            return ui.HTML(f"""<div class="reco-card" style="border-color:{T.RED}">
              <h3 style="margin:0 0 6px;color:{T.RED}">{ic('bullseye')} {titre}</h3>
              <p style="font-size:14px">{t('reco_nopop', mm=nf(n_mm), ag=nf(n_ag))}</p>
              <p style="font-size:13px;color:#8c1c2b">{t('reco_nopop2')}</p></div>""")
        e = R.compute(pop, n_mm, n_ag, obj_mm, obj_ag, c_mm, c_ag)
        return ui.HTML(f"""
        <div class="reco-card">
          <h3 style="margin:0 0 8px;color:{T.GREEN_DARK}">{ic('bullseye')} {titre}</h3>
          <p style="margin:0 0 10px;font-size:13px;color:#41524c">
            {t('reco_offer', y=META['annee_pop'], pop=nf(pop), mm=nf(n_mm),
               d1=e['mm_pour_1000_actuel'], ag=nf(n_ag), d2=e['ag_pour_100k_actuel'])}</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:12px">
            <div class="reco-card" style="border-color:{T.GREEN}">
              <div class="reco-num">+{nf(e['besoin_mm'])}</div>
              <div>{t('reco_need_mm')}<br/><small>{t('reco_reach', v=obj_mm)}</small></div></div>
            <div class="reco-card" style="border-color:{T.YELLOW}">
              <div class="reco-num">+{nf(e['besoin_ag'])}</div>
              <div>{t('reco_need_ag')}<br/><small>{t('reco_reach_ag', v=obj_ag)}</small></div></div>
          </div>
          <div class="invest-box">
            <div class="b fcfa">{ic('sack-dollar')}<div>{t('reco_total')}</div>
              <div class="amt">{R.fmt_fcfa(e['cout_fcfa'])}</div></div>
            <div class="b eur">{ic('euro-sign')}<div>{t('reco_eur')}</div>
              <div class="amt">{R.fmt_eur(e['cout_eur'])}</div>
              <div style="font-size:11px;opacity:.8">{t('reco_parite', v=FCFA)}</div></div>
          </div>
        </div>""")

    @reactive.calc
    def reco_plan():
        obj_mm, obj_ag, c_mm, c_ag = reco_params()
        recs = []
        for r in PREF.itertuples():
            e = R.compute(int(r.population), int(r.n_mobile_money), int(r.n_agences),
                          obj_mm, obj_ag, c_mm, c_ag)
            e.update(prefecture=r.prefecture, region=r.region, rang=int(r.rang_priorite))
            recs.append(e)
        return pd.DataFrame(recs)

    @render.ui
    def reco_chart():
        d = reco_plan().sort_values("cout_fcfa", ascending=False).head(15)
        return T.highchart({
            "chart": {"type": "bar"}, "title": {"text": None},
            "xAxis": {"categories": d["prefecture"].tolist()},
            "yAxis": {"title": {"text": t("ax_invest")}},
            "tooltip": {"pointFormat": "<b>{point.y:,.0f}</b> M FCFA"},
            "plotOptions": {"bar": {"color": T.GREEN_DARK, "borderRadius": 2}},
            "series": [{"name": t("s_invest"), "data": (d["cout_fcfa"] / 1e6).round(1).tolist()}],
        }, height=440)

    @render.ui
    def reco_table():
        d = reco_plan().sort_values("rang")
        tot_f, tot_e = d["cout_fcfa"].sum(), d["cout_eur"].sum()
        rows = "".join(
            f"<tr><td>{int(r.rang)}</td><td><b>{r.prefecture}</b></td><td>{r.region}</td>"
            f"<td>+{nf(r.besoin_mm)}</td><td>+{nf(r.besoin_ag)}</td>"
            f"<td>{R.fmt_fcfa(r.cout_fcfa)}</td><td>{R.fmt_eur(r.cout_eur)}</td></tr>"
            for r in d.itertuples())
        return ui.HTML(
            f"<p style='font-size:13px'>{t('reco_natbudget', f=R.fmt_fcfa(tot_f), e=R.fmt_eur(tot_e))}</p>"
            f"<div style='max-height:380px;overflow:auto'><table class='reco'>"
            f"<tr><th>{t('th_rank')}</th><th>{t('th_prefecture')}</th><th>{t('th_region')}</th>"
            f"<th>{t('th_needmm')}</th><th>{t('th_needag')}</th><th>{t('th_invest')}</th>"
            f"<th>{t('th_eur')}</th></tr>{rows}</table></div>")

    # ==================================================================
    #  CARTE
    # ==================================================================
    @render.ui
    def tab_carte():
        inds = {"mm_pour_1000": t("ind_mm1000"), "agences_pour_100k": t("ind_ag100k"),
                "score_priorite": t("ind_score"), "population": t("ind_pop"),
                "n_mobile_money": t("ind_nmm")}
        overlay = {"none": t("opt_none"), "all": t("opt_all_infra"),
                   "Togocom": t("opt_togocom"), "Moov": t("opt_moov"),
                   "Datacenter": t("opt_dc")}
        return panel("map", "p_carte", ui.div(
            ui.input_select("c_ind", t("c_indic"), inds, selected="mm_pour_1000"),
            ui.input_select("c_overlay", t("map_show"), overlay, selected="none"),
            ui.input_checkbox("c_labels", t("map_labels"), False),
            style="display:flex;gap:18px;align-items:end;margin-bottom:8px;flex-wrap:wrap"),
            ui.output_ui("carte_map"))

    @render.ui
    def carte_map():
        ind = input.c_ind()
        suff = {"mm_pour_1000": " /1000", "agences_pour_100k": " /100k",
                "score_priorite": " /100", "population": "", "n_mobile_money": ""}
        scale = T.PRIORITY_SCALE if ind == "score_priorite" else T.GREEN_SCALE
        vals = [{"key": r.key, "name": r.prefecture, "value": float(getattr(r, ind))}
                for r in PREF.itertuples()]
        ov = input.c_overlay()
        series = infra_series(PTS, ov) if ov != "none" else []
        strip = legend_strip(series) if ov != "none" else ui.HTML("")
        return ui.TagList(strip, T.highmap(
            vals, subtitle="", scale=scale, point_series=series,
            show_labels=input.c_labels(), value_suffix=suff.get(ind, ""), height=540))

    # ==================================================================
    #  AUTEUR
    # ==================================================================
    @render.ui
    def tab_auteur():
        lang = L()
        hood = "".join(f"<li>{x}</li>" for x in I.t(lang, "au_hood_list"))
        srcs = "".join(f"<li>{x}</li>" for x in I.t(lang, "au_sources_list"))
        rate = f"{META['taux_croissance']*100:.1f}"
        about_pop = t("au_pop", y=META["annee_pop"], r=rate)
        return ui.div(
            ui.div(
                panel("user", "au_profile", ui.HTML(f"""
                    <div class="photo-ph" style="height:220px"><span class="ic" style="font-size:34px">
                    {ic('camera')}</span><div>{t('au_photo')}</div></div>
                    <h3 style="text-align:center;color:#0B6E4F;margin:12px 0 2px">Maurice Kodjo SEKOU</h3>
                    <p style="text-align:center;color:#D21034;font-weight:700;margin:0">{t('au_role')}</p>
                    <p style="text-align:center;font-size:13px">sekoukodjo4@gmail.com</p>
                    <div style="text-align:center">
                      <span class="badge" style="background:#0B6E4F;margin:2px">Statistique</span>
                      <span class="badge" style="background:#008751;margin:2px">Python</span>
                      <span class="badge" style="background:#FFCE00;color:#1c2b27;margin:2px">R / Shiny</span>
                      <span class="badge" style="background:#D21034;margin:2px">SIG / GIS</span>
                      <span class="badge" style="background:#4c5a55;margin:2px">Machine Learning</span>
                    </div>""")),
                ui.div(
                    panel("circle-info", "au_about", ui.HTML(
                        f"<p style='font-size:14px;line-height:1.6'>{t('au_about_txt')}</p>"
                        f"<p style='font-size:13px;color:#41524c'>{about_pop}</p>")),
                    ui.div(
                        panel("gear", "au_hood", ui.HTML(
                            f"<ul style='font-size:13px;line-height:1.7'>{hood}</ul>")),
                        panel("database", "au_sources", ui.HTML(
                            f"<ul style='font-size:13px;line-height:1.7'>{srcs}</ul>")),
                        class_="grid-2")),
                class_="author-wrap"))


app = App(app_ui, server, static_assets=Path(__file__).parent / "www")
