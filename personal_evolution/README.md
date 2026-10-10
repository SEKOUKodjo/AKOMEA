# Personal Evolution Intelligence (PEI)

Système personnel, entièrement local, qui transforme le vécu quotidien en données
pour mieux comprendre son évolution.

> Observer, collecter, structurer, analyser, apprendre, prédire, recommander, observer à nouveau.

```
Téléphone (PWA)  ──Wi-Fi local──▶  FastAPI (PC)  ──▶  SQLite + storage/ + IA locale
                                                   └─▶  Shiny for Python (tableau de bord)
```

Couleurs du drapeau togolais (vert `#006A4E`, jaune `#FFCE00`, rouge `#D21034`, blanc),
icônes dessinées en Python (`backend/icons.py`), aucun emoji.

## Contenu du dossier

| Élément | Description |
|---|---|
| `README.md` | ce fichier : installation et utilisation |
| `docs/RAPPORT.pdf` | rapport explicatif complet (conception, méthodes, résultats, limites) |
| `docs/RAPPORT.md` | même rapport au format texte |
| `docs/MCD.pdf` | Modèle Conceptuel de Données : schéma, associations, cardinalités, propriétés de chaque table, MLD |
| `docs/MCD.md`, `docs/mcd.svg`, `docs/mcd.png` | même contenu en texte, schéma vectoriel et image |
| `docs/windesign/` | script SQL et guide pour ouvrir le MCD dans WinDesign (rétroconception) |
| `docs/captures/` | captures d'écran du téléphone et du tableau de bord |
| `backend/`, `ai/`, `frontend/`, `dashboard/` | code source |
| `tests/` | tests automatisés |
| `scripts/generer_rapport.py` | régénère le rapport (`pip install reportlab`) |
| `scripts/generer_mcd.py` | régénère le MCD à partir des modèles du code |
| `scripts/exporter_windesign.py` | régénère le script SQL pour WinDesign |

## Prérequis

Python 3.10 ou plus récent, un PC et un téléphone connectés au même Wi-Fi.

## Démarrage

```bash
cd personal_evolution
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
pip install faster-whisper                              # facultatif : transcription audio locale

python run.py all                  # API + interface téléphone (8000) et tableau de bord (8001)
```

Le terminal affiche l'adresse à ouvrir sur le téléphone, par exemple `http://192.168.1.20:8000`.
Dans le navigateur du téléphone : menu, puis **Ajouter à l'écran d'accueil**.

Pour découvrir l'application avec des données fictives sans toucher à ta vraie base :

```bash
python run.py demo                          # crée data/demo.db (150 jours simulés)
python run.py all --db data/demo.db
```

Autres commandes :

| Commande | Rôle |
|---|---|
| `python run.py serve` | API et interface téléphone seules |
| `python run.py dashboard` | tableau de bord Shiny seul |
| `python run.py backup --to /media/cle_usb` | sauvegarde (base cohérente et médias) en archive zip |
| `python run.py reindex` | reconstruit l'index de la mémoire |
| `PEI_PIN=4821 python run.py all` | protège l'accès par un code PIN |
| `python run.py serve --cert cert.pem --key key.pem` | HTTPS local, active l'enregistrement direct au micro |
| `python -m pytest` | tests automatisés |

## Utilisation quotidienne

**Matin.** Tu écris ou dictes tes intentions. Le moteur d'extraction propose une liste
structurée (dimension, type d'activité, durée, priorité) que tu corriges puis valides.
Pour chaque durée saisie, PEI indique ce que ce type de tâche prend réellement chez toi.

**Journée.** Activités réalisées (reliées ou non à une intention), notes, réflexions,
passages bibliques, photos, vidéos, audios, documents.

**Soir.** Tu racontes ta journée. PEI préremplit le bilan : statut de chaque intention,
temps réel, résultat, raison d'un abandon, apprentissages, émotions repérées.

**Ensuite.** Bilan sur le téléphone, analyse complète dans Shiny, mémoire interrogeable
(« Qu'est ce qui m'a marqué le mois dernier ? »).

## Améliorations apportées à la conception initiale

1. **Intention et Objectif séparés.** Le cahier des charges appelait `Goal` l'élément
   quotidien. PEI distingue l'`Intention` (ce que je veux faire aujourd'hui) de l'`Objectif`
   hiérarchique (vision, long terme, annuel, mensuel, hebdomadaire). Chaque intention peut
   être reliée à un objectif, et le temps investi remonte jusqu'à la vision.
2. **Provenance complète.** Chaque saisie crée une `Source` immuable (texte brut ou audio).
   Chaque proposition de l'IA est une `Extraction` conservée avec son statut
   (proposée, validée telle quelle, corrigée). L'IA ne modifie jamais l'historique en silence,
   et le taux de correction mesure la qualité de l'extraction dans le temps.
3. **Intégrité des médias.** Chaque fichier est conservé tel quel avec son empreinte SHA 256.
   Une transcription corrigée à la main n'efface ni l'audio ni la trace du moteur.
4. **Partiel n'est pas un échec.** Le taux de réalisation compte une réalisation partielle
   pour moitié, et les intentions non encore évaluées sont exclues du calcul.
5. **Prédictions qui s'adaptent à la quantité de données.** Peu d'historique : taux de base
   lissés (bayésien). Assez d'historique : régression logistique validée par validation
   croisée temporelle (AUC affichée). Toute prédiction est enregistrée pour être comparée
   plus tard à la réalité.
6. **Statistique prudente.** Corrélations de Spearman avec correction de Benjamini Hochberg,
   exclusion des paires mécaniquement liées, détection d'anomalies robuste (médiane et MAD),
   tests non paramétriques pour les tendances et les expériences. Chaque recommandation
   affiche ses données justificatives et une mise en garde sur la causalité.
7. **Expériences personnelles mesurées.** Une hypothèse est comparée à une période de
   référence de même durée (test de Mann Whitney, delta de Cliff).
8. **Scénarios par simulation.** « 1 h 30 de Python par jour pendant 3 mois » est simulé
   (Monte Carlo) avec ta régularité passée et tes écarts d'estimation : fourchette prudente,
   médiane et favorable, jamais une certitude.
9. **Relations sans score.** On enregistre les échanges et un rythme souhaité ; PEI rappelle
   simplement une relation à entretenir.
10. **Compétences : ressenti et preuves.** Les activités sont rattachées automatiquement aux
    compétences par mots clés ; heures, preuves (exercices, projets, tests) et auto
    évaluation sont affichées côte à côte, avec une projection prudente.

## Architecture

```
personal_evolution/
├── run.py                     commandes (serve, dashboard, all, demo, backup, reindex)
├── backend/
│   ├── main.py                application FastAPI, interface et icônes
│   ├── config.py              chemins et réglages (variables PEI_*)
│   ├── db.py                  SQLite (WAL, clés étrangères)
│   ├── models.py              modèle de données
│   ├── schemas.py             schémas d'échange
│   ├── domain.py              dimensions, horizons, statuts
│   ├── icons.py               icônes SVG et icônes PNG de l'application, en Python
│   ├── api/                   routes : daily, media, planning, statistics
│   └── services/              days, analytics, memory (FTS5), ask, skills, media, backup, demo
├── ai/
│   ├── nlp/                   extraction en français (durées, dimensions, résultats, raisons)
│   ├── transcription/         Whisper local (faster-whisper ou openai-whisper)
│   └── ml/                    prédiction de réalisation, de durée, simulation, projection
├── frontend/                  PWA : index.html, manifest.json, service-worker.js, src/
├── dashboard/app.py           Shiny for Python
├── data/                      personal.db (non versionné)
├── storage/                   audio, video, images, documents (non versionnés)
└── tests/
```

### Modèle de données

`Day`, `Intention`, `Activity`, `Reflection`, `Goal`, `Source`, `Extraction`, `Media`,
`Skill`, `SkillProgress`, `Decision`, `Experiment`, `Person`, `Interaction`, `Prediction`.

### API principale

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/api/morning/parse` | analyse le texte du matin (proposition, rien n'est appliqué) |
| POST | `/api/morning` | enregistre les intentions validées et les indicateurs |
| POST | `/api/evening/parse` | analyse le bilan libre et le rapproche des intentions |
| POST | `/api/evening` | enregistre le bilan |
| POST | `/api/audio`, `/api/media` | conserve le fichier, lance la transcription locale |
| GET | `/api/days`, `/api/days/{date}` | journées et détail |
| GET | `/api/goals`, `/api/goals/progress` | objectifs et progression |
| GET | `/api/activities`, `/api/reflections` | historique |
| GET | `/api/statistics/*` | résumé, série quotidienne, calibration, tendances, anomalies, corrélations |
| GET | `/api/insights` | recommandations justifiées |
| POST | `/api/predict/completion`, `/api/predict/duration`, `/api/simulate` | estimations |
| GET | `/api/memory/search`, `/api/memory/ask` | mémoire personnelle |
| GET | `/api/sources/{id}` | remonter à la donnée brute |
| POST | `/api/system/backup` | sauvegarde |

Documentation interactive : `http://127.0.0.1:8000/docs`.

## Confidentialité

Aucune donnée ne quitte le PC. Pas de cloud, pas de service externe, pas de bibliothèque
chargée depuis Internet. Le dossier `data/`, le dossier `storage/` et les sauvegardes sont
exclus de Git. Le microphone du navigateur exige HTTPS sur une adresse réseau : en HTTP,
l'import de fichier audio (qui ouvre l'enregistreur du téléphone) fonctionne toujours.

## Feuille de route

Les phases 1 à 8 du cahier des charges disposent d'une première version. Pistes suivantes :
modèle NLP local plus riche (Transformers) en complément du moteur à règles, recherche
sémantique par embeddings locaux, chiffrement de la base (SQLCipher), synchronisation
automatique des sauvegardes vers un disque externe, résumé mensuel généré automatiquement.
