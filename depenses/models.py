from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid


class Quartier(models.Model):
    """
    Quartier de Yaoundé (ex: TITI GARAGE, Ngoa-Ekellé, etc.)
    """
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)      # Pour géolocalisation Kobo (_ge)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Quartier"
        verbose_name_plural = "Quartiers"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class TypeDepense(models.Model):
    """
    Types de dépenses avec catégories prédéfinies
    """
    CATEGORIES = [
        ('TRANSPORT', 'Transport'),
        ('LOGEMENT', 'Logement'),
        ('RESTAURATION', 'Restauration'),
        ('SERVICES', 'Services'),       # Internet, santé, loisirs, etc.
        ('AUTRES', 'Autres'),
    ]

    nom = models.CharField(max_length=100)
    categorie = models.CharField(max_length=20, choices=CATEGORIES, default='AUTRES')

    class Meta:
        verbose_name = "Type de dépense"
        verbose_name_plural = "Types de dépenses"
        ordering = ['categorie', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_categorie_display()})"


class Sondage(models.Model):
    """
    Représente une soumission complète du formulaire KoboToolbox
    """
    # Métadonnées Kobo
    kobo_id = models.CharField(max_length=50, unique=True, help_text="Champ _id de Kobo")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, help_text="Champ _uuid")
    submission_time = models.DateTimeField(help_text="Date et heure de soumission")
    validation_status = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True)
    submitted_by = models.CharField(max_length=100, blank=True, null=True)  # ← Corrigé ici
    version = models.CharField(max_length=50, blank=True, null=True)

    # Données personnelles
    nom_et_prenom = models.CharField(max_length=200, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=50, blank=True)
    study = models.CharField(max_length=50, blank=True)

    # Localisation
    city = models.ForeignKey(Quartier, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='sondages', verbose_name="Quartier")
    geolocation = models.CharField(max_length=100, blank=True)

    # Logement
    logement = models.CharField(max_length=100, blank=True)
    coloc = models.PositiveIntegerField(null=True, blank=True)
    loyer = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    logement_satisfaction = models.CharField(max_length=50, blank=True)

    # Transport
    transport = models.CharField(max_length=50, blank=True)
    dep_transport = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    temps_trajet = models.PositiveIntegerField(null=True, blank=True)
    diff_transport_cout = models.BooleanField(default=False)
    diff_transport_insecurite = models.BooleanField(default=False)
    diff_transport_retards = models.BooleanField(default=False)
    diff_transport_autre = models.TextField(blank=True)

    # Alimentation
    freq_repas = models.CharField(max_length=50, blank=True)
    dep_alim = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lieu_repas = models.CharField(max_length=100, blank=True)
    satisfaction_repas = models.CharField(max_length=50, blank=True)

    # Autres dépenses mensuelles
    dep_internet = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dep_loisirs = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dep_sante = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    autres_dep = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Difficultés et stratégies
    aug_cost = models.CharField(max_length=50, blank=True)
    diff_fin = models.TextField(blank=True)
    strategies_coloc = models.BooleanField(default=False)
    strategies_repas_maison = models.BooleanField(default=False)
    strategies_pied = models.BooleanField(default=False)
    strategies_autre = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)

    class Meta:
        verbose_name = "Sondage Kobo"
        verbose_name_plural = "Sondages Kobo"
        ordering = ['-submission_time']

    def __str__(self):
        return f"Sondage {self.kobo_id} - {self.nom_et_prenom or 'Anonyme'} ({self.submission_time.date() if self.submission_time else 'N/A'})"

class Depense(models.Model):
    """
    Dépense individuelle (peut provenir du formulaire manuel ou être générée depuis un Sondage Kobo)
    """
    type_depense = models.ForeignKey(TypeDepense, on_delete=models.CASCADE)
    quartier = models.ForeignKey(Quartier, on_delete=models.CASCADE)
    prix = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    lieu = models.CharField(max_length=200)
    date = models.DateField(default=timezone.now)
    commentaire = models.TextField(blank=True)
    photo = models.ImageField(upload_to='justificatifs/', blank=True, null=True)

    # Lien avec le sondage Kobo (optionnel)
    sondage = models.ForeignKey(Sondage, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='depenses')

    # Indicateurs
    est_mensuel = models.BooleanField(default=False, help_text="Dépense mensuelle agrégée (provenant de Kobo)")
    est_valide = models.BooleanField(default=True)
    est_aberrant = models.BooleanField(default=False)
    justification_anomalie = models.TextField(blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-date_creation']
        verbose_name = 'Dépense'
        verbose_name_plural = 'Dépenses'

    def __str__(self):
        source = " (Kobo)" if self.sondage else ""
        return f"{self.type_depense} - {self.prix} FCFA - {self.quartier}{source}"