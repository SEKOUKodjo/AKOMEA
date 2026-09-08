# -*- coding: utf-8 -*-
"""Internationalisation FR / EN du tableau de bord."""

TR = {
    # ------- navigation / bandeau -------
    "nav_accueil": ("Accueil", "Home"),
    "nav_infra": ("Infrastructures", "Infrastructure"),
    "nav_services": ("Services numeriques", "Digital services"),
    "nav_couverture": ("Zones blanches", "White zones"),
    "nav_priorites": ("Priorites", "Priorities"),
    "nav_reco": ("Recommandations", "Recommendations"),
    "nav_carte": ("Carte", "Map"),
    "nav_auteur": ("Auteur", "Author"),
    "brand": ("SAD Economie Numerique", "Digital Economy DSS"),
    "republic": ("REPUBLIQUE TOGOLAISE", "TOGOLESE REPUBLIC"),
    "motto": ("TRAVAIL - LIBERTE - PATRIE", "WORK - LIBERTY - HOMELAND"),
    "ministry": ("MINISTERE DE L'ECONOMIE NUMERIQUE ET DE LA TRANSFORMATION DIGITALE",
                 "MINISTRY OF THE DIGITAL ECONOMY AND DIGITAL TRANSFORMATION"),
    "banner_sub": ("Tableau de bord d'aide a la decision — Acces aux telecommunications & services numeriques",
                   "Decision-support dashboard — Access to telecommunications & digital services"),
    "logo_ph": ("Logo Togo AI Lab", "Togo AI Lab logo"),
    "crest_ph": ("Armoiries", "Coat of arms"),

    # ------- sidebar -------
    "side_title": ("NIVEAU D'ANALYSE", "ANALYSIS LEVEL"),
    "region": ("Region", "Region"),
    "prefecture": ("Prefecture", "Prefecture"),
    "commune": ("Commune", "Commune"),
    "canton": ("Canton / localite", "Canton / locality"),
    "all": ("Toutes", "All"),
    "reset": ("Tout le Togo", "All Togo"),
    "sources": ("Sources", "Sources"),
    "sources_list": ("geodata.gouv.tg · RGPH-5 (2022) · geoBoundaries",
                     "geodata.gouv.tg · RGPH-5 (2022) · geoBoundaries"),
    "pop_note": ("Population projetee {y} (taux {r} %/an)",
                 "Population projected to {y} ({r} %/yr)"),

    # ------- KPI -------
    "kpi_mm": ("Agents mobile money", "Mobile money agents"),
    "kpi_mm_s": ("Points de service", "Service points"),
    "kpi_ag": ("Agences telecoms", "Telecom agencies"),
    "kpi_ag_s": ("Togocom + Moov", "Togocom + Moov"),
    "kpi_ratio": ("Agents / 1 000 hab.", "Agents / 1,000 pop."),
    "kpi_ratio_s": ("Inclusion financiere", "Financial inclusion"),
    "kpi_dc": ("Datacenters", "Data centers"),
    "kpi_dc_s": ("Centres de donnees", "Data centers"),
    "kpi_pop": ("Population {y}", "Population {y}"),
    "kpi_pop_s": ("Estimation", "Estimate"),
    "kpi_zb": ("Zones blanches", "White zones"),
    "kpi_zb_s": ("Cantons sans agent", "Cantons with no agent"),

    # ------- scope label -------
    "scope_all": ("Tout le Togo", "All Togo"),
    "scope_region": ("Region : {v}", "Region: {v}"),
    "scope_prefecture": ("Prefecture : {v}", "Prefecture: {v}"),
    "scope_commune": ("Commune : {v}", "Commune: {v}"),
    "scope_canton": ("Canton : {v}", "Canton: {v}"),

    # ------- accueil panels -------
    "p_mm_region": ("Agents mobile money par region", "Mobile money agents by region"),
    "p_ag_op": ("Agences telecoms par operateur", "Telecom agencies by operator"),
    "p_adequation": ("Adequation offre / population (agents pour 1 000 hab.)",
                     "Supply vs population (agents per 1,000 pop.)"),
    "p_densite_pref": ("Densite mobile money par prefecture",
                       "Mobile money density by prefecture"),

    # ------- infra -------
    "infra_badge": ("Repartition spatiale des infrastructures — {s}",
                    "Spatial distribution of infrastructure — {s}"),
    "p_infra_map": ("Localisation des agences telecoms & datacenters",
                    "Location of telecom agencies & data centers"),
    "p_infra_bar": ("Agences par prefecture (Top 15)", "Agencies by prefecture (Top 15)"),
    "p_infra_time": ("Anciennete des agences (annee de creation)",
                     "Agency age (year created)"),
    "p_infra_dc": ("Concentration des centres de donnees", "Data center concentration"),
    "infra_dc_note": (
        "Les {n} datacenters recenses sont tous situes dans le Grand Lome "
        "(prefecture du Golfe) — une concentration extreme qui constitue un risque "
        "de resilience et un frein a la deconcentration numerique du territoire.",
        "All {n} recorded data centers are located in Greater Lome (Golfe prefecture) "
        "— an extreme concentration that is a resilience risk and a barrier to the "
        "territorial deconcentration of digital services."),
    "th_etab": ("Etablissement", "Facility"),
    "th_commune": ("Commune", "Commune"),
    "th_annee": ("Annee", "Year"),

    # ------- services -------
    "srv_badge": ("Couverture des services numeriques — {s}",
                  "Digital service coverage — {s}"),
    "p_srv_map": ("Densite d'agents mobile money (pour 1 000 hab.)",
                  "Mobile money agent density (per 1,000 pop.)"),
    "p_srv_op": ("Repartition des agents par operateur", "Agents by operator"),
    "p_srv_top": ("Prefectures les mieux servies", "Best-served prefectures"),
    "p_srv_bottom": ("Prefectures les moins servies", "Least-served prefectures"),
    "p_srv_hab": ("Habitants par agent (accessibilite) — plus la barre est haute, "
                  "moins le service est accessible",
                  "Inhabitants per agent (accessibility) — the taller the bar, the "
                  "less accessible the service"),

    # ------- couverture -------
    "cov_couverts": ("Cantons couverts", "Covered cantons"),
    "cov_couverts_s": ("au moins 1 agent", "at least 1 agent"),
    "cov_blancs_s": ("aucun agent mobile money", "no mobile money agent"),
    "cov_taux": ("Taux de couverture", "Coverage rate"),
    "cov_taux_s": ("cantons desservis", "served cantons"),
    "cov_total": ("Cantons (total)", "Cantons (total)"),
    "cov_total_s": ("decoupage adm3", "adm3 breakdown"),
    "p_cov_bar": ("Zones blanches par region", "White zones by region"),
    "p_cov_map": ("Cartographie des zones blanches", "Mapping of white zones"),
    "p_cov_table": ("Liste des cantons non desservis (zones blanches)",
                    "List of unserved cantons (white zones)"),
    "cov_map_sub": ("Points rouges = cantons sans agent", "Red points = cantons with no agent"),
    "th_canton": ("Canton", "Canton"),
    "th_region": ("Region", "Region"),
    "th_prefecture": ("Prefecture", "Prefecture"),
    "covered": ("Couverts", "Covered"),

    # ------- priorites -------
    "prio_badge": ("Score de priorite = deficit d'offre pondere par la population (0 a 100)",
                   "Priority score = supply deficit weighted by population (0 to 100)"),
    "p_prio_bar": ("Classement des prefectures prioritaires",
                   "Ranking of priority prefectures"),
    "p_prio_map": ("Carte des priorites", "Priority map"),
    "p_prio_table": ("Tableau de priorisation", "Prioritization table"),
    "th_rank": ("Rang", "Rank"),
    "th_pop": ("Population", "Population"),
    "th_mm": ("Agents MM", "MM agents"),
    "th_score": ("Score", "Score"),
    "th_agences": ("Agences", "Agencies"),

    # ------- carte -------
    "p_carte": ("Carte nationale interactive", "Interactive national map"),
    "c_indic": ("Indicateur", "Indicator"),
    "c_points": ("Afficher les infrastructures (points)", "Show infrastructure (points)"),
    "ind_mm1000": ("Agents mobile money / 1 000 hab.", "Mobile money agents / 1,000 pop."),
    "ind_ag100k": ("Agences telecoms / 100 000 hab.", "Telecom agencies / 100,000 pop."),
    "ind_score": ("Score de priorite", "Priority score"),
    "ind_pop": ("Population 2026", "Population 2026"),
    "ind_nmm": ("Nombre d'agents mobile money", "Number of mobile money agents"),

    # ------- recommandations -------
    "reco_badge": ("Simulateur d'investissement — choisissez un territoire et un objectif",
                   "Investment simulator — choose a territory and a target"),
    "p_reco_geo": ("Territoire cible (region -> prefecture -> commune -> canton)",
                   "Target territory (region -> prefecture -> commune -> canton)"),
    "p_reco_obj": ("Objectifs & couts unitaires", "Targets & unit costs"),
    "obj_mm": ("Objectif : agents mobile money / 1 000 hab.",
               "Target: mobile money agents / 1,000 pop."),
    "obj_ag": ("Objectif : agences telecoms / 100 000 hab.",
               "Target: telecom agencies / 100,000 pop."),
    "cost_mm": ("Cout unitaire agent MM (FCFA)", "Unit cost per MM agent (FCFA)"),
    "cost_ag": ("Cout unitaire agence (FCFA)", "Unit cost per agency (FCFA)"),
    "reco_offer": ("Population {y} : <b>{pop}</b> hab. — offre actuelle : <b>{mm}</b> "
                   "agents MM ({d1} /1000), <b>{ag}</b> agences ({d2} /100k).",
                   "Population {y}: <b>{pop}</b> — current supply: <b>{mm}</b> MM agents "
                   "({d1} /1000), <b>{ag}</b> agencies ({d2} /100k)."),
    "reco_need_mm": ("agents mobile money a creer", "mobile money agents to create"),
    "reco_need_ag": ("agences telecoms a ouvrir", "telecom agencies to open"),
    "reco_reach": ("pour atteindre {v} /1000 hab.", "to reach {v} /1000 pop."),
    "reco_reach_ag": ("pour atteindre {v} /100k hab.", "to reach {v} /100k pop."),
    "reco_total": ("Investissement total", "Total investment"),
    "reco_eur": ("Equivalent euros", "Euro equivalent"),
    "reco_parite": ("parite 1 € = {v} FCFA", "peg 1 € = {v} FCFA"),
    "reco_nopop": ("Offre recensee : <b>{mm}</b> agents mobile money, <b>{ag}</b> agences "
                   "telecoms.", "Recorded supply: <b>{mm}</b> mobile money agents, "
                   "<b>{ag}</b> telecom agencies."),
    "reco_nopop2": ("La population de reference n'est pas disponible a ce niveau de detail : "
                    "selectionnez la commune ou la prefecture pour le chiffrage.",
                    "Reference population is unavailable at this level of detail: select "
                    "the commune or prefecture to run the costing."),
    "p_reco_chart": ("Budget d'investissement par prefecture prioritaire (objectif choisi)",
                     "Investment budget by priority prefecture (chosen target)"),
    "p_reco_table": ("Plan d'investissement detaille", "Detailed investment plan"),
    "reco_natbudget": ("Budget national pour l'objectif choisi : <b>{f}</b> (≈ {e}).",
                       "National budget for the chosen target: <b>{f}</b> (≈ {e})."),
    "th_needmm": ("+Agents MM", "+MM agents"),
    "th_needag": ("+Agences", "+Agencies"),
    "th_invest": ("Investissement FCFA", "Investment FCFA"),
    "th_eur": ("≈ EUR", "≈ EUR"),

    # ------- auteur -------
    "au_profile": ("Profil", "Profile"),
    "au_role": ("Analyste Statisticien", "Statistical Analyst"),
    "au_photo": ("Emplacement photo de profil (a inserer)",
                 "Profile photo placeholder (to insert)"),
    "au_about": ("A propos de ce projet", "About this project"),
    "au_about_txt": (
        "Ce tableau de bord, developpe dans le cadre du <b>Data Challenge — Economie "
        "Numerique</b> du <b>Togo AI Lab</b>, dresse un diagnostic de l'acces aux "
        "telecommunications et services numeriques au Togo. Il cartographie les "
        "infrastructures, analyse la couverture des services au regard de la population, "
        "identifie les <b>zones blanches</b> et propose des <b>recommandations "
        "d'investissement interactives</b>.",
        "This dashboard, built for the <b>Digital Economy Data Challenge</b> of the "
        "<b>Togo AI Lab</b>, provides a diagnosis of access to telecommunications and "
        "digital services in Togo. It maps the infrastructure, analyses service coverage "
        "against population, identifies <b>white zones</b> and offers <b>interactive "
        "investment recommendations</b>."),
    "au_pop": ("Population de reference : projection <b>{y}</b> a partir du RGPH-5 (2022), "
               "taux de croissance moyen {r} %/an.",
               "Reference population: projection to <b>{y}</b> from the 2022 census "
               "(RGPH-5), average growth rate {r} %/yr."),
    "au_hood": ("Sous le capot", "Under the hood"),
    "au_hood_list": (
        ["Pretraitement Python : nettoyage, fusion, indicateurs",
         "Projection demographique 2026 (taux 2,3 %)",
         "Score de priorite + simulation de couts",
         "Donnees pre-agregees en .parquet (chargement rapide)",
         "Shiny for Python · Highcharts · Highmaps"],
        ["Python preprocessing: cleaning, merging, indicators",
         "2026 demographic projection (2.3 % rate)",
         "Priority score + cost simulation",
         "Pre-aggregated .parquet data (fast loading)",
         "Shiny for Python · Highcharts · Highmaps"]),
    "au_sources": ("Sources de donnees", "Data sources"),
    "au_sources_list": (
        ["geodata.gouv.tg — agences telecoms, mobile money, datacenters",
         "RGPH-5 (2022) — population",
         "geoBoundaries — limites administratives"],
        ["geodata.gouv.tg — telecom agencies, mobile money, data centers",
         "RGPH-5 (2022) — population",
         "geoBoundaries — administrative boundaries"]),

    # ------- chart axes / series -------
    "ax_agents": ("Agents", "Agents"),
    "s_mm": ("Agents mobile money", "Mobile money agents"),
    "ax_nb_agences": ("Nombre d'agences", "Number of agencies"),
    "s_cumul_ag": ("Agences (cumul)", "Agencies (cumulative)"),
    "ax_hab_agent": ("Habitants / agent", "Inhabitants / agent"),
    "s_hab_agent": ("Habitants / agent", "Inhabitants / agent"),
    "ax_mm1000": ("Agents / 1 000 hab.", "Agents / 1,000 pop."),
    "nat_avg": ("Moyenne nationale", "National average"),
    "s_wz": ("Zones blanches", "White zones"),
    "ax_score": ("Score de priorite", "Priority score"),
    "s_invest": ("Investissement (M FCFA)", "Investment (M FCFA)"),
    "ax_invest": ("Investissement (millions FCFA)", "Investment (million FCFA)"),
    "ax_nb_cantons": ("Nombre de cantons", "Number of cantons"),
    "na": ("n.d.", "n/a"),
}


def t(lang, key, **fmt):
    v = TR.get(key)
    if v is None:
        return key
    s = v[1] if lang == "en" else v[0]
    if isinstance(s, list):
        return s
    return s.format(**fmt) if fmt else s
