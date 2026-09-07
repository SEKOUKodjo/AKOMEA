import os
import requests
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.utils import timezone

from depenses.models import Sondage, Depense, Quartier, TypeDepense


class Command(BaseCommand):
    help = "Importer les soumissions du formulaire KoboToolbox dans EcoTrack Local"

    def handle(self, *args, **options):
        # ==== Configuration lue depuis les variables d'environnement ====
        # Ne jamais coder le token en dur : le définir dans un fichier .env
        #   KOBO_ASSET_UID=...
        #   KOBO_API_TOKEN=...
        ASSET_UID = os.environ.get("KOBO_ASSET_UID", "")
        API_TOKEN = os.environ.get("KOBO_API_TOKEN", "")
        # ================================================================

        if not API_TOKEN or not ASSET_UID:
            self.stdout.write(self.style.ERROR("⚠️  Configure d'abord KOBO_ASSET_UID et KOBO_API_TOKEN (variables d'environnement)."))
            self.stdout.write("Récupère ton token sur https://kf.kobotoolbox.org/token/")
            return

        url = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_UID}/data.json"
        headers = {"Authorization": f"Token {API_TOKEN}"}

        self.stdout.write("🔄 Connexion à KoboToolbox...")
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"❌ Erreur API Kobo : {response.status_code}"))
            self.stdout.write(self.style.ERROR(response.text[:500]))
            return

        submissions = response.json().get("results", [])
        self.stdout.write(self.style.SUCCESS(f"✅ {len(submissions)} soumission(s) trouvée(s) sur Kobo."))

        imported_count = 0
        for submission in submissions:
            if self.import_submission(submission):
                imported_count += 1

        self.stdout.write(self.style.SUCCESS(f"🎉 Import terminé ! {imported_count} nouvelle(s) soumission(s) importée(s)."))

    def import_submission(self, data):
        kobo_id = data.get("_id")
        if Sondage.objects.filter(kobo_id=kobo_id).exists():
            return False  # Déjà importé

        # Mapping des champs
        sondage_data = {
            "kobo_id": kobo_id,
            "uuid": data.get("_uuid", ""),
            "submission_time": self.parse_datetime(data.get("_submission_time")),
            "validation_status": data.get("_validation_status", {}).get("uid", ""),
            "notes": data.get("_notes", ""),
            "submitted_by": data.get("_submitted_by", ""),
            "version": data.get("__version__", ""),
            "nom_et_prenom": data.get("Nom_et_prenom", ""),
            "age": self.to_int(data.get("Age")),
            "gender": data.get("gender", ""),
            "status": data.get("status", ""),
            "study": data.get("study", ""),
            "logement": data.get("logement", ""),
            "coloc": self.to_int(data.get("coloc")),
            "loyer": self.to_decimal(data.get("loyer")),
            "charges": self.to_decimal(data.get("charges")),
            "logement_satisfaction": data.get("logement_satisfaction", ""),
            "transport": data.get("transport", ""),
            "dep_transport": self.to_decimal(data.get("dep_transport")),
            "temps_trajet": self.to_int(data.get("temps_trajet")),
            "diff_transport_cout": data.get("diff_transport/cout") == "1",
            "diff_transport_insecurite": data.get("diff_transport/insecurite") == "1",
            "diff_transport_retards": data.get("diff_transport/retards") == "1",
            "diff_transport_autre": data.get("diff_transport/autre", ""),
            "freq_repas": data.get("freq_repas", ""),
            "dep_alim": self.to_decimal(data.get("dep_alim")),
            "lieu_repas": data.get("lieu_repas", ""),
            "satisfaction_repas": data.get("satisfaction_repas", ""),
            "dep_internet": self.to_decimal(data.get("dep_internet")),
            "dep_loisirs": self.to_decimal(data.get("dep_loisirs")),
            "dep_sante": self.to_decimal(data.get("dep_sante")),
            "autres_dep": self.to_decimal(data.get("autres_dep")),
            "aug_cost": data.get("aug_cost", ""),
            "diff_fin": data.get("diff_fin", ""),
            "strategies_coloc": data.get("strategies/coloc") == "1",
            "strategies_repas_maison": data.get("strategies/repas_maison") == "1",
            "strategies_pied": data.get("strategies/pied") == "1",
            "strategies_autre": data.get("strategies/autre", ""),
            "suggestions": data.get("suggestions", ""),
            "geolocation": data.get("_ge", ""),
        }

        # Gestion du quartier
        city_name = data.get("city")
        if city_name:
            quartier, _ = Quartier.objects.get_or_create(nom=city_name.strip().title())
            sondage_data["city"] = quartier

        # Création du sondage
        sondage = Sondage.objects.create(**sondage_data)

        # Création des dépenses associées
        self.create_depenses_from_sondage(sondage)

        return True

    def create_depenses_from_sondage(self, sondage):
        date = sondage.submission_time.date() if sondage.submission_time else timezone.now().date()

        # 1. Logement
        prix_logement = Decimal(0)
        if sondage.loyer:
            prix_logement += sondage.loyer
        if sondage.charges:
            prix_logement += sondage.charges

        if prix_logement > 0:
            type_dep, _ = TypeDepense.objects.get_or_create(
                nom="Loyer & Charges",
                defaults={"categorie": "LOGEMENT"}
            )
            Depense.objects.create(
                type_depense=type_dep,
                quartier=sondage.city,
                prix=prix_logement,
                lieu=sondage.logement or "Logement étudiant",
                date=date,
                commentaire=f"Colocation : {sondage.coloc or '?'} personnes | Satisfaction : {sondage.logement_satisfaction}",
                sondage=sondage,
                est_valide=True,
                est_mensuel=True,
            )

        # 2. Transport
        if sondage.dep_transport and sondage.dep_transport > 0:
            type_dep, _ = TypeDepense.objects.get_or_create(
                nom=sondage.transport or "Transport",
                defaults={"categorie": "TRANSPORT"}
            )
            Depense.objects.create(
                type_depense=type_dep,
                quartier=sondage.city,
                prix=sondage.dep_transport,
                lieu="Trajet domicile-école",
                date=date,
                commentaire=f"Mode : {sondage.transport} | Temps trajet : {sondage.temps_trajet} min",
                sondage=sondage,
                est_valide=True,
                est_mensuel=True,
            )

        # 3. Alimentation
        if sondage.dep_alim and sondage.dep_alim > 0:
            type_dep, _ = TypeDepense.objects.get_or_create(
                nom="Alimentation",
                defaults={"categorie": "RESTAURATION"}
            )
            Depense.objects.create(
                type_depense=type_dep,
                quartier=sondage.city,
                prix=sondage.dep_alim,
                lieu=sondage.lieu_repas or "Repas",
                date=date,
                commentaire=f"Fréquence : {sondage.freq_repas} | Satisfaction : {sondage.satisfaction_repas}",
                sondage=sondage,
                est_valide=True,
                est_mensuel=True,
            )

        # Tu pourras ajouter plus tard : internet, loisirs, santé, autres...

    # Fonctions utilitaires
    def to_int(self, value):
        try:
            return int(value) if value else None
        except:
            return None

    def to_decimal(self, value):
        try:
            return Decimal(value) if value else None
        except InvalidOperation:
            return None

    def parse_datetime(self, value):
        if not value:
            return timezone.now()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except:
            return timezone.now()