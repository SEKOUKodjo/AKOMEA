# Tableau de bord — Acces aux telecommunications & services numeriques au Togo

Diagnostic territorial de l'economie numerique togolaise (agences telecoms, agents
mobile money, datacenters) rapporte a la population, identification des **zones
blanches** et **simulateur d'investissement** (FCFA / EUR).

**Data Challenge — Economie Numerique · Togo AI Lab**
Auteur : *Maurice Kodjo SEKOU — Analyste Statisticien*
Stack : **Shiny for Python · Highcharts / Highmaps** (embarques localement).

---

## 1. Contenu du projet

```
dashboard_econ_num/
├── app.py                  # Application Shiny for Python (8 onglets)
├── prepare_data.py         # Pipeline de pretraitement -> data/*.parquet
├── requirements.txt
├── modules/
│   ├── theme.py            # Palette drapeau togolais + helpers Highcharts/Highmaps
│   └── recommender.py      # Modele d'estimation des investissements
├── data/                   # Donnees PRE-AGREGEES (chargement rapide)
│   ├── prefectures.parquet · regions.parquet · cantons.parquet
│   ├── points_infra.parquet · points_mobile_money.parquet
│   ├── geo_prefectures.json · geo_regions.json · meta.json
├── data_raw/               # Donnees brutes (pour reproduire le pipeline)
├── www/                    # Assets statiques
│   ├── js/                 # Highcharts / Highmaps embarques (aucune dependance CDN)
│   └── geo/                # GeoJSON servis a la carte
└── rapport/
    ├── Rapport_Methodologique_Economie_Numerique_Togo.docx
    ├── Presentation_Economie_Numerique_Togo.pptx
    ├── figures/            # Figures analytiques (couleurs drapeau togolais)
    ├── make_figures.py · build_word.py · build_pptx.py
```

## 2. Lancer le tableau de bord

```bash
pip install -r requirements.txt
shiny run --reload app.py
# puis ouvrir http://127.0.0.1:8000
```

Pour un deploiement (shinyapps.io, serveur, conteneur), le point d'entree est
`app.py` (objet `app`). L'application est **autonome** : Highcharts est servi
depuis `www/js`, aucune connexion CDN n'est requise a l'execution.

## 3. Reproduire les analyses (facultatif)

```bash
python prepare_data.py                 # regenere data/*.parquet + meta.json
python rapport/make_figures.py         # regenere les figures
python rapport/build_word.py           # regenere le rapport Word
python rapport/build_pptx.py           # regenere la presentation
```

## 4. Performance

Toutes les analyses lourdes sont **pre-calculees** par `prepare_data.py` et
stockees en `.parquet` (< 1 Mo au total) + GeoJSON simplifie. L'application ne
fait aucun calcul couteux au demarrage : le chargement est de l'ordre de la
seconde.

## 5. Onglets

1. **Accueil** — KPI + vue d'ensemble
2. **Infrastructures** — carte des agences & datacenters
3. **Services numeriques** — densite mobile money vs population
4. **Zones blanches** — cantons non desservis
5. **Priorites** — score composite de priorisation
6. **Recommandations** — simulateur d'investissement interactif (FCFA / EUR)
7. **Carte** — carte nationale multi-indicateurs
8. **Auteur** — profil & methodologie

## 6. Personnalisation des images

Les emplacements de logos (bandeau), d'armoiries et la photo de profil (onglet
Auteur) sont des **placeholders** a remplacer par vos propres images.

## 7. Sources

- `geodata.gouv.tg` — agences telecoms, agents mobile money, datacenters
- **RGPH-5 (2022)** — population (projetee 2026 au taux de 2,3 %/an)
- **geoBoundaries** — limites administratives (region / prefecture / canton)
