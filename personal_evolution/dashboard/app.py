"""Tableau de bord analytique PEI (Shiny for Python).

Lancement : python run.py dashboard   puis http://127.0.0.1:8001
Lit la même base SQLite que l'API, avec les mêmes fonctions d'analyse.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.ml import predict  # noqa: E402
from backend import icons  # noqa: E402
from backend import models as m  # noqa: E402
from backend.db import init_engine, session_scope  # noqa: E402
from backend.domain import DIMENSIONS, HORIZONS, INTENTION_STATUSES, dimension_label  # noqa: E402
from backend.services import analytics, ask  # noqa: E402
from backend.services import skills as skill_service  # noqa: E402

init_engine()

GREEN, YELLOW, RED = icons.TOGO_GREEN, icons.TOGO_YELLOW, icons.TOGO_RED
PALETTE = [GREEN, YELLOW, RED, "#2E9C7A", "#B58F00", "#8C0B23", "#7FC8B0", "#5B6A63"]
DIM_COLORS = dict(zip(DIMENSIONS, [YELLOW, RED, GREEN, "#004B37", "#5B6A63", "#8C0B23", "#B58F00"]))
STATUS_COLORS = {"realise": GREEN, "partiel": YELLOW, "non_realise": RED, "abandonne": "#8C0B23", "reporte": "#5B6A63",
                 "prevu": "#C9D3CD"}


def ic(name: str, size: int = 20, color: str = "currentColor") -> ui.HTML:
    return ui.HTML(icons.svg(name, size=size, color=color))


def layout(fig: go.Figure, height: int = 360, title: str | None = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=height, colorway=PALETTE, margin=dict(l=40, r=20, t=50 if title else 20, b=40),
        font=dict(family="system-ui, Segoe UI, Roboto, sans-serif", size=13, color="#10231C"),
        title=dict(text=title, font=dict(size=15)) if title else None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), hoverlabel=dict(font_size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(gridcolor="#E3E9E5")
    fig.update_yaxes(gridcolor="#E3E9E5")
    return fig


def empty_fig(msg: str = "Pas encore assez de données") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color="#5B6A63"), x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return layout(fig, 260)


CSS = f"""
:root {{ --g:{GREEN}; --y:{YELLOW}; --r:{RED}; }}
body {{ background:#F4F6F2; }}
.pei-head {{ display:flex; align-items:center; gap:14px; padding:14px 22px; background:var(--g); color:#fff; }}
.pei-head h1 {{ font-size:20px; margin:0; font-weight:700; }}
.pei-head small {{ opacity:.85; }}
.pei-band {{ height:6px; background:linear-gradient(90deg, var(--r) 0 30%, var(--y) 30% 44%, var(--g) 44% 58%, var(--y) 58% 72%, var(--g) 72% 86%, var(--y) 86% 100%); }}
.nav-underline .nav-link.active, .nav-pills .nav-link.active {{ color:var(--g)!important; border-bottom-color:var(--y)!important; font-weight:700; }}
.nav-link {{ color:#40514A; display:flex; gap:6px; align-items:center; }}
.card {{ border-radius:14px; border:1px solid #DFE6E0; box-shadow:0 1px 2px rgba(16,35,28,.05); }}
.card-header {{ background:#fff; font-weight:700; display:flex; gap:8px; align-items:center; color:#10231C; }}
.card-header svg {{ color:var(--g); }}
.bslib-value-box .value-box-value {{ color:var(--g); font-weight:800; }}
.bslib-value-box .value-box-showcase svg {{ color:var(--g); }}
.vb-yellow .value-box-showcase svg {{ color:#B58F00!important; }}
.vb-red .value-box-showcase svg {{ color:var(--r)!important; }}
.btn-primary {{ background:var(--g); border-color:var(--g); }}
.btn-primary:hover {{ background:#004B37; border-color:#004B37; }}
.btn-warning {{ background:var(--y); border-color:var(--y); color:#1d1a00; }}
.insight {{ display:flex; gap:12px; padding:10px 0; border-bottom:1px solid #EEF2EF; }}
.insight .ib {{ width:38px; height:38px; border-radius:10px; background:#FFF6CC; color:#8A6D00; display:grid; place-items:center; flex:none; }}
.insight b {{ display:block; }}
.caveat {{ font-size:12px; color:#5B6A63; display:flex; gap:5px; align-items:center; margin-top:3px; }}
.note {{ font-size:13px; color:#5B6A63; display:flex; gap:6px; align-items:center; }}
.tag {{ display:inline-block; font-size:12px; font-weight:600; padding:2px 8px; border-radius:99px; background:#E3F1EC; color:var(--g); margin-right:6px; }}
.tag.y {{ background:#FFF6CC; color:#7A6100; }} .tag.r {{ background:#FBE3E8; color:var(--r); }}
table.dataframe, .pei-table {{ width:100%; font-size:13px; }}
.pei-table th {{ color:#5B6A63; font-weight:600; border-bottom:2px solid var(--y); padding:6px; text-align:left; }}
.pei-table td {{ padding:6px; border-bottom:1px solid #EEF2EF; vertical-align:top; }}
.bar {{ height:8px; background:#E3E9E5; border-radius:99px; overflow:hidden; min-width:80px; }}
.bar i {{ display:block; height:100%; background:var(--g); }}
"""


def table(rows: list[dict], cols: list[tuple[str, str]]) -> ui.HTML:
    if not rows:
        return ui.HTML('<p class="note">Aucune donnée.</p>')
    head = "".join(f"<th>{label}</th>" for _, label in cols)
    body = "".join("<tr>" + "".join(f"<td>{'' if r.get(k) is None else r.get(k)}</td>" for k, _ in cols) + "</tr>" for r in rows)
    return ui.HTML(f'<table class="pei-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')


def nav_title(icon_name: str, text: str):
    return ui.span(ic(icon_name, 18), text)


def card(icon_name: str, title: str, *body, full_screen: bool = False):
    return ui.card(ui.card_header(ic(icon_name, 18), title), *body, full_screen=full_screen)


metric_choices = {k: v for k, v in analytics.METRIC_LABELS.items()}
dim_choices = {k: v["label"] for k, v in DIMENSIONS.items()}

app_ui = ui.page_fillable(
    ui.tags.style(CSS),
    ui.div(ui.div(class_="pei-band")),
    ui.div(
        ui.HTML(icons.logo_svg(44)),
        ui.div(ui.h1("Personal Evolution Intelligence"), ui.tags.small("Tableau de bord analytique, entièrement local")),
        class_="pei-head",
    ),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("period", ui.span(ic("calendar", 16), " Période"),
                            {"30": "30 derniers jours", "90": "3 derniers mois", "180": "6 derniers mois",
                             "365": "12 derniers mois", "all": "Tout l'historique", "custom": "Personnalisée"}, selected="90"),
            ui.panel_conditional("input.period === 'custom'",
                                 ui.input_date_range("custom_range", "Du ... au", start=date.today() - timedelta(days=60),
                                                     end=date.today(), language="fr", separator=" au ")),
            ui.input_action_button("refresh", ui.span(ic("refresh", 16), " Actualiser"), class_="btn-primary"),
            ui.hr(),
            ui.output_ui("sidebar_info"),
            width=260, bg="#FFFFFF",
        ),
        ui.navset_underline(
            ui.nav_panel(
                nav_title("home", "Vue générale"),
                ui.output_ui("kpis"),
                ui.layout_columns(
                    card("layers", "Temps quotidien par dimension", output_widget("fig_daily_dims"), full_screen=True),
                    card("target", "Taux de réalisation (moyenne glissante 7 jours)", output_widget("fig_completion"), full_screen=True),
                    col_widths=[7, 5],
                ),
                ui.layout_columns(
                    card("chart", "Activités principales", output_widget("fig_top")),
                    card("bulb", "Ce que montrent tes données", ui.output_ui("insights")),
                    card("star", "Événements marquants", ui.output_ui("highlights")),
                    col_widths=[4, 5, 3],
                ),
            ),
            ui.nav_panel(
                nav_title("trend_up", "Évolution"),
                ui.layout_columns(
                    ui.input_selectize("evo_metrics", "Indicateurs", metric_choices, multiple=True,
                                       selected=["completion_rate", "mood", "energy"]),
                    ui.input_radio_buttons("evo_freq", "Échelle", {"D": "Jour", "W": "Semaine", "M": "Mois"}, selected="W", inline=True),
                    col_widths=[8, 4],
                ),
                card("trend_up", "Évolution des indicateurs", output_widget("fig_evolution"), full_screen=True),
                ui.layout_columns(
                    card("calendar", "Calendrier de régularité", output_widget("fig_heat")),
                    card("route", "Comparer deux périodes",
                         ui.layout_columns(
                             ui.input_date_range("cmp_a", "Période A", start=date.today() - timedelta(days=59),
                                                 end=date.today() - timedelta(days=30), language="fr", separator=" au "),
                             ui.input_date_range("cmp_b", "Période B", start=date.today() - timedelta(days=29),
                                                 end=date.today(), language="fr", separator=" au "),
                         ),
                         ui.output_ui("compare")),
                    col_widths=[6, 6],
                ),
            ),
            ui.nav_panel(
                nav_title("target", "Objectifs"),
                ui.layout_columns(
                    card("star", "Vision et objectifs", ui.output_ui("goals_tree")),
                    card("chart", "Statut des intentions par semaine", output_widget("fig_status")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    card("hourglass", "Temps prévu et temps réel", output_widget("fig_calibration"), full_screen=True),
                    card("clock", "Calibration par type de tâche", ui.output_ui("calibration_table")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    card("alert", "Objectifs souvent abandonnés", output_widget("fig_abandons")),
                    card("message", "Raisons citées", output_widget("fig_reasons")),
                    col_widths=[7, 5],
                ),
            ),
            ui.nav_panel(
                nav_title("grid", "Dimensions"),
                ui.input_radio_buttons("dim", None, dim_choices, selected="etudes", inline=True),
                ui.output_ui("dim_kpis"),
                ui.layout_columns(
                    card("chart", "Temps hebdomadaire", output_widget("fig_dim_week")),
                    card("layers", "Répartition des activités", output_widget("fig_dim_cats")),
                    col_widths=[7, 5],
                ),
                card("message", "Réflexions de cette dimension", ui.output_ui("dim_reflections")),
            ),
            ui.nav_panel(
                nav_title("graduation", "Compétences"),
                ui.layout_columns(
                    card("graduation", "Auto évaluation dans le temps", output_widget("fig_skill_rating"), full_screen=True),
                    card("clock", "Heures de pratique par mois", output_widget("fig_skill_hours"), full_screen=True),
                    col_widths=[6, 6],
                ),
                card("check_circle", "Ressenti et preuves observables", ui.output_ui("skills_table")),
            ),
            ui.nav_panel(
                nav_title("flask", "Analyse"),
                ui.div(ic("info", 16), ui.span(analytics.CAUSALITY_NOTE), class_="note", style="margin:8px 0 12px"),
                ui.layout_columns(
                    card("link", "Corrélations (Spearman)", output_widget("fig_corr"), full_screen=True),
                    card("link", "Associations les plus nettes", ui.output_ui("corr_table")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    card("trend_up", "Tendances récentes", ui.output_ui("trends")),
                    card("alert", "Jours atypiques", ui.output_ui("anomalies")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    card("calendar", "Profil de la semaine", output_widget("fig_weekday")),
                    card("target", "Nombre d'intentions et réalisation", output_widget("fig_load")),
                    col_widths=[6, 6],
                ),
                card("flask", "Expériences personnelles", ui.output_ui("experiments")),
            ),
            ui.nav_panel(
                nav_title("cpu", "Prédiction"),
                ui.div(ic("info", 16), ui.span("Les prédictions sont des estimations fondées sur ton historique, jamais des certitudes."),
                       class_="note", style="margin:8px 0 12px"),
                ui.layout_columns(
                    card("route", "Simulation de scénario",
                         ui.input_selectize("sim_cat", "Activité", choices=[], options={"create": True}),
                         ui.layout_columns(ui.input_numeric("sim_min", "Minutes par jour", 90, min=5, max=600),
                                           ui.input_numeric("sim_days", "Durée (jours)", 90, min=7, max=3650)),
                         ui.input_slider("sim_week", "Jours par semaine", 1, 7, 6),
                         ui.input_action_button("sim_go", ui.span(ic("play", 16), " Simuler"), class_="btn-warning"),
                         ui.output_ui("sim_text")),
                    card("chart", "Distribution simulée des heures totales", output_widget("fig_sim"), full_screen=True),
                    col_widths=[4, 8],
                ),
                card("cpu", "Modèle de réalisation des intentions", ui.output_ui("model_info")),
            ),
            ui.nav_panel(
                nav_title("archive", "Mémoire"),
                ui.layout_columns(
                    ui.input_text("q", None, placeholder="Qu'est ce qui m'a marqué le mois dernier ?", width="100%"),
                    ui.input_action_button("q_go", ui.span(ic("search", 16), " Interroger"), class_="btn-primary"),
                    col_widths=[10, 2],
                ),
                ui.output_ui("memory"),
            ),
            id="tabs",
        ),
    ),
    title="PEI Tableau de bord",
    padding=0,
    gap=0,
)


def server(input, output, session):
    @reactive.calc
    def period() -> tuple[date | None, date | None]:
        input.refresh()
        p = input.period()
        if p == "all":
            return None, None
        if p == "custom":
            a, b = input.custom_range()
            return a, b
        return date.today() - timedelta(days=int(p) - 1), date.today()

    @reactive.calc
    def data():
        start, end = period()
        with session_scope() as s:
            fr = analytics.load_frames(s, start, end)
            daily = analytics.daily_series(fr, start, end) if start else analytics.daily_series(fr)
            summ = analytics.summary(s, start, end)
            ins = analytics.insights(s, start, end)
            goals = analytics.goals_progress(s)
        return {"fr": fr, "daily": daily, "summary": summ, "insights": ins, "goals": goals}

    @reactive.calc
    def full():
        input.refresh()
        with session_scope() as s:
            fr = analytics.load_frames(s)
        return fr

    @render.ui
    def sidebar_info():
        input.refresh()
        with session_scope() as s:
            n_days = s.query(m.Day).count()
            first = s.query(m.Day.date).order_by(m.Day.date).first()
        return ui.div(
            ui.p(ic("archive", 16), f" {n_days} journées enregistrées", class_="note"),
            ui.p(ic("calendar", 16), f" depuis le {first[0].strftime('%d/%m/%Y')}" if first else " aucune donnée", class_="note"),
            ui.p(ic("shield", 16), " Données stockées sur ce PC uniquement", class_="note"),
        )

    # Vue générale

    @render.ui
    def kpis():
        s = data()["summary"]
        if s.get("empty"):
            return ui.p("Aucune donnée sur cette période. Commence par saisir tes intentions depuis le téléphone.", class_="note")

        def pct(x):
            return "n.d." if x is None else f"{round(x * 100)} %"
        boxes = [
            ("calendar", "Régularité", pct(s["regularity"]), f"{s['n_logged_days']} jours sur {s['n_days']}", ""),
            ("target", "Réalisation", pct(s["completion_rate"]), f"{s['n_done']} sur {s['n_reviewed']} intentions", "vb-yellow"),
            ("clock", "Temps suivi", f"{s['total_hours']} h", f"{s['n_intentions']} intentions", ""),
            ("flag", "Série en cours", f"{s['current_streak']} j", f"record {s['longest_streak']} j", "vb-red"),
            ("smile", "Humeur moyenne", s["avg_mood"] if s["avg_mood"] is not None else "n.d.", f"énergie {s['avg_energy']}", "vb-yellow"),
            ("bed", "Sommeil moyen", f"{s['avg_sleep']} h" if s["avg_sleep"] else "n.d.", "par nuit", ""),
        ]
        return ui.layout_columns(*[ui.value_box(t, v, sub, showcase=ic(icn, 34), class_=cls)
                                   for icn, t, v, sub, cls in boxes], col_widths=[2] * 6)

    @render_plotly
    def fig_daily_dims():
        d = data()["daily"]
        if d.empty:
            return empty_fig()
        fig = go.Figure()
        for dim in DIMENSIONS:
            col = f"min_{dim}"
            if d[col].sum() > 0:
                fig.add_bar(x=d.index, y=d[col] / 60, name=dimension_label(dim), marker_color=DIM_COLORS[dim])
        fig.update_layout(barmode="stack", yaxis_title="heures")
        return layout(fig)

    @render_plotly
    def fig_completion():
        d = data()["daily"]
        if d.empty or d["completion_rate"].notna().sum() < 2:
            return empty_fig()
        roll = d["completion_rate"].rolling(7, min_periods=3).mean() * 100
        fig = go.Figure()
        fig.add_scatter(x=d.index, y=d["completion_rate"] * 100, mode="markers", name="jour", marker=dict(color=YELLOW, size=6))
        fig.add_scatter(x=d.index, y=roll, mode="lines", name="moyenne 7 jours", line=dict(color=GREEN, width=3))
        fig.update_layout(yaxis=dict(range=[0, 105], title="%"))
        return layout(fig)

    @render_plotly
    def fig_top():
        top = data()["summary"].get("top_categories") or []
        if not top:
            return empty_fig()
        top = list(reversed(top[:8]))
        fig = go.Figure(go.Bar(x=[t["hours"] for t in top], y=[t["category"] for t in top], orientation="h",
                               marker_color=[DIM_COLORS.get(t["dimension"], GREEN) for t in top],
                               text=[f"{t['hours']} h" for t in top], textposition="auto"))
        fig.update_layout(xaxis_title="heures")
        return layout(fig, 330)

    @render.ui
    def insights():
        ins = data()["insights"]
        if not ins:
            return ui.p("Les recommandations apparaîtront avec quelques semaines de données.", class_="note")
        return ui.div(*[ui.div(ui.div(ic(i.get("icon", "bulb"), 20), class_="ib"),
                               ui.div(ui.tags.b(i["title"]), ui.span(i["message"]),
                                      ui.div(ic("info", 13), i.get("caveat", ""), class_="caveat")),
                               class_="insight") for i in ins[:6]],
                      style="max-height:340px;overflow:auto")

    @render.ui
    def highlights():
        hl = data()["summary"].get("highlights") or []
        if not hl:
            return ui.p("Aucun événement marquant.", class_="note")
        return ui.div(*[ui.div(ui.tags.span(pd.Timestamp(h["date"]).strftime("%d/%m"), class_="tag y"), h["content"],
                               style="padding:6px 0;border-bottom:1px solid #EEF2EF;font-size:14px") for h in hl],
                      style="max-height:340px;overflow:auto")

    # Évolution

    @render_plotly
    def fig_evolution():
        d = data()["daily"]
        metrics = input.evo_metrics()
        if d.empty or not metrics:
            return empty_fig()
        freq = input.evo_freq()
        sums = {c for c in d.columns if c.startswith("min_")} | {"actual_minutes", "planned_minutes", "n_intentions", "n_done"}
        fig = go.Figure()
        for i, col in enumerate(metrics):
            s = d[col].astype(float)
            if freq != "D":
                rule = "W-MON" if freq == "W" else "MS"
                s = s.resample(rule).sum(min_count=1) if col in sums else s.resample(rule).mean()
            if col == "completion_rate":
                s = s * 100
            fig.add_scatter(x=s.index, y=s.values, mode="lines+markers", name=analytics.METRIC_LABELS.get(col, col),
                            line=dict(width=3, color=PALETTE[i % len(PALETTE)]), yaxis="y" if i == 0 else "y2")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False))
        return layout(fig, 420)

    @render_plotly
    def fig_heat():
        d = data()["daily"]
        if d.empty:
            return empty_fig()
        z = d["completion_rate"].copy()
        z[~d["logged"]] = None
        frame = pd.DataFrame({"z": z * 100, "dow": d.index.dayofweek, "week": d.index.to_period("W").start_time})
        piv = frame.pivot_table(index="dow", columns="week", values="z", aggfunc="mean", dropna=False)
        piv = piv.reindex(range(7))
        fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
                                   colorscale=[[0, RED], [0.5, YELLOW], [1, GREEN]], zmin=0, zmax=100, xgap=2, ygap=2,
                                   colorbar=dict(title="%"), hoverongaps=False))
        fig.update_yaxes(autorange="reversed")
        return layout(fig, 300)

    @render.ui
    def compare():
        a, b = input.cmp_a(), input.cmp_b()
        if not all(a) or not all(b):
            return ui.p("Choisis deux périodes.", class_="note")
        input.refresh()
        with session_scope() as s:
            res = analytics.compare_periods(s, a, b)
        sa, sb, diff = res["a"], res["b"], res["difference"]
        if sa.get("empty") or sb.get("empty"):
            return ui.p("Une des périodes ne contient pas de données.", class_="note")
        rows = []
        for key, label, factor, unit in [("regularity", "Régularité", 100, " %"), ("completion_rate", "Réalisation", 100, " %"),
                                         ("total_hours", "Heures suivies", 1, " h"), ("avg_mood", "Humeur", 1, ""),
                                         ("avg_energy", "Énergie", 1, ""), ("avg_sleep", "Sommeil", 1, " h"),
                                         ("n_intentions", "Intentions", 1, "")]:
            va, vb, dv = sa.get(key), sb.get(key), diff.get(key)
            fmt = lambda v: "n.d." if v is None else f"{round(v * factor, 1):g}{unit}"  # noqa: E731
            sign = "" if dv is None else ("tag" if dv > 0 else "tag r" if dv < 0 else "tag y")
            rows.append({"k": label, "a": fmt(va), "b": fmt(vb),
                         "d": "" if dv is None else f'<span class="{sign}">{"+" if dv > 0 else ""}{round(dv * factor, 1):g}{unit}</span>'})
        return table(rows, [("k", "Indicateur"), ("a", "Période A"), ("b", "Période B"), ("d", "Écart")])

    # Objectifs

    @render.ui
    def goals_tree():
        goals = data()["goals"]
        if not goals:
            return ui.p("Aucun objectif. Ajoute ta vision depuis le téléphone.", class_="note")
        children: dict = {}
        for g in goals:
            children.setdefault(g["parent_id"], []).append(g)
        order = list(HORIZONS)

        def node(g, depth=0):
            rate = g["completion_rate"]
            status_cls = {"atteint": "tag", "actif": "tag y", "abandonne": "tag r"}.get(g["status"], "tag")
            dim_icon = DIMENSIONS.get(g["dimension"] or "", {}).get("icon", "star")
            rate_txt = f", {round(rate * 100)} % réalisé" if rate is not None else ""
            since = g["days_since_last_action"]
            since_txt = f", dernière action il y a {since} j" if since is not None else ""
            horizon = HORIZONS.get(g["horizon"], g["horizon"])
            status = g["status"].replace("_", " ")
            html = (f'<div style="margin-left:{depth * 18}px;padding:7px 0;border-bottom:1px solid #EEF2EF">'
                    f'{icons.svg(dim_icon, 16, GREEN)} <b>{g["title"]}</b> <span class="tag y">{horizon}</span>'
                    f'<span class="{status_cls}">{status}</span>'
                    f'<div class="note">{g["n_intentions"]} actions, {g["hours"]} h{rate_txt}{since_txt}</div></div>')
            for c in sorted(children.get(g["id"], []), key=lambda x: order.index(x["horizon"]) if x["horizon"] in order else 9):
                html += node(c, depth + 1)
            return html
        roots = sorted(children.get(None, []), key=lambda x: order.index(x["horizon"]) if x["horizon"] in order else 9)
        return ui.HTML('<div style="max-height:380px;overflow:auto">' + "".join(node(g) for g in roots) + "</div>")

    @render_plotly
    def fig_status():
        it = data()["fr"].intentions
        if it.empty:
            return empty_fig()
        w = it.assign(week=it["date"].dt.to_period("W").dt.start_time).groupby(["week", "status"])["id"].count().unstack(fill_value=0)
        fig = go.Figure()
        for st in ["realise", "partiel", "reporte", "non_realise", "abandonne", "prevu"]:
            if st in w:
                fig.add_bar(x=w.index, y=w[st], name=INTENTION_STATUSES[st], marker_color=STATUS_COLORS[st])
        fig.update_layout(barmode="stack")
        return layout(fig)

    @render_plotly
    def fig_calibration():
        cal = analytics.calibration(data()["fr"])
        pts = pd.DataFrame(cal.get("points") or [])
        if pts.empty:
            return empty_fig("Indique durées prévues et réelles pour calibrer tes estimations")
        mx = float(max(pts["estimated_minutes"].max(), pts["actual_minutes"].max())) * 1.05
        fig = go.Figure()
        fig.add_scatter(x=[0, mx], y=[0, mx], mode="lines", name="estimation parfaite", line=dict(color="#9AA8A1", dash="dot"))
        for i, (cat, g) in enumerate(pts.groupby("category")):
            fig.add_scatter(x=g["estimated_minutes"], y=g["actual_minutes"], mode="markers", name=cat,
                            marker=dict(size=8, opacity=.7, color=PALETTE[i % len(PALETTE)]), text=g["date"])
        fig.update_layout(xaxis_title="minutes prévues", yaxis_title="minutes réelles")
        return layout(fig, 400)

    @render.ui
    def calibration_table():
        cal = analytics.calibration(data()["fr"])
        if not cal.get("categories"):
            return ui.p("Pas encore de données de calibration.", class_="note")
        rows = [{**c, "bias_tag": f'<span class="tag {"r" if c["bias"] == "sous estimation" else "y" if c["bias"] == "surestimation" else ""}">{c["bias"]}</span>',
                 "ratio": f"x {c['median_ratio']}"} for c in cal["categories"]]
        return ui.div(ui.p(ic("info", 14), " ", cal["overall"]["message"], class_="note"),
                      table(rows, [("category", "Type"), ("n", "Obs."), ("mean_estimated", "Prévu (min)"),
                                   ("mean_actual", "Réel (min)"), ("ratio", "Ratio médian"), ("bias_tag", "Tendance")]),
                      style="max-height:400px;overflow:auto")

    @render_plotly
    def fig_abandons():
        ab = analytics.abandons(data()["fr"])["categories"][:10]
        if not ab:
            return empty_fig()
        ab = list(reversed(ab))
        fig = go.Figure(go.Bar(x=[a["abandon_rate"] * 100 for a in ab], y=[a["category"] for a in ab], orientation="h",
                               marker_color=RED, text=[f"{a['abandoned']}/{a['n']}" for a in ab], textposition="auto"))
        fig.update_layout(xaxis=dict(title="% non réalisé", range=[0, 100]))
        return layout(fig)

    @render_plotly
    def fig_reasons():
        reasons = analytics.abandons(data()["fr"])["reasons"]
        if not reasons:
            return empty_fig("Aucune raison renseignée")
        fig = go.Figure(go.Pie(labels=[r["reason"] for r in reasons], values=[r["count"] for r in reasons], hole=.55,
                               marker=dict(colors=PALETTE)))
        return layout(fig)

    # Dimensions

    @render.ui
    def dim_kpis():
        dim = input.dim()
        s = data()["summary"]
        if s.get("empty"):
            return ui.div()
        d = next((x for x in s["dimensions"] if x["dimension"] == dim), None)
        rate = "n.d." if d["completion_rate"] is None else f"{round(d['completion_rate'] * 100)} %"
        return ui.layout_columns(
            ui.value_box("Temps consacré", f"{d['hours']} h", showcase=ic(d["icon"], 34)),
            ui.value_box("Intentions", d["n_intentions"], showcase=ic("target", 34), class_="vb-yellow"),
            ui.value_box("Réalisation", rate, showcase=ic("check_circle", 34)),
            ui.value_box("Séances", d["n_activities"], showcase=ic("layers", 34), class_="vb-red"),
            col_widths=[3, 3, 3, 3],
        )

    @render_plotly
    def fig_dim_week():
        d = data()["daily"]
        col = f"min_{input.dim()}"
        if d.empty or d[col].sum() == 0:
            return empty_fig()
        w = d[col].resample("W-MON").sum() / 60
        fig = go.Figure(go.Bar(x=w.index, y=w.values, marker_color=DIM_COLORS[input.dim()]))
        trend = w.rolling(4, min_periods=2).mean()
        fig.add_scatter(x=trend.index, y=trend.values, mode="lines", name="moyenne 4 semaines", line=dict(color="#10231C", width=2))
        fig.update_layout(yaxis_title="heures par semaine", showlegend=False)
        return layout(fig)

    @render_plotly
    def fig_dim_cats():
        ac = data()["fr"].activities
        ac = ac[ac["dimension"] == input.dim()] if not ac.empty else ac
        if ac.empty:
            return empty_fig()
        g = ac.groupby("category")["minutes"].sum().sort_values(ascending=False).head(8)
        fig = go.Figure(go.Pie(labels=g.index, values=g.values / 60, hole=.55, marker=dict(colors=PALETTE)))
        return layout(fig)

    @render.ui
    def dim_reflections():
        rf = data()["fr"].reflections
        rf = rf[rf["dimension"] == input.dim()] if not rf.empty else rf
        if rf.empty:
            return ui.p("Aucune réflexion pour cette dimension sur la période.", class_="note")
        rows = [{"date": r.date.strftime("%d/%m/%Y"), "kind": f'<span class="tag y">{r.kind}</span>', "content": r.content}
                for r in rf.sort_values("date", ascending=False).head(40).itertuples()]
        return ui.div(table(rows, [("date", "Date"), ("kind", "Type"), ("content", "Contenu")]), style="max-height:320px;overflow:auto")

    # Compétences

    @reactive.calc
    def skills_data():
        input.refresh()
        with session_scope() as s:
            out = []
            for sk in s.query(m.Skill).order_by(m.Skill.name).all():
                summ = skill_service.summary(s, sk)
                summ["projection"] = predict.skill_projection(summ["timeline"])
                out.append(summ)
        return out

    @render_plotly
    def fig_skill_rating():
        sk = skills_data()
        if not sk:
            return empty_fig("Aucune compétence suivie")
        fig = go.Figure()
        for i, s in enumerate(sk):
            pts = [t for t in s["timeline"] if t["self_rating"] is not None]
            if pts:
                fig.add_scatter(x=[p["date"] for p in pts], y=[p["self_rating"] for p in pts], mode="lines+markers",
                                name=s["name"], line=dict(width=3, color=PALETTE[i % len(PALETTE)]))
        fig.update_layout(yaxis=dict(range=[0, 5.2], title="niveau déclaré"))
        return layout(fig)

    @render_plotly
    def fig_skill_hours():
        sk = skills_data()
        if not sk:
            return empty_fig("Aucune compétence suivie")
        fig = go.Figure()
        for i, s in enumerate(sk):
            if s["hours_by_month"]:
                fig.add_bar(x=[h["month"] for h in s["hours_by_month"]], y=[h["hours"] for h in s["hours_by_month"]],
                            name=s["name"], marker_color=PALETTE[i % len(PALETTE)])
        fig.update_layout(barmode="group", yaxis_title="heures")
        return layout(fig)

    @render.ui
    def skills_table():
        sk = skills_data()
        rows = []
        for s in sk:
            proj = s["projection"]
            rows.append({
                "name": f"<b>{s['name']}</b>", "rating": "n.d." if s["current_rating"] is None else f"{s['current_rating']}/5",
                "change": "" if s["rating_change"] is None else f"{'+' if s['rating_change'] > 0 else ''}{s['rating_change']:.1f}",
                "hours": f"{s['hours']} h", "sessions": s["n_activities"], "score": s["latest_objective_score"],
                "evidence": ", ".join(f"{v} {k}" for k, v in s["evidence"].items()),
                "proj": "" if not proj else f"{proj['projected']}/5 <span class='note'>[{proj['interval'][0]} ; {proj['interval'][1]}]</span>",
            })
        return table(rows, [("name", "Compétence"), ("rating", "Ressenti"), ("change", "Évolution"), ("hours", "Pratique"),
                            ("sessions", "Séances"), ("score", "Score objectif"), ("evidence", "Preuves"), ("proj", "Projection 3 mois")])

    # Analyse

    @render_plotly
    def fig_corr():
        c = analytics.correlations(data()["daily"])
        mat = c.get("matrix") or {}
        if not mat.get("values"):
            return empty_fig("Au moins 14 jours renseignés sont nécessaires")
        fig = go.Figure(go.Heatmap(z=mat["values"], x=mat["columns"], y=mat["columns"], zmin=-1, zmax=1,
                                   colorscale=[[0, RED], [0.5, "#FFFFFF"], [1, GREEN]], colorbar=dict(title="rho")))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(tickangle=-40)
        return layout(fig, 480)

    @render.ui
    def corr_table():
        c = analytics.correlations(data()["daily"])
        pairs = c["pairs"][:14]
        rows = [{"pair": f"{p['x_label']} et {p['y_label']}", "rho": p["rho"], "n": p["n"], "q": p["q_value"],
                 "sig": '<span class="tag">nette</span>' if p["significant"] else '<span class="tag y">incertaine</span>'}
                for p in pairs]
        return ui.div(table(rows, [("pair", "Variables"), ("rho", "rho"), ("n", "Jours"), ("q", "q (BH)"), ("sig", "Lecture")]),
                      ui.p(ic("info", 14), " q est la p valeur corrigée pour les tests multiples (Benjamini Hochberg).", class_="note"),
                      style="max-height:480px;overflow:auto")

    @render.ui
    def trends():
        t = analytics.trends(data()["daily"], fr=data()["fr"])
        if not t:
            return ui.p("Aucune tendance nette sur les 3 dernières semaines.", class_="note")
        return ui.div(*[ui.div(ic("trend_up" if x["direction"] == "hausse" else "trend_down", 20,
                                  GREEN if x["direction"] == "hausse" else RED), " ", x["message"],
                               ui.span(f" p = {x['p_value']}", class_="note"),
                               style="padding:6px 0;border-bottom:1px solid #EEF2EF") for x in t])

    @render.ui
    def anomalies():
        an = analytics.anomalies(data()["daily"])[:25]
        rows = [{**a, "dir": f'<span class="tag {"" if a["direction"] == "haut" else "r"}">{a["direction"]}</span>'} for a in an]
        return ui.div(table(rows, [("date", "Date"), ("label", "Indicateur"), ("value", "Valeur"), ("expected", "Habituel"),
                                   ("dir", "Écart")]), style="max-height:320px;overflow:auto")

    @render_plotly
    def fig_weekday():
        wd = analytics.weekday_profile(data()["daily"])
        if not wd:
            return empty_fig()
        fig = go.Figure()
        fig.add_bar(x=[w["weekday"] for w in wd], y=[(w["completion_rate"] or 0) * 100 for w in wd], name="réalisation (%)",
                    marker_color=GREEN)
        fig.add_scatter(x=[w["weekday"] for w in wd], y=[w["actual_minutes"] for w in wd], name="minutes suivies",
                        yaxis="y2", mode="lines+markers", line=dict(color=YELLOW, width=3))
        fig.update_layout(yaxis=dict(title="%"), yaxis2=dict(overlaying="y", side="right", showgrid=False, title="min"))
        return layout(fig)

    @render_plotly
    def fig_load():
        d = data()["daily"]
        d = d[d["n_closed"] > 0]
        if d.empty:
            return empty_fig()
        g = d.groupby("n_intentions")["completion_rate"].agg(["mean", "count"]).reset_index()
        fig = go.Figure(go.Bar(x=g["n_intentions"], y=g["mean"] * 100, marker_color=[GREEN if v >= .6 else YELLOW if v >= .4 else RED for v in g["mean"]],
                               text=[f"{c} j" for c in g["count"]], textposition="auto"))
        fig.update_layout(xaxis_title="intentions fixées le matin", yaxis_title="réalisation moyenne (%)")
        return layout(fig)

    @render.ui
    def experiments():
        input.refresh()
        with session_scope() as s:
            exps = [(e.title, e.hypothesis, analytics.experiment_analysis(s, e)) for e in s.query(m.Experiment).all()]
        if not exps:
            return ui.p("Aucune expérience. Formule une hypothèse depuis le téléphone (Journal).", class_="note")
        rows = [{"t": f"<b>{t}</b><div class='note'>{h}</div>", "m": a.get("label"),
                 "b": f"{a.get('baseline_mean')} ({a.get('n_baseline')} j)", "e": f"{a.get('experiment_mean')} ({a.get('n_experiment')} j)",
                 "r": a.get("message")} for t, h, a in exps]
        return ui.div(table(rows, [("t", "Expérience"), ("m", "Indicateur"), ("b", "Avant"), ("e", "Pendant"), ("r", "Lecture")]),
                      ui.p(ic("info", 14), " ", analytics.CAUSALITY_NOTE, class_="note"))

    # Prédiction

    @reactive.effect
    def _sim_choices():
        fr = full()
        cats = sorted(set(fr.activities["category"].dropna())) if not fr.activities.empty else []
        ui.update_selectize("sim_cat", choices=cats, selected="Python" if "Python" in cats else (cats[0] if cats else None))

    @reactive.calc
    @reactive.event(input.sim_go, ignore_none=False)
    def sim():
        fr = full()
        cat = input.sim_cat() or None
        dim = None
        if cat and not fr.activities.empty:
            dims = fr.activities.loc[fr.activities["category"] == cat, "dimension"].dropna()
            dim = dims.mode().iloc[0] if not dims.empty else None
        return predict.simulate_scenario(fr.intentions, fr.activities, category=cat, dimension=dim,
                                         minutes_per_day=int(input.sim_min() or 60), days=int(input.sim_days() or 90),
                                         days_per_week=int(input.sim_week()))

    @render.ui
    def sim_text():
        r = sim()
        return ui.div(ui.hr(), ui.p(r["message"]), ui.p(ic("info", 14), " ", r["disclaimer"], class_="note"))

    @render_plotly
    def fig_sim():
        r = sim()
        edges = r["histogram_edges"]
        mids = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
        fig = go.Figure(go.Bar(x=mids, y=r["histogram"], marker_color=GREEN, name="simulations"))
        for v, name, col in [(r["hours_p10"], "prudent", RED), (r["hours_median"], "médian", "#10231C"),
                             (r["hours_p90"], "favorable", YELLOW), (r["ideal_hours"], "si tout est réalisé", "#9AA8A1")]:
            fig.add_vline(x=v, line=dict(color=col, width=2, dash="dash"), annotation_text=f"{name} {v:g} h",
                          annotation_position="top")
        fig.update_layout(xaxis_title="heures totales", yaxis_title="nombre de simulations", showlegend=False)
        return layout(fig, 420)

    @render.ui
    def model_info():
        fr = full()
        mdl = predict.fit_completion(fr.intentions, fr.days)
        if mdl.kind == "aucune_donnee":
            return ui.p("Aucune intention évaluée pour le moment.", class_="note")
        parts = [ui.p(ui.tags.b("Modèle : "), {"taux_de_base": "taux de base lissés (historique encore court)",
                                                 "regression_logistique": "régression logistique"}[mdl.kind],
                      f", entraîné sur {mdl.n} intentions évaluées.")]
        if mdl.auc:
            parts.append(ui.p(ui.tags.b("Qualité en validation temporelle (AUC) : "), f"{mdl.auc:.2f}",
                              ui.span(" (0,5 = hasard, 1 = parfait)", class_="note")))
        rows = sorted([{"k": k[1], "type": "catégorie" if k[0] == "category" else "dimension", "rate": f"{round(v['rate'] * 100)} %",
                        "n": v["n"]} for k, v in mdl.base_rates.items() if k[0] == "category"], key=lambda r: -r["n"])[:15]
        parts.append(table(rows, [("k", "Type d'activité"), ("rate", "Probabilité estimée de réalisation"), ("n", "Observations")]))
        return ui.div(*parts)

    # Mémoire

    @render.ui
    @reactive.event(input.q_go)
    def memory():
        q = input.q().strip()
        if not q:
            return ui.p("Pose une question ou cherche un mot.", class_="note")
        with session_scope() as s:
            r = ask.ask(s, q)
        rows = [{"date": it.get("date") or "", "kind": f'<span class="tag">{it["kind_label"]}</span>',
                 "text": str(it["text"]).replace("[", "<mark>").replace("]", "</mark>")} for it in r["items"]]
        return ui.card(ui.card_header(ic("bulb", 18), r["answer"]),
                       ui.p(f"Période : {r['period']}", class_="note"),
                       table(rows, [("date", "Date"), ("kind", "Source"), ("text", "Contenu")]))


app = App(app_ui, server)
