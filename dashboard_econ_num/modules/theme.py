# -*- coding: utf-8 -*-
"""
Theme, palette (couleurs du drapeau togolais) et helpers Highcharts.
Toutes les visualisations utilisent Highcharts / Highmaps (graphiques
interactifs) charges via CDN.
"""
import json
import uuid

from faicons import icon_svg
from htmltools import HTML, Tag
from shiny import ui


def ic(name, cls=""):
    """Icone Font Awesome (SVG integre) — aucune emoji dans l'application."""
    return f'<span class="ic {cls}">{icon_svg(name)}</span>'

# --------------------------------------------------------------------------
# Palette — drapeau togolais
# --------------------------------------------------------------------------
GREEN_DARK = "#0B6E4F"   # vert du bandeau / barre de navigation
GREEN = "#008751"        # vert drapeau
YELLOW = "#FFCE00"       # jaune/or drapeau
RED = "#D21034"          # rouge drapeau
WHITE = "#FFFFFF"
INK = "#1c2b27"          # texte
GREY = "#6b7b76"

# Sequence de couleurs pour les series Highcharts
SERIES_COLORS = [GREEN, YELLOW, RED, "#5aa17f", "#e0a800", "#8c1c2b", GREEN_DARK]

# Echelle sequentielle pour choroplethes (clair -> vert fonce)
GREEN_SCALE = [
    [0.0, "#eef7f2"], [0.25, "#a9d7c1"], [0.5, "#5aa17f"],
    [0.75, "#1f8a5f"], [1.0, GREEN_DARK],
]
# Echelle de priorite (faible=vert -> eleve=rouge, drapeau togolais)
PRIORITY_SCALE = [
    [0.0, GREEN], [0.5, YELLOW], [1.0, RED],
]

# Highcharts / Highmaps sont embarques localement (www/js) : application
# autonome, chargement rapide, aucune dependance CDN a l'execution.
CDN = [
    "js/highcharts.js",
    "js/highcharts-more.js",
    "js/modules/map.js",
    "js/modules/exporting.js",
    "js/modules/accessibility.js",
]


def head_deps() -> Tag:
    """Dependances <head> : Highcharts + police + CSS + JS utilitaires."""
    scripts = "\n".join(f'<script src="{u}"></script>' for u in CDN)
    js = """
    <script>
    // Theme Highcharts global (couleurs drapeau togolais)
    function applyHCTheme(){
      if(typeof Highcharts==='undefined'){ setTimeout(applyHCTheme,60); return; }
      Highcharts.setOptions({
        colors: %COLORS%,
        chart: { style:{fontFamily:'Segoe UI, Roboto, Helvetica, Arial, sans-serif'},
                 backgroundColor:'transparent' },
        title: { style:{color:'%INK%', fontWeight:'700', fontSize:'15px'} },
        subtitle:{ style:{color:'%GREY%'} },
        xAxis:{ labels:{style:{color:'%INK%'}}, lineColor:'#dfe6e3',
                tickColor:'#dfe6e3', title:{style:{color:'%GREY%'}} },
        yAxis:{ labels:{style:{color:'%INK%'}}, gridLineColor:'#eef2f0',
                title:{style:{color:'%GREY%'}} },
        legend:{ itemStyle:{color:'%INK%'} },
        credits:{ enabled:false },
        lang:{ decimalPoint:',', thousandsSep:'\\u00a0',
               noData:'Aucune donnee a afficher' }
      });
    }
    applyHCTheme();
    // Reflow de tous les graphiques (utile quand on change d'onglet)
    function reflowAllCharts(){
      if(typeof Highcharts==='undefined') return;
      Highcharts.charts.forEach(function(c){ if(c){ try{c.reflow();}catch(e){} } });
    }
    document.addEventListener('shiny:connected', function(){
      Shiny.addCustomMessageHandler('reflow', function(m){
        setTimeout(reflowAllCharts, 120);
      });
    });
    window.addEventListener('resize', function(){ setTimeout(reflowAllCharts,150); });
    </script>
    """
    js = (js.replace("%COLORS%", json.dumps(SERIES_COLORS))
            .replace("%INK%", INK).replace("%GREY%", GREY))
    return ui.head_content(HTML(scripts + js), ui.tags.style(CSS))


# --------------------------------------------------------------------------
# Rendu d'un graphique Highcharts a partir d'une config Python (dict)
# --------------------------------------------------------------------------
def highchart(config: dict, height: int = 320) -> HTML:
    cid = "hc_" + uuid.uuid4().hex[:10]
    cfg = json.dumps(config, ensure_ascii=False)
    html = f"""
    <div id="{cid}" class="hc-chart" style="height:{height}px;width:100%;"></div>
    <script>(function(){{
      function draw(){{
        if(typeof Highcharts==='undefined'||!Highcharts.charts){{setTimeout(draw,60);return;}}
        var el=document.getElementById("{cid}"); if(!el){{return;}}
        Highcharts.chart("{cid}", {cfg});
      }}
      draw();
    }})();</script>"""
    return HTML(html)


def highmap(values: list, title: str = "", subtitle: str = "",
            scale=None, points: list = None, point_series: list = None,
            value_suffix: str = "", show_labels: bool = False,
            fond_name: str = "", geo_url: str = "geo/geo_prefectures.json",
            height: int = 520) -> HTML:
    """Choroplethe Highmaps (prefectures) + couches de points nommees.

    point_series : liste de {"name","color","data":[{"name","lon","lat"}]}.
    Chaque couche apparait dans la LEGENDE (clic pour afficher/masquer) : la
    carte indique donc explicitement ou se trouve chaque type d'infrastructure.
    show_labels : affiche le nom de chaque point directement sur la carte.
    """
    cid = "hm_" + uuid.uuid4().hex[:10]
    scale = scale or GREEN_SCALE
    if point_series is None:
        point_series = ([{"name": "Sites", "color": RED, "data": points}]
                        if points else [])
    payload = json.dumps({
        "values": values, "title": title, "subtitle": subtitle, "scale": scale,
        "series": point_series, "suffix": value_suffix, "labels": bool(show_labels),
        "fond": fond_name or title, "geo": geo_url,
    }, ensure_ascii=False)
    html = f"""
    <div id="{cid}" class="hc-chart" style="height:{height}px;width:100%;"></div>
    <script>(function(){{
      var P={payload};
      function draw(){{
        if(typeof Highcharts==='undefined'||!Highcharts.mapChart){{setTimeout(draw,80);return;}}
        function build(geo){{
          var series=[{{
            mapData:geo, joinBy:['_key','key'], data:P.values, name:P.fond,
            showInLegend:false, states:{{hover:{{color:'{YELLOW}'}}}},
            enableMouseTracking:true, borderColor:'#ffffff', borderWidth:0.5,
            tooltip:{{pointFormat:'<b>{{point.name}}</b><br/>{{point.value:,.2f}}'+P.suffix}}
          }}];
          P.series.forEach(function(s){{
            series.push({{type:'mappoint', name:s.name, color:s.color, data:s.data,
              showInLegend:false,
              marker:{{radius:5,symbol:'circle',lineColor:'#ffffff',lineWidth:1}},
              dataLabels:{{enabled:P.labels, format:'{{point.name}}', style:{{
                fontSize:'10px', fontWeight:'600', textOutline:'2px #ffffff'}}}},
              tooltip:{{headerFormat:'', pointFormat:'<b>{{point.name}}</b><br/>'+s.name}} }});
          }});
          Highcharts.mapChart("{cid}",{{
            chart:{{backgroundColor:'transparent'}},
            title:{{text:P.title}}, subtitle:{{text:P.subtitle}},
            mapNavigation:{{enabled:true,buttonOptions:{{verticalAlign:'bottom'}}}},
            colorAxis:{{stops:P.scale,minColor:'#eef7f2'}},
            legend:{{enabled:P.series.length>0, align:'left', verticalAlign:'top',
                     floating:true, backgroundColor:'rgba(255,255,255,.85)',
                     borderColor:'#dfe6e3', borderWidth:1, borderRadius:6,
                     itemStyle:{{fontSize:'11px'}}, title:{{text:''}}}},
            series:series
          }});
        }}
        if(window.__geo&&window.__geo[P.geo]){{build(window.__geo[P.geo]);}}
        else{{fetch(P.geo).then(function(r){{return r.json();}}).then(function(g){{
          window.__geo=window.__geo||{{}}; window.__geo[P.geo]=g; build(g);
        }});}}
      }}
      draw();
    }})();</script>"""
    return HTML(html)


# --------------------------------------------------------------------------
# CSS — reproduit la mise en forme du tableau de bord (bandeau fixe, etc.)
# --------------------------------------------------------------------------
CSS = f"""
:root{{ --green:{GREEN}; --green-dark:{GREEN_DARK}; --yellow:{YELLOW};
        --red:{RED}; --ink:{INK}; --grey:{GREY}; }}
*{{box-sizing:border-box;}}
body{{ background:#f4f6f5; color:var(--ink); margin:0;
       font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif; }}
.ic{{ display:inline-flex; align-items:center; }}
.ic svg{{ height:1em; width:1em; vertical-align:-0.125em; fill:currentColor; }}
.kpi .ic svg{{ height:1.5em; width:1.5em; }}
.kpi-ic{{ float:right; opacity:.55; }}

/* Bascule de langue (fixe, coin superieur droit) */
.lang-switch{{ position:fixed; top:8px; right:14px; z-index:1100; }}
.lang-switch .shiny-input-radiogroup{{ display:flex; gap:0; background:#ffffff;
   border:1px solid var(--green); border-radius:8px; overflow:hidden;
   box-shadow:0 1px 3px rgba(0,0,0,.15); }}
.lang-switch .radio, .lang-switch .form-check{{ margin:0; }}
.lang-switch label{{ padding:4px 12px; font-weight:800; font-size:12px; cursor:pointer;
   color:var(--green-dark); margin:0; display:flex; align-items:center; }}
.lang-switch input{{ display:none; }}
.lang-switch input:checked + span{{ }}
.lang-switch .form-check:has(input:checked) label,
.lang-switch label:has(input:checked){{ background:var(--green); color:#fff; }}

/* ---------- Bandeau + navigation FIXES en haut ---------- */
.topbar{{ position:fixed; top:0; left:0; right:0; z-index:1000; }}
.gov-banner{{ background:#fff; border-bottom:3px solid var(--yellow);
   display:flex; align-items:center; gap:14px; padding:6px 16px; }}
.gov-banner .flag-strip{{ height:6px; background:linear-gradient(90deg,
   var(--green) 0 33%, var(--yellow) 33% 66%, var(--red) 66% 100%); }}
.gov-banner .ph{{ display:flex; align-items:center; justify-content:center;
   border:1px dashed #c7d2cd; border-radius:6px; color:#9aa8a3;
   font-size:11px; text-align:center; background:#fbfdfc; }}
.logo-ph{{ width:120px; height:52px; }}
.crest-ph{{ width:60px; height:56px; }}
.gov-titles{{ flex:1; text-align:center; line-height:1.25; }}
.gov-titles .t1{{ color:var(--green-dark); font-weight:800; font-size:16px; }}
.gov-titles .t2{{ color:var(--red); font-weight:700; font-size:12px;
   letter-spacing:2px; }}
.gov-titles .t3{{ color:var(--green-dark); font-weight:700; font-size:13px; }}
.gov-titles .t4{{ color:var(--grey); font-style:italic; font-size:12px; }}
.flag-band{{ height:7px; background:linear-gradient(90deg,
   var(--green) 0 40%, var(--yellow) 40% 62%, var(--red) 62% 100%); }}

.appbar{{ background:var(--green-dark); color:#fff; padding:0 16px;
   display:flex; align-items:center; gap:6px; flex-wrap:wrap;
   box-shadow:0 2px 6px rgba(0,0,0,.15); }}
.appbar .brand{{ font-weight:800; font-size:16px; padding:10px 14px 10px 0;
   display:flex; align-items:center; gap:8px; white-space:nowrap; }}
.appbar .navlink{{ color:#dbe9e3; text-decoration:none; padding:12px 12px;
   font-size:13.5px; font-weight:600; border:none; background:none;
   cursor:pointer; border-bottom:3px solid transparent; }}
.appbar .navlink:hover{{ color:#fff; }}
.appbar .navlink.active{{ color:var(--ink); background:var(--yellow);
   border-radius:6px 6px 0 0; }}

/* ---------- Corps : compense la hauteur de la barre fixe ---------- */
.app-body{{ padding-top:150px; display:flex; gap:14px; padding-left:14px;
   padding-right:14px; padding-bottom:30px; }}
.sidebar{{ width:250px; flex:0 0 250px; background:#fff; border-radius:10px;
   padding:16px; box-shadow:0 1px 4px rgba(0,0,0,.08); align-self:flex-start;
   position:sticky; top:158px; }}
.sidebar h4{{ color:var(--green-dark); font-size:14px; font-weight:800;
   margin:0 0 14px; display:flex; align-items:center; gap:6px; }}
.content{{ flex:1; min-width:0; }}

/* ---------- Cartes KPI ---------- */
.kpi-row{{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
   gap:12px; margin-bottom:16px; }}
.kpi{{ border-radius:10px; padding:14px 16px; color:#fff;
   box-shadow:0 2px 6px rgba(0,0,0,.12); min-height:92px; }}
.kpi .v{{ font-size:26px; font-weight:800; line-height:1.1; }}
.kpi .l{{ font-size:12.5px; font-weight:700; margin-top:4px; }}
.kpi .s{{ font-size:11px; opacity:.85; }}
.kpi.green{{ background:var(--green-dark); }}
.kpi.green2{{ background:var(--green); }}
.kpi.yellow{{ background:var(--yellow); color:var(--ink); }}
.kpi.yellow .s{{ opacity:.7; }}
.kpi.grey{{ background:#4c5a55; }}
.kpi.red{{ background:var(--red); }}

/* ---------- Panneaux graphiques ---------- */
.panel{{ background:#fff; border-radius:10px; padding:12px 14px 6px;
   box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:16px; }}
.panel .ph-head{{ border-top:3px solid var(--yellow); padding-top:8px;
   font-weight:800; color:var(--green-dark); font-size:14px;
   display:flex; align-items:center; gap:8px; margin-bottom:4px; }}
.grid-2{{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
@media(max-width:1100px){{ .grid-2{{grid-template-columns:1fr;}} }}

/* ---------- Placeholders photos utilisateur ---------- */
.photo-ph{{ border:2px dashed #c7d2cd; border-radius:10px; background:#fbfdfc;
   color:#9aa8a3; display:flex; flex-direction:column; align-items:center;
   justify-content:center; text-align:center; padding:20px; font-size:13px; }}

/* ---------- Recommandations ---------- */
.reco-card{{ background:linear-gradient(135deg,#fff, #f3f9f6);
   border-left:5px solid var(--green); border-radius:10px; padding:16px 18px;
   box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:12px; }}
.reco-num{{ font-size:24px; font-weight:800; color:var(--green-dark); }}
.invest-box{{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.invest-box .b{{ border-radius:10px; padding:14px; color:#fff; text-align:center; }}
.invest-box .fcfa{{ background:var(--green-dark); }}
.invest-box .eur{{ background:var(--red); }}
.invest-box .amt{{ font-size:22px; font-weight:800; }}

.dataframe, table.reco{{ width:100%; border-collapse:collapse; font-size:13px; }}
table.reco th{{ background:var(--green-dark); color:#fff; padding:7px 9px;
   text-align:left; }}
table.reco td{{ padding:6px 9px; border-bottom:1px solid #eef2f0; }}
table.reco tr:nth-child(even){{ background:#f7faf9; }}
.badge{{ display:inline-block; padding:2px 8px; border-radius:12px;
   font-size:11px; font-weight:700; color:#fff; }}
.form-label{{ font-weight:700; font-size:13px; color:var(--green-dark); }}
.selectize-input, .form-select, .form-control{{ font-size:13px; }}
.author-wrap{{ display:grid; grid-template-columns:280px 1fr; gap:18px; }}
@media(max-width:900px){{ .author-wrap{{grid-template-columns:1fr;}}
   .app-body{{flex-direction:column;}} .sidebar{{width:100%;position:relative;top:0;}} }}
"""
