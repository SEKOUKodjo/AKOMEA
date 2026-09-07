# EcoTrack Local

**EcoTrack Local** est une application web développée avec **Django** permettant de collecter, importer, analyser et visualiser les **dépenses de la vie étudiante** dans les quartiers de Yaoundé. Elle s'appuie sur les données d'un formulaire d'enquête **KoboToolbox** et produit des tableaux de bord ainsi que des rapports PDF.

> Projet réalisé par le **Groupe 9** — ISSEA.

---

## Fonctionnalités

- **Saisie manuelle** de dépenses (type, quartier, prix, lieu, date, justificatif photo).
- **Import automatique** des soumissions du formulaire **KoboToolbox** (via l'API).
- **Synchronisation** des données depuis l'interface web.
- **Tableau de bord** avec statistiques (moyennes, minima, maxima, répartition par catégorie).
- **Comparaison** des dépenses entre quartiers.
- **Détection d'anomalies** : doublons et valeurs aberrantes (méthode de l'écart interquartile / IQR).
- **Génération de rapports PDF** personnalisables (ReportLab).
- **Interface d'administration** Django.

---

## Technologies

- **Python** 3.11+
- **Django** 5.2
- **pandas / numpy / scipy** — analyse de données
- **reportlab** — génération des PDF
- **requests** — appels à l'API KoboToolbox
- **Pillow** — gestion des images
- **SQLite** — base de données par défaut

---

## Structure du projet

```
ecotrack_local/
├── manage.py
├── requirements.txt
├── .env.example
├── ecotrack_local/          # Configuration du projet Django
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── depenses/                # Application principale
│   ├── models.py            # Quartier, TypeDepense, Sondage, Depense
│   ├── views.py             # Vues (dashboard, import, PDF, etc.)
│   ├── forms.py
│   ├── urls.py
│   ├── analyse.py           # Détection d'anomalies
│   ├── admin.py
│   ├── management/commands/
│   │   └── importer_kobo.py # Commande d'import KoboToolbox
│   └── templates/depenses/  # Gabarits HTML
└── static/                  # Fichiers statiques (logo, etc.)
```

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/sekoukodjo/akomea.git
cd akomea
```

### 2. Créer et activer un environnement virtuel

```bash
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Copiez le modèle et renseignez vos valeurs :

```bash
cp .env.example .env
```

Puis exportez-les avant de lancer l'application (ou utilisez un outil comme `python-dotenv`) :

```bash
export KOBO_ASSET_UID="votre_asset_uid"
export KOBO_API_TOKEN="votre_token_api"
```

> Le token KoboToolbox se récupère sur https://kf.kobotoolbox.org/token/

### 5. Appliquer les migrations

```bash
python manage.py migrate
```

### 6. Créer un compte administrateur

```bash
python manage.py createsuperuser
```

### 7. Lancer le serveur de développement

```bash
python manage.py runserver
```

L'application est accessible sur **http://127.0.0.1:8000/**
et l'administration sur **http://127.0.0.1:8000/admin/**

---

## Import des données KoboToolbox

Une fois les variables d'environnement configurées :

```bash
python manage.py importer_kobo
```

L'import est également disponible depuis l'interface web (page **Synchroniser**, réservée au personnel administrateur).

---

## Sécurité

- ⚠️ **Ne publiez jamais** votre token KoboToolbox ni de clé secrète sur GitHub. Ils doivent rester dans le fichier `.env` (ignoré par Git).
- Le paramètre `DEBUG = True` et la `SECRET_KEY` par défaut conviennent **uniquement au développement**. En production, désactivez `DEBUG`, définissez une `SECRET_KEY` propre et configurez `ALLOWED_HOSTS`.
- La base de données `db.sqlite3` et le dossier `media/` ne sont pas versionnés (voir `.gitignore`).

---

## Auteurs

Projet **Groupe 9** — ISSEA (Institut Sous-régional de Statistique et d'Économie Appliquée).
"# AKOMEA"  
