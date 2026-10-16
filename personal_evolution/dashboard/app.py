"""Tableau de bord analytique PEI (Shiny for Python).

Lancement : python run.py dashboard   puis http://127.0.0.1:8001
Lit la même base SQLite que l'API, avec les mêmes fonctions d'analyse.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.ml import predict  # noqa: E402
from backend import i18n, icons  # noqa: E402
from backend import models as m  # noqa: E402
from backend.db import init_engine, session_scope  # noqa: E402
from backend.domain import DIMENSIONS, HORIZONS, INTENTION_STATUSES, GOAL_STATUSES, REFLECTION_KINDS, dimension_label, label as label_of  # noqa: E402
from backend.i18n import tr  # noqa: E402
from backend.services import analytics, ask, auth, export_excel, profile  # noqa: E402
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


def nan_to_none(df: pd.DataFrame) -> list:
    """Les cases vides doivent être None (et non NaN) pour la transmission au navigateur."""
    return df.astype(object).where(df.notna(), None).values.tolist()


def empty_fig(msg: str | None = None) -> go.Figure:
    msg = msg or tr("Pas encore assez de données")
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color="#5B6A63"), x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return layout(fig, 260)


CSS = f"""
:root {{ --g:{GREEN}; --y:{YELLOW}; --r:{RED}; }}
body {{ background:#F4F6F2; }}
.pei-head {{ display:flex; align-items:center; gap:14px; padding:14px 22px; background:var(--g); color:#fff; }}
.head-photo {{ width: 46px; height: 46px; border-radius: 50%; object-fit: cover; box-shadow: 0 0 0 3px var(--y); display: block; }}
.head-user {{ font-size: 13px; opacity: .9; }}
.pei-head h1 {{ font-size:20px; margin:0; font-weight:700; }}
.pei-head small {{ opacity:.85; }}
.head-right {{ margin-left:auto; display:flex; align-items:center; gap:14px; }}
.head-right .shiny-input-container {{ margin:0; width:auto; }}
.head-right .form-check-inline {{ margin-right:6px; }}
.head-right label {{ color:#fff; font-size:13px; }}
.head-right .form-check-input:checked {{ background-color:var(--y); border-color:var(--y); }}
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
        return ui.HTML(f'<p class="note">{tr("Aucune donnée.")}</p>')
    head = "".join(f"<th>{label}</th>" for _, label in cols)
    body = "".join("<tr>" + "".join(f"<td>{'' if r.get(k) is None else r.get(k)}</td>" for k, _ in cols) + "</tr>" for r in rows)
    return ui.HTML(f'<table class="pei-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')


def nav_title(icon_name: str, text: str):
    return ui.span(ic(icon_name, 18), text)


def panel(icon_name: str, text: str, value: str, *body):
    """Onglet avec un identifiant fixe, pour rester sur le même onglet après un changement de langue."""
    return ui.nav_panel(nav_title(icon_name, text), *body, value=value)


def card(icon_name: str, title: str, *body, full_screen: bool = False):
    return ui.card(ui.card_header(ic(icon_name, 18), title), *body, full_screen=full_screen)


def date_range(input_id: str, title: str, start: date, end: date):
    return ui.input_date_range(input_id, title, start=start, end=end, language=i18n.get_lang(),
                               separator=tr(" au "), format="dd/mm/yyyy")


def build_main(keep: dict | None = None):
    """Interface principale, construite dans la langue de la session. keep conserve les choix en cours."""
    keep = keep or {}
    metric_choices = analytics.metric_labels()
    dim_choices = {k: dimension_label(k) for k in DIMENSIONS}
    today = date.today()
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("period", ui.span(ic("calendar", 16), " " + tr("Période")),
                            {"30": tr("30 derniers jours"), "90": tr("3 derniers mois"), "180": tr("6 derniers mois"),
                             "365": tr("12 derniers mois"), "all": tr("Tout l'historique"), "custom": tr("Personnalisée")},
                            selected=keep.get("period", "90")),
            ui.panel_conditional("input.period === 'custom'",
                                 date_range("custom_range", tr("Du ... au"), *keep.get("custom_range", (today - timedelta(days=60), today)))),
            ui.input_action_button("refresh", ui.span(ic("refresh", 16), " " + tr("Actualiser")), class_="btn-primary"),
            ui.download_button("export_xlsx", ui.span(ic("download", 16), " " + tr("Exporter en Excel")), class_="btn-warning"),
            ui.p(tr("Données et indicateurs de la période choisie."), class_="note"),
            ui.hr(),
            ui.output_ui("sidebar_info"),
            width=260, bg="#FFFFFF",
        ),
        ui.navset_underline(
            panel("home", tr("Vue générale"), "overview",
                ui.output_ui("kpis"),
                ui.layout_columns(
                    card("layers", tr("Temps quotidien par dimension"), output_widget("fig_daily_dims"), full_screen=True),
                    card("target", tr("Taux de réalisation (moyenne glissante 7 jours)"), output_widget("fig_completion"), full_screen=True),
                    col_widths=[7, 5],
                ),
                ui.layout_columns(
                    card("chart", tr("Activités principales"), output_widget("fig_top")),
                    card("bulb", tr("Ce que montrent tes données"), ui.output_ui("insights")),
                    card("star", tr("Événements marquants"), ui.output_ui("highlights")),
                    col_widths=[4, 5, 3],
                ),
            ),
            panel("calendar", tr("Saisie"), "entries",
                ui.output_ui("entry_kpis"),
                ui.layout_columns(
                    card("calendar", tr("Journées renseignées, rattrapées et oubliées, par semaine"), output_widget("fig_entry_weeks"), full_screen=True),
                    card("alert", tr("Jours de la semaine les plus souvent oubliés"), output_widget("fig_entry_weekday")),
                    col_widths=[7, 5],
                ),
                ui.layout_columns(
                    card("clock", tr("Délai des rattrapages"), output_widget("fig_entry_delay")),
                    card("grid", tr("Calendrier de saisie"), output_widget("fig_entry_calendar"), full_screen=True),
                    card("edit", tr("Journées encore rattrapables"), ui.output_ui("entry_pending")),
                    col_widths=[3, 6, 3],
                ),
            ),
            panel("trend_up", tr("Évolution"), "evolution",
                ui.layout_columns(
                    ui.input_selectize("evo_metrics", tr("Indicateurs"), metric_choices, multiple=True,
                                       selected=keep.get("evo_metrics", ["completion_rate", "mood", "energy"])),
                    ui.input_radio_buttons("evo_freq", tr("Échelle"), {"D": tr("Jour"), "W": tr("Semaine"), "M": tr("Mois")},
                                           selected=keep.get("evo_freq", "W"), inline=True),
                    col_widths=[8, 4],
                ),
                card("trend_up", tr("Évolution des indicateurs"), output_widget("fig_evolution"), full_screen=True),
                ui.layout_columns(
                    card("calendar", tr("Calendrier de régularité"), output_widget("fig_heat")),
                    card("route", tr("Comparer deux périodes"),
                         ui.layout_columns(
                             date_range("cmp_a", tr("Période A"),
                                        *keep.get("cmp_a", (today - timedelta(days=59), today - timedelta(days=30)))),
                             date_range("cmp_b", tr("Période B"), *keep.get("cmp_b", (today - timedelta(days=29), today))),
                         ),
                         ui.output_ui("compare")),
                    col_widths=[6, 6],
                ),
            ),
            panel("target", tr("Objectifs"), "goals",
                ui.layout_columns(
                    card("star", tr("Vision et objectifs"), ui.output_ui("goals_tree")),
                    card("chart", tr("Statut des intentions par semaine"), output_widget("fig_status")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    card("hourglass", tr("Temps prévu et temps réel"), output_widget("fig_calibration"), full_screen=True),
                    card("clock", tr("Calibration par type de tâche"), ui.output_ui("calibration_table")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    card("alert", tr("Objectifs souvent abandonnés"), output_widget("fig_abandons")),
                    card("message", tr("Raisons citées"), output_widget("fig_reasons")),
                    col_widths=[7, 5],
                ),
            ),
            panel("grid", tr("Dimensions"), "dimensions",
                ui.input_radio_buttons("dim", None, dim_choices, selected=keep.get("dim", "etudes"), inline=True),
                ui.output_ui("dim_kpis"),
                ui.layout_columns(
                    card("chart", tr("Temps hebdomadaire"), output_widget("fig_dim_week")),
                    card("layers", tr("Répartition des activités"), output_widget("fig_dim_cats")),
                    col_widths=[7, 5],
                ),
                card("message", tr("Réflexions de cette dimension"), ui.output_ui("dim_reflections")),
            ),
            panel("graduation", tr("Compétences"), "skills",
                ui.layout_columns(
                    card("graduation", tr("Auto évaluation dans le temps"), output_widget("fig_skill_rating"), full_screen=True),
                    card("clock", tr("Heures de pratique par mois"), output_widget("fig_skill_hours"), full_screen=True),
                    col_widths=[6, 6],
                ),
                card("check_circle", tr("Ressenti et preuves observables"), ui.output_ui("skills_table")),
            ),
            panel("flask", tr("Analyse"), "analysis",
                ui.div(ic("info", 16), ui.span(analytics.causality_note()), class_="note", style="margin:8px 0 12px"),
                ui.layout_columns(
                    card("link", tr("Corrélations (Spearman)"), output_widget("fig_corr"), full_screen=True),
                    card("link", tr("Associations les plus nettes"), ui.output_ui("corr_table")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    card("trend_up", tr("Tendances récentes"), ui.output_ui("trends")),
                    card("alert", tr("Jours atypiques"), ui.output_ui("anomalies")),
                    col_widths=[6, 6],
                ),
                ui.layout_columns(
                    card("calendar", tr("Profil de la semaine"), output_widget("fig_weekday")),
                    card("target", tr("Nombre d'intentions et réalisation"), output_widget("fig_load")),
                    col_widths=[6, 6],
                ),
                card("flask", tr("Expériences personnelles"), ui.output_ui("experiments")),
            ),
            panel("cpu", tr("Prédiction"), "prediction",
                ui.div(ic("info", 16), ui.span(tr("Les prédictions sont des estimations fondées sur ton historique, jamais des certitudes.")),
                       class_="note", style="margin:8px 0 12px"),
                ui.layout_columns(
                    card("route", tr("Simulation de scénario"),
                         ui.output_ui("sim_cat_ui"),
                         ui.layout_columns(ui.input_numeric("sim_min", tr("Minutes par jour"), keep.get("sim_min", 90), min=5, max=600),
                                           ui.input_numeric("sim_days", tr("Durée (jours)"), keep.get("sim_days", 90), min=7, max=3650)),
                         ui.input_slider("sim_week", tr("Jours par semaine"), 1, 7, keep.get("sim_week", 6)),
                         ui.input_action_button("sim_go", ui.span(ic("play", 16), " " + tr("Simuler")), class_="btn-warning"),
                         ui.output_ui("sim_text")),
                    card("chart", tr("Distribution simulée des heures totales"), output_widget("fig_sim"), full_screen=True),
                    col_widths=[4, 8],
                ),
                card("cpu", tr("Modèle de réalisation des intentions"), ui.output_ui("model_info")),
            ),
            panel("archive", tr("Mémoire"), "memory",
                ui.layout_columns(
                    ui.input_text("q", None, placeholder=tr("Qu'est ce qui m'a marqué le mois dernier ?"), width="100%"),
                    ui.input_action_button("q_go", ui.span(ic("search", 16), " " + tr("Interroger")), class_="btn-primary"),
                    col_widths=[10, 2],
                ),
                ui.output_ui("memory"),
            ),
            id="tabs", selected=keep.get("tabs"),
        ),
    )

app_ui = ui.page_fillable(
    ui.tags.style(CSS),
    ui.div(ui.div(class_="pei-band")),
    ui.div(
        ui.output_ui("head_photo", inline=True),
        ui.div(ui.h1("Personal Evolution Intelligence"), ui.output_ui("head_sub", inline=True)),
        ui.div(ui.output_ui("head_user", inline=True), ui.output_ui("lang_ui", inline=True), class_="head-right"),
        class_="pei-head",
    ),
    ui.output_ui("root", fill=True, fillable=True),
    title="PEI",
    padding=0,
    gap=0,
)


LOGIN_CSS = """
.pei-login { max-width: 380px; margin: 70px auto; background: #fff; border-radius: 20px; padding: 80px 26px 26px;
  box-shadow: 0 18px 44px rgba(16,35,28,.18); position: relative; text-align: center; }
.pei-login .ph { position: absolute; left: 50%; top: 0; transform: translate(-50%,-50%); width: 120px; height: 120px;
  border-radius: 50%; overflow: hidden; box-shadow: 0 0 0 5px #FFCE00, 0 0 0 9px #fff; }
.pei-login .ph img { width: 100%; height: 100%; object-fit: cover; }
.pei-login h2 { color: #006A4E; font-size: 20px; margin: 0 0 6px; }
.pei-login .form-group { text-align: left; }
.pei-login .err { color: #D21034; min-height: 22px; font-size: 14px; }
"""


def photo_data_uri() -> str:
    import base64

    data, mime = profile.photo_bytes()
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def server(input, output, session):
    # Authentification : session ouverte sur l'application (cookie partagé) ou connexion ici.
    try:
        cookies = session.http_conn.cookies
        accept = session.http_conn.headers.get("accept-language")
    except AttributeError:
        cookies, accept = {}, None

    def user_info(u):
        return {"id": u.id, "name": u.display_name or u.username, "language": u.language or "fr"} if u else None

    with session_scope() as s:
        first_user = user_info(auth.user_for_token(s, cookies.get(auth.COOKIE)))

    authed = reactive.value(first_user)
    login_error = reactive.value("")
    # Langue : choix du compte, sinon cookie partagé avec l'application, sinon navigateur.
    lang = reactive.value(i18n.normalize((first_user or {}).get("language") or cookies.get(i18n.COOKIE)
                                         or i18n.from_accept_language(accept)))

    def localized(fn):
        """Exécute un rendu dans la langue de la session."""
        @wraps(fn)
        def inner(*args, **kwargs):
            with i18n.use(lang()):
                return fn(*args, **kwargs)
        return inner

    @render.ui
    def lang_ui():
        current = lang()
        return ui.TagList(
            ui.input_radio_buttons("lang_sel", None, {"fr": "FR", "en": "EN"}, selected=current, inline=True),
            ui.tags.script(f"document.cookie='{i18n.COOKIE}={current}; path=/; max-age=31536000; samesite=lax';"
                           f"document.documentElement.lang='{current}';"),
        )

    @reactive.effect
    @reactive.event(input.lang_sel)
    def _switch_lang():
        new = i18n.normalize(input.lang_sel())
        if new == lang():
            return
        lang.set(new)
        user = authed()
        if user:
            with session_scope() as s:
                u = s.get(m.User, user["id"])
                if u is not None:
                    u.language = new

    @render.ui
    @localized
    def head_sub():
        return ui.tags.small(tr("Tableau de bord analytique, entièrement local"))

    @render.ui
    @localized
    def head_photo():
        authed()  # rafraîchie à la connexion (la photo a pu changer)
        return ui.img(src=photo_data_uri(), class_="head-photo", alt=tr("Photo de profil"))

    @render.ui
    @localized
    def head_user():
        user = authed()
        return ui.span(tr("Connecté : {name}", name=user["name"]), class_="head-user") if user else ui.span()

    def current_choices() -> dict:
        """Choix en cours, repris quand l'interface est reconstruite dans l'autre langue."""
        keep = {}
        for key in ("period", "custom_range", "evo_metrics", "evo_freq", "cmp_a", "cmp_b", "dim", "tabs",
                    "sim_min", "sim_days", "sim_week"):
            try:
                value = getattr(input, key)()
            except Exception:  # noqa: BLE001 (entrée pas encore créée)
                continue
            if value is not None:
                keep[key] = value
        return keep

    @render.ui
    @localized
    def root():
        if authed():
            with reactive.isolate():
                keep = current_choices()
            return build_main(keep)
        with session_scope() as s:
            configured = auth.is_configured(s)
        body = [ui.tags.style(LOGIN_CSS), ui.div(ui.img(src=photo_data_uri(), alt=tr("Photo")), class_="ph"),
                ui.h2(tr("Tableau de bord"))]
        if not configured:
            body.append(ui.p(tr("Crée d'abord ton compte depuis l'application (port 8000), puis reviens ici."), class_="note"))
        else:
            body += [ui.p(tr("Connecte toi avec ton compte PEI."), class_="note"),
                     ui.input_text("login_user", tr("Identifiant"), width="100%"),
                     ui.input_password("login_pass", tr("Mot de passe"), width="100%"),
                     ui.div(login_error(), class_="err"),
                     ui.input_action_button("login_go", ui.span(ic("arrow_right", 16), " " + tr("Se connecter")),
                                            class_="btn-primary", width="100%")]
        return ui.div(*body, class_="pei-login")

    @reactive.effect
    @reactive.event(input.login_go)
    def _login():
        try:
            with i18n.use(lang()), session_scope() as s:
                info = user_info(auth.check_credentials(s, input.login_user() or "", input.login_pass() or ""))
            login_error.set("")
            lang.set(i18n.normalize(info["language"]))
            authed.set(info)
        except auth.AuthError as exc:
            login_error.set(str(exc))

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
    @localized
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

    @render.download(filename=lambda: export_excel.filename(*period()))
    def export_xlsx():
        start, end = period()
        with i18n.use(lang()), session_scope() as s:
            content = export_excel.export_bytes(s, start, end)
        yield content

    @render.ui
    @localized
    def sidebar_info():
        input.refresh()
        with session_scope() as s:
            n_days = s.query(m.Day).count()
            first = s.query(m.Day.date).order_by(m.Day.date).first()
        return ui.div(
            ui.p(ic("archive", 16), " " + tr("{n} journées enregistrées", n=n_days), class_="note"),
            ui.p(ic("calendar", 16), " " + (tr("depuis le {date}", date=first[0].strftime('%d/%m/%Y')) if first else tr("aucune donnée")),
                 class_="note"),
            ui.p(ic("shield", 16), " " + tr("Données stockées sur ce PC uniquement"), class_="note"),
        )

    # Régularité de saisie

    @reactive.calc
    @localized
    def entry():
        start, end = period()
        with session_scope() as s:
            return analytics.entry_discipline(s, start, end)

    @render.ui
    @localized
    def entry_kpis():
        e = entry()
        if not e["n_closed"]:
            return ui.p(tr("Pas encore de journée terminée à analyser."), class_="note")

        nd = tr("n.d.")

        def pct(x):
            return nd if x is None else f"{round(x * 100)} %"
        boxes = [
            ("check_circle", tr("Le jour même"), pct(e["on_time_rate"]), tr("{n} journées", n=e["on_time"]), ""),
            ("clock", tr("Rattrapées"), pct(e["late_rate"]), tr("{n} journées", n=e["late"]), "vb-yellow"),
            ("x_circle", tr("Oubliées"), pct(e["missed_rate"]), tr("{n} journées verrouillées", n=e["missed"]), "vb-red"),
            ("hourglass", tr("Délai moyen"), tr("{n} j", n=i18n.num(e["mean_delay"], 1)) if e["mean_delay"] is not None else nd,
             tr("rattrapage autorisé : {n} jours", n=e["window_days"]), ""),
            ("moon", tr("Bilans du soir oubliés"), e["evening_missing"],
             tr("{pct} des journées avec intentions", pct=pct(e["evening_missing_rate"])), "vb-red"),
            ("flag", tr("Record à temps"), tr("{n} j", n=e["best_on_time_streak"]), tr("jours de suite renseignés le jour même"),
             "vb-yellow"),
        ]
        return ui.div(
            ui.layout_columns(*[ui.value_box(t, v, sub, showcase=ic(icn, 34), class_=cls)
                                for icn, t, v, sub, cls in boxes], col_widths=[2] * 6),
            ui.div(ic("info", 16), ui.span(e["message"]), class_="note", style="margin:4px 0 10px"),
        )

    @render_plotly
    @localized
    def fig_entry_weeks():
        e = entry()
        if not e["weekly"]:
            return empty_fig()
        w = pd.DataFrame(e["weekly"])
        fig = go.Figure()
        for key, label, color in [("a_temps", tr("Le jour même"), GREEN), ("rattrapee", tr("Rattrapée"), YELLOW),
                                  ("oubliee", tr("Oubliée"), RED), ("a_rattraper", tr("À rattraper"), "#F2A7B5")]:
            fig.add_bar(x=w["week"], y=w[key], name=label, marker_color=color)
        fig.update_layout(barmode="stack", yaxis_title=tr("journées"))
        return layout(fig)

    @render_plotly
    @localized
    def fig_entry_weekday():
        e = entry()
        if not e["by_weekday"]:
            return empty_fig()
        wd = e["by_weekday"]
        fig = go.Figure()
        fig.add_bar(x=[w["weekday"] for w in wd], y=[(w["forget_rate"] or 0) * 100 for w in wd],
                    name=tr("Non renseignée le jour même"), marker_color=YELLOW)
        fig.add_bar(x=[w["weekday"] for w in wd], y=[(w["missed_rate"] or 0) * 100 for w in wd],
                    name=tr("Oubliée définitivement"), marker_color=RED)
        fig.update_layout(barmode="group", yaxis=dict(title="%", range=[0, 100]))
        return layout(fig)

    @render_plotly
    @localized
    def fig_entry_delay():
        e = entry()
        dist = e["delay_distribution"]
        if not dist:
            return empty_fig(tr("Aucun rattrapage"))
        fig = go.Figure(go.Bar(x=[tr("{n} j", n=d['delay']) for d in dist], y=[d["count"] for d in dist], marker_color=YELLOW,
                               text=[d["count"] for d in dist], textposition="auto"))
        fig.update_layout(xaxis_title=tr("jours après"), yaxis_title=tr("journées"))
        return layout(fig, 300)

    @render_plotly
    @localized
    def fig_entry_calendar():
        e = entry()
        if not e["days"]:
            return empty_fig()
        code = {"a_temps": 3, "rattrapee": 2, "a_rattraper": 1, "oubliee": 0, "en_cours": None}
        df = pd.DataFrame(e["days"])
        df["date"] = pd.to_datetime(df["date"])
        df["z"] = df["status"].map(code)
        df["week"] = df["date"].dt.to_period("W").dt.start_time
        df["dow"] = df["date"].dt.dayofweek
        piv = df.pivot_table(index="dow", columns="week", values="z", aggfunc="first").reindex(range(7))
        lab = df.pivot_table(index="dow", columns="week", values="status_label", aggfunc="first").reindex(range(7))
        fig = go.Figure(go.Heatmap(
            z=nan_to_none(piv), x=list(piv.columns), y=[i18n.weekday(i, short=True) for i in range(7)], text=nan_to_none(lab),
            hovertemplate="%{x|%d/%m}<br>%{text}<extra></extra>", zmin=0, zmax=3, xgap=2, ygap=2, showscale=False,
            colorscale=[[0, RED], [0.33, RED], [0.34, "#F2A7B5"], [0.5, "#F2A7B5"], [0.51, YELLOW], [0.83, YELLOW],
                        [0.84, GREEN], [1, GREEN]]))
        fig.update_yaxes(autorange="reversed")
        return layout(fig, 300)

    @render.ui
    @localized
    def entry_pending():
        e = entry()
        if not e["pending"]:
            return ui.p(tr("Aucune journée à rattraper."), class_="note")
        rows = [{"d": pd.Timestamp(p["date"]).strftime("%d/%m/%Y"), "r": p["reason"],
                 "l": f'<span class="tag {"r" if p["days_left"] <= 1 else "y"}">'
                      f'{tr("dernier jour") if p["days_left"] <= 0 else tr("{n} j restants", n=p["days_left"])}</span>'}
                for p in e["pending"]]
        return table(rows, [("d", tr("Journée")), ("r", tr("Manque")), ("l", tr("Délai"))])

    # Vue générale

    @render.ui
    @localized
    def kpis():
        s = data()["summary"]
        if s.get("empty"):
            return ui.p(tr("Aucune donnée sur cette période. Commence par saisir tes intentions depuis le téléphone."), class_="note")

        nd = tr("n.d.")

        def pct(x):
            return nd if x is None else f"{round(x * 100)} %"
        boxes = [
            ("calendar", tr("Régularité"), pct(s["regularity"]),
             tr("{n} jours sur {total}", n=s["n_logged_days"], total=s["n_days"]), ""),
            ("target", tr("Réalisation"), pct(s["completion_rate"]),
             tr("{n} sur {total} intentions", n=s["n_done"], total=s["n_reviewed"]), "vb-yellow"),
            ("clock", tr("Temps suivi"), f"{i18n.num(s['total_hours'], 1)} h", tr("{n} intentions", n=s["n_intentions"]), ""),
            ("flag", tr("Série en cours"), tr("{n} j", n=s["current_streak"]), tr("record {n} j", n=s["longest_streak"]), "vb-red"),
            ("smile", tr("Humeur moyenne"), i18n.num(s["avg_mood"], 1) if s["avg_mood"] is not None else nd,
             tr("énergie {n}", n=i18n.num(s["avg_energy"], 1) if s["avg_energy"] is not None else nd), "vb-yellow"),
            ("bed", tr("Sommeil moyen"), f"{i18n.num(s['avg_sleep'], 1)} h" if s["avg_sleep"] else nd, tr("par nuit"), ""),
        ]
        return ui.layout_columns(*[ui.value_box(t, v, sub, showcase=ic(icn, 34), class_=cls)
                                   for icn, t, v, sub, cls in boxes], col_widths=[2] * 6)

    @render_plotly
    @localized
    def fig_daily_dims():
        d = data()["daily"]
        if d.empty:
            return empty_fig()
        fig = go.Figure()
        for dim in DIMENSIONS:
            col = f"min_{dim}"
            if d[col].sum() > 0:
                fig.add_bar(x=d.index, y=d[col] / 60, name=dimension_label(dim), marker_color=DIM_COLORS[dim])
        fig.update_layout(barmode="stack", yaxis_title=tr("heures"))
        return layout(fig)

    @render_plotly
    @localized
    def fig_completion():
        d = data()["daily"]
        if d.empty or d["completion_rate"].notna().sum() < 2:
            return empty_fig()
        roll = d["completion_rate"].rolling(7, min_periods=3).mean() * 100
        fig = go.Figure()
        fig.add_scatter(x=d.index, y=d["completion_rate"] * 100, mode="markers", name=tr("jour"), marker=dict(color=YELLOW, size=6))
        fig.add_scatter(x=d.index, y=roll, mode="lines", name=tr("moyenne 7 jours"), line=dict(color=GREEN, width=3))
        fig.update_layout(yaxis=dict(range=[0, 105], title="%"))
        return layout(fig)

    @render_plotly
    @localized
    def fig_top():
        top = data()["summary"].get("top_categories") or []
        if not top:
            return empty_fig()
        top = list(reversed(top[:8]))
        fig = go.Figure(go.Bar(x=[t["hours"] for t in top], y=[t["category"] for t in top], orientation="h",
                               marker_color=[DIM_COLORS.get(t["dimension"], GREEN) for t in top],
                               text=[f"{t['hours']} h" for t in top], textposition="auto"))
        fig.update_layout(xaxis_title=tr("heures"))
        return layout(fig, 330)

    @render.ui
    @localized
    def insights():
        ins = data()["insights"]
        if not ins:
            return ui.p(tr("Les recommandations apparaîtront avec quelques semaines de données."), class_="note")
        return ui.div(*[ui.div(ui.div(ic(i.get("icon", "bulb"), 20), class_="ib"),
                               ui.div(ui.tags.b(i["title"]), ui.span(i["message"]),
                                      ui.div(ic("info", 13), i.get("caveat", ""), class_="caveat")),
                               class_="insight") for i in ins[:6]],
                      style="max-height:340px;overflow:auto")

    @render.ui
    @localized
    def highlights():
        hl = data()["summary"].get("highlights") or []
        if not hl:
            return ui.p(tr("Aucun événement marquant."), class_="note")
        return ui.div(*[ui.div(ui.tags.span(pd.Timestamp(h["date"]).strftime("%d/%m"), class_="tag y"), h["content"],
                               style="padding:6px 0;border-bottom:1px solid #EEF2EF;font-size:14px") for h in hl],
                      style="max-height:340px;overflow:auto")

    # Évolution

    @render_plotly
    @localized
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
            fig.add_scatter(x=s.index, y=s.values, mode="lines+markers", name=analytics.metric_label(col),
                            line=dict(width=3, color=PALETTE[i % len(PALETTE)]), yaxis="y" if i == 0 else "y2")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False))
        return layout(fig, 420)

    @render_plotly
    @localized
    def fig_heat():
        d = data()["daily"]
        if d.empty:
            return empty_fig()
        z = d["completion_rate"].copy()
        z[~d["logged"]] = None
        frame = pd.DataFrame({"z": z * 100, "dow": d.index.dayofweek, "week": d.index.to_period("W").start_time})
        piv = frame.pivot_table(index="dow", columns="week", values="z", aggfunc="mean", dropna=False)
        piv = piv.reindex(range(7))
        fig = go.Figure(go.Heatmap(z=nan_to_none(piv), x=list(piv.columns), y=[i18n.weekday(i, short=True) for i in range(7)],
                                   colorscale=[[0, RED], [0.5, YELLOW], [1, GREEN]], zmin=0, zmax=100, xgap=2, ygap=2,
                                   colorbar=dict(title="%"), hoverongaps=False))
        fig.update_yaxes(autorange="reversed")
        return layout(fig, 300)

    @render.ui
    @localized
    def compare():
        a, b = input.cmp_a(), input.cmp_b()
        if not all(a) or not all(b):
            return ui.p(tr("Choisis deux périodes."), class_="note")
        input.refresh()
        with session_scope() as s:
            res = analytics.compare_periods(s, a, b)
        sa, sb, diff = res["a"], res["b"], res["difference"]
        if sa.get("empty") or sb.get("empty"):
            return ui.p(tr("Une des périodes ne contient pas de données."), class_="note")
        rows = []
        nd = tr("n.d.")
        for key, label, factor, unit in [("regularity", tr("Régularité"), 100, " %"), ("completion_rate", tr("Réalisation"), 100, " %"),
                                         ("total_hours", tr("Heures suivies"), 1, " h"), ("avg_mood", tr("Humeur"), 1, ""),
                                         ("avg_energy", tr("Énergie"), 1, ""), ("avg_sleep", tr("Sommeil"), 1, " h"),
                                         ("n_intentions", tr("Intentions"), 1, "")]:
            va, vb, dv = sa.get(key), sb.get(key), diff.get(key)
            fmt = lambda v: nd if v is None else f"{round(v * factor, 1):g}{unit}"  # noqa: E731
            sign = "" if dv is None else ("tag" if dv > 0 else "tag r" if dv < 0 else "tag y")
            rows.append({"k": label, "a": fmt(va), "b": fmt(vb),
                         "d": "" if dv is None else f'<span class="{sign}">{"+" if dv > 0 else ""}{round(dv * factor, 1):g}{unit}</span>'})
        return table(rows, [("k", tr("Indicateur")), ("a", tr("Période A")), ("b", tr("Période B")), ("d", tr("Écart"))])

    # Objectifs

    @render.ui
    @localized
    def goals_tree():
        goals = data()["goals"]
        if not goals:
            return ui.p(tr("Aucun objectif. Ajoute ta vision depuis le téléphone."), class_="note")
        children: dict = {}
        for g in goals:
            children.setdefault(g["parent_id"], []).append(g)
        order = list(HORIZONS)

        def node(g, depth=0):
            rate = g["completion_rate"]
            status_cls = {"atteint": "tag", "actif": "tag y", "abandonne": "tag r"}.get(g["status"], "tag")
            dim_icon = DIMENSIONS.get(g["dimension"] or "", {}).get("icon", "star")
            rate_txt = ", " + tr("{pct} % réalisé", pct=round(rate * 100)) if rate is not None else ""
            since = g["days_since_last_action"]
            since_txt = ", " + tr("dernière action il y a {n} j", n=since) if since is not None else ""
            horizon = label_of(HORIZONS, g["horizon"], g["horizon"])
            status = label_of(GOAL_STATUSES, g["status"], g["status"].replace("_", " "))
            html = (f'<div style="margin-left:{depth * 18}px;padding:7px 0;border-bottom:1px solid #EEF2EF">'
                    f'{icons.svg(dim_icon, 16, GREEN)} <b>{g["title"]}</b> <span class="tag y">{horizon}</span>'
                    f'<span class="{status_cls}">{status}</span>'
                    f'<div class="note">{tr("{n} actions", n=g["n_intentions"])}, {g["hours"]} h{rate_txt}{since_txt}</div></div>')
            for c in sorted(children.get(g["id"], []), key=lambda x: order.index(x["horizon"]) if x["horizon"] in order else 9):
                html += node(c, depth + 1)
            return html
        roots = sorted(children.get(None, []), key=lambda x: order.index(x["horizon"]) if x["horizon"] in order else 9)
        return ui.HTML('<div style="max-height:380px;overflow:auto">' + "".join(node(g) for g in roots) + "</div>")

    @render_plotly
    @localized
    def fig_status():
        it = data()["fr"].intentions
        if it.empty:
            return empty_fig()
        w = it.assign(week=it["date"].dt.to_period("W").dt.start_time).groupby(["week", "status"])["id"].count().unstack(fill_value=0)
        fig = go.Figure()
        for st in ["realise", "partiel", "reporte", "non_realise", "abandonne", "prevu"]:
            if st in w:
                fig.add_bar(x=w.index, y=w[st], name=label_of(INTENTION_STATUSES, st), marker_color=STATUS_COLORS[st])
        fig.update_layout(barmode="stack")
        return layout(fig)

    @render_plotly
    @localized
    def fig_calibration():
        cal = analytics.calibration(data()["fr"])
        pts = pd.DataFrame(cal.get("points") or [])
        if pts.empty:
            return empty_fig(tr("Indique durées prévues et réelles pour calibrer tes estimations"))
        mx = float(max(pts["estimated_minutes"].max(), pts["actual_minutes"].max())) * 1.05
        fig = go.Figure()
        fig.add_scatter(x=[0, mx], y=[0, mx], mode="lines", name=tr("estimation parfaite"), line=dict(color="#9AA8A1", dash="dot"))
        for i, (cat, g) in enumerate(pts.groupby("category")):
            fig.add_scatter(x=g["estimated_minutes"], y=g["actual_minutes"], mode="markers", name=cat,
                            marker=dict(size=8, opacity=.7, color=PALETTE[i % len(PALETTE)]), text=g["date"])
        fig.update_layout(xaxis_title=tr("minutes prévues"), yaxis_title=tr("minutes réelles"))
        return layout(fig, 400)

    @render.ui
    @localized
    def calibration_table():
        cal = analytics.calibration(data()["fr"])
        if not cal.get("categories"):
            return ui.p(tr("Pas encore de données de calibration."), class_="note")
        rows = [{**c, "bias_tag": f'<span class="tag {"r" if c["bias"] == "sous estimation" else "y" if c["bias"] == "surestimation" else ""}">{c.get("bias_label") or tr(c["bias"])}</span>',
                 "ratio": f"x {c['median_ratio']}"} for c in cal["categories"]]
        return ui.div(ui.p(ic("info", 14), " ", cal["overall"]["message"], class_="note"),
                      table(rows, [("category", tr("Type")), ("n", tr("Obs.")), ("mean_estimated", tr("Prévu (min)")),
                                   ("mean_actual", tr("Réel (min)")), ("ratio", tr("Ratio médian")), ("bias_tag", tr("Tendance"))]),
                      style="max-height:400px;overflow:auto")

    @render_plotly
    @localized
    def fig_abandons():
        ab = analytics.abandons(data()["fr"])["categories"][:10]
        if not ab:
            return empty_fig()
        ab = list(reversed(ab))
        fig = go.Figure(go.Bar(x=[a["abandon_rate"] * 100 for a in ab], y=[a["category"] for a in ab], orientation="h",
                               marker_color=RED, text=[f"{a['abandoned']}/{a['n']}" for a in ab], textposition="auto"))
        fig.update_layout(xaxis=dict(title=tr("% non réalisé"), range=[0, 100]))
        return layout(fig)

    @render_plotly
    @localized
    def fig_reasons():
        reasons = analytics.abandons(data()["fr"])["reasons"]
        if not reasons:
            return empty_fig(tr("Aucune raison renseignée"))
        fig = go.Figure(go.Pie(labels=[r["reason"] for r in reasons], values=[r["count"] for r in reasons], hole=.55,
                               marker=dict(colors=PALETTE)))
        return layout(fig)

    # Dimensions

    @render.ui
    @localized
    def dim_kpis():
        dim = input.dim()
        s = data()["summary"]
        if s.get("empty"):
            return ui.div()
        d = next((x for x in s["dimensions"] if x["dimension"] == dim), None)
        rate = tr("n.d.") if d["completion_rate"] is None else f"{round(d['completion_rate'] * 100)} %"
        return ui.layout_columns(
            ui.value_box(tr("Temps consacré"), f"{i18n.num(d['hours'], 1)} h", showcase=ic(d["icon"], 34)),
            ui.value_box(tr("Intentions"), d["n_intentions"], showcase=ic("target", 34), class_="vb-yellow"),
            ui.value_box(tr("Réalisation"), rate, showcase=ic("check_circle", 34)),
            ui.value_box(tr("Séances"), d["n_activities"], showcase=ic("layers", 34), class_="vb-red"),
            col_widths=[3, 3, 3, 3],
        )

    @render_plotly
    @localized
    def fig_dim_week():
        d = data()["daily"]
        col = f"min_{input.dim()}"
        if d.empty or d[col].sum() == 0:
            return empty_fig()
        w = d[col].resample("W-MON").sum() / 60
        fig = go.Figure(go.Bar(x=w.index, y=w.values, marker_color=DIM_COLORS[input.dim()]))
        trend = w.rolling(4, min_periods=2).mean()
        fig.add_scatter(x=trend.index, y=trend.values, mode="lines", name=tr("moyenne 4 semaines"), line=dict(color="#10231C", width=2))
        fig.update_layout(yaxis_title=tr("heures par semaine"), showlegend=False)
        return layout(fig)

    @render_plotly
    @localized
    def fig_dim_cats():
        ac = data()["fr"].activities
        ac = ac[ac["dimension"] == input.dim()] if not ac.empty else ac
        if ac.empty:
            return empty_fig()
        g = ac.groupby("category")["minutes"].sum().sort_values(ascending=False).head(8)
        fig = go.Figure(go.Pie(labels=g.index, values=g.values / 60, hole=.55, marker=dict(colors=PALETTE)))
        return layout(fig)

    @render.ui
    @localized
    def dim_reflections():
        rf = data()["fr"].reflections
        rf = rf[rf["dimension"] == input.dim()] if not rf.empty else rf
        if rf.empty:
            return ui.p(tr("Aucune réflexion pour cette dimension sur la période."), class_="note")
        rows = [{"date": r.date.strftime("%d/%m/%Y"), "kind": f'<span class="tag y">{label_of(REFLECTION_KINDS, r.kind, r.kind)}</span>', "content": r.content}
                for r in rf.sort_values("date", ascending=False).head(40).itertuples()]
        return ui.div(table(rows, [("date", tr("Date")), ("kind", tr("Type")), ("content", tr("Contenu"))]), style="max-height:320px;overflow:auto")

    # Compétences

    @reactive.calc
    @localized
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
    @localized
    def fig_skill_rating():
        sk = skills_data()
        if not sk:
            return empty_fig(tr("Aucune compétence suivie"))
        fig = go.Figure()
        for i, s in enumerate(sk):
            pts = [t for t in s["timeline"] if t["self_rating"] is not None]
            if pts:
                fig.add_scatter(x=[p["date"] for p in pts], y=[p["self_rating"] for p in pts], mode="lines+markers",
                                name=s["name"], line=dict(width=3, color=PALETTE[i % len(PALETTE)]))
        fig.update_layout(yaxis=dict(range=[0, 5.2], title=tr("niveau déclaré")))
        return layout(fig)

    @render_plotly
    @localized
    def fig_skill_hours():
        sk = skills_data()
        if not sk:
            return empty_fig(tr("Aucune compétence suivie"))
        fig = go.Figure()
        for i, s in enumerate(sk):
            if s["hours_by_month"]:
                fig.add_bar(x=[h["month"] for h in s["hours_by_month"]], y=[h["hours"] for h in s["hours_by_month"]],
                            name=s["name"], marker_color=PALETTE[i % len(PALETTE)])
        fig.update_layout(barmode="group", yaxis_title=tr("heures"))
        return layout(fig)

    @render.ui
    @localized
    def skills_table():
        sk = skills_data()
        rows = []
        for s in sk:
            proj = s["projection"]
            rows.append({
                "name": f"<b>{s['name']}</b>", "rating": tr("n.d.") if s["current_rating"] is None else f"{s['current_rating']}/5",
                "change": "" if s["rating_change"] is None else f"{'+' if s['rating_change'] > 0 else ''}{s['rating_change']:.1f}",
                "hours": f"{s['hours']} h", "sessions": s["n_activities"], "score": s["latest_objective_score"],
                "evidence": ", ".join(f"{v} {tr(k)}" for k, v in s["evidence"].items()),
                "proj": "" if not proj else f"{proj['projected']}/5 <span class='note'>[{proj['interval'][0]} ; {proj['interval'][1]}]</span>",
            })
        return table(rows, [("name", tr("Compétence")), ("rating", tr("Ressenti")), ("change", tr("Évolution")), ("hours", tr("Pratique")),
                            ("sessions", tr("Séances")), ("score", tr("Score objectif")), ("evidence", tr("Preuves")), ("proj", tr("Projection 3 mois"))])

    # Analyse

    @render_plotly
    @localized
    def fig_corr():
        c = analytics.correlations(data()["daily"])
        mat = c.get("matrix") or {}
        if not mat.get("values"):
            return empty_fig(tr("Au moins 14 jours renseignés sont nécessaires"))
        fig = go.Figure(go.Heatmap(z=mat["values"], x=mat["columns"], y=mat["columns"], zmin=-1, zmax=1,
                                   colorscale=[[0, RED], [0.5, "#FFFFFF"], [1, GREEN]], colorbar=dict(title=tr("rho"))))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(tickangle=-40)
        return layout(fig, 480)

    @render.ui
    @localized
    def corr_table():
        c = analytics.correlations(data()["daily"])
        pairs = c["pairs"][:14]
        rows = [{"pair": tr("{x} et {y}", x=p['x_label'], y=p['y_label']), "rho": p["rho"], "n": p["n"], "q": p["q_value"],
                 "sig": f'<span class="tag">{tr("nette")}</span>' if p["significant"] else f'<span class="tag y">{tr("incertaine")}</span>'}
                for p in pairs]
        return ui.div(table(rows, [("pair", tr("Variables")), ("rho", tr("rho")), ("n", tr("Jours")), ("q", tr("q (BH)")), ("sig", tr("Lecture"))]),
                      ui.p(ic("info", 14), " " + tr("q est la p valeur corrigée pour les tests multiples (Benjamini Hochberg)."), class_="note"),
                      style="max-height:480px;overflow:auto")

    @render.ui
    @localized
    def trends():
        t = analytics.trends(data()["daily"], fr=data()["fr"])
        if not t:
            return ui.p(tr("Aucune tendance nette sur les 3 dernières semaines."), class_="note")
        return ui.div(*[ui.div(ic("trend_up" if x["direction"] == "hausse" else "trend_down", 20,
                                  GREEN if x["direction"] == "hausse" else RED), " ", x["message"],
                               ui.span(f" p = {x['p_value']}", class_="note"),
                               style="padding:6px 0;border-bottom:1px solid #EEF2EF") for x in t])

    @render.ui
    @localized
    def anomalies():
        an = analytics.anomalies(data()["daily"])[:25]
        rows = [{**a, "dir": f'<span class="tag {"" if a["direction"] == "haut" else "r"}">{a.get("direction_label") or tr(a["direction"])}</span>'} for a in an]
        return ui.div(table(rows, [("date", tr("Date")), ("label", tr("Indicateur")), ("value", tr("Valeur")), ("expected", tr("Habituel")),
                                   ("dir", tr("Écart"))]), style="max-height:320px;overflow:auto")

    @render_plotly
    @localized
    def fig_weekday():
        wd = analytics.weekday_profile(data()["daily"])
        if not wd:
            return empty_fig()
        fig = go.Figure()
        fig.add_bar(x=[w["weekday"] for w in wd], y=[(w["completion_rate"] or 0) * 100 for w in wd], name=tr("réalisation (%)"),
                    marker_color=GREEN)
        fig.add_scatter(x=[w["weekday"] for w in wd], y=[w["actual_minutes"] for w in wd], name=tr("minutes suivies"),
                        yaxis="y2", mode="lines+markers", line=dict(color=YELLOW, width=3))
        fig.update_layout(yaxis=dict(title="%"), yaxis2=dict(overlaying="y", side="right", showgrid=False, title=tr("min")))
        return layout(fig)

    @render_plotly
    @localized
    def fig_load():
        d = data()["daily"]
        d = d[d["n_closed"] > 0]
        if d.empty:
            return empty_fig()
        g = d.groupby("n_intentions")["completion_rate"].agg(["mean", "count"]).reset_index()
        fig = go.Figure(go.Bar(x=g["n_intentions"], y=g["mean"] * 100, marker_color=[GREEN if v >= .6 else YELLOW if v >= .4 else RED for v in g["mean"]],
                               text=[f"{c} j" for c in g["count"]], textposition="auto"))
        fig.update_layout(xaxis_title=tr("intentions fixées le matin"), yaxis_title=tr("réalisation moyenne (%)"))
        return layout(fig)

    @render.ui
    @localized
    def experiments():
        input.refresh()
        with session_scope() as s:
            exps = [(e.title, e.hypothesis, analytics.experiment_analysis(s, e)) for e in s.query(m.Experiment).all()]
        if not exps:
            return ui.p(tr("Aucune expérience. Formule une hypothèse depuis le téléphone (Journal)."), class_="note")
        rows = [{"t": f"<b>{t}</b><div class='note'>{h}</div>", "m": a.get("label"),
                 "b": f"{a.get('baseline_mean')} ({tr('{n} j', n=a.get('n_baseline'))})",
                 "e": f"{a.get('experiment_mean')} ({tr('{n} j', n=a.get('n_experiment'))})",
                 "r": a.get("message")} for t, h, a in exps]
        return ui.div(table(rows, [("t", tr("Expérience")), ("m", tr("Indicateur")), ("b", tr("Avant")), ("e", tr("Pendant")), ("r", tr("Lecture"))]),
                      ui.p(ic("info", 14), " ", analytics.causality_note(), class_="note"))

    # Prédiction

    @render.ui
    @localized
    def sim_cat_ui():
        fr = full()
        cats = sorted(set(fr.activities["category"].dropna())) if not fr.activities.empty else []
        return ui.input_selectize("sim_cat", tr("Activité"), choices=cats, options={"create": True},
                                  selected="Python" if "Python" in cats else (cats[0] if cats else None))

    @reactive.calc
    @reactive.event(input.sim_go, ignore_none=False)
    @localized
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
    @localized
    def sim_text():
        r = sim()
        return ui.div(ui.hr(), ui.p(r["message"]), ui.p(ic("info", 14), " ", r["disclaimer"], class_="note"))

    @render_plotly
    @localized
    def fig_sim():
        r = sim()
        edges = r["histogram_edges"]
        mids = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
        fig = go.Figure(go.Bar(x=mids, y=r["histogram"], marker_color=GREEN, name=tr("simulations")))
        for v, name, col in [(r["hours_p10"], tr("prudent"), RED), (r["hours_median"], tr("médian"), "#10231C"),
                             (r["hours_p90"], tr("favorable"), YELLOW), (r["ideal_hours"], tr("si tout est réalisé"), "#9AA8A1")]:
            fig.add_vline(x=v, line=dict(color=col, width=2, dash="dash"), annotation_text=f"{name} {v:g} h",
                          annotation_position="top")
        fig.update_layout(xaxis_title=tr("heures totales"), yaxis_title=tr("nombre de simulations"), showlegend=False)
        return layout(fig, 420)

    @render.ui
    @localized
    def model_info():
        fr = full()
        mdl = predict.fit_completion(fr.intentions, fr.days)
        if mdl.kind == "aucune_donnee":
            return ui.p(tr("Aucune intention évaluée pour le moment."), class_="note")
        parts = [ui.p(ui.tags.b(tr("Modèle : ")), {"taux_de_base": tr("taux de base lissés (historique encore court)"),
                                                     "regression_logistique": tr("régression logistique")}[mdl.kind],
                      tr(", entraîné sur {n} intentions évaluées.", n=mdl.n))]
        if mdl.auc:
            parts.append(ui.p(ui.tags.b(tr("Qualité en validation temporelle (AUC) : ")), i18n.num(mdl.auc, 2),
                              ui.span(tr(" (0,5 = hasard, 1 = parfait)"), class_="note")))
        rows = sorted([{"k": k[1], "rate": f"{round(v['rate'] * 100)} %",
                        "n": v["n"]} for k, v in mdl.base_rates.items() if k[0] == "category"], key=lambda r: -r["n"])[:15]
        parts.append(table(rows, [("k", tr("Type d'activité")), ("rate", tr("Probabilité estimée de réalisation")), ("n", tr("Observations"))]))
        return ui.div(*parts)

    # Mémoire

    @render.ui
    @reactive.event(input.q_go)
    @localized
    def memory():
        q = input.q().strip()
        if not q:
            return ui.p(tr("Pose une question ou cherche un mot."), class_="note")
        with session_scope() as s:
            r = ask.ask(s, q)
        rows = [{"date": it.get("date") or "", "kind": f'<span class="tag">{it["kind_label"]}</span>',
                 "text": str(it["text"]).replace("[", "<mark>").replace("]", "</mark>")} for it in r["items"]]
        return ui.card(ui.card_header(ic("bulb", 18), r["answer"]),
                       ui.p(tr("Période : {period}", period=r['period']), class_="note"),
                       table(rows, [("date", tr("Date")), ("kind", tr("Source")), ("text", tr("Contenu"))]))


app = App(app_ui, server)
