"""
views.py - Toutes les vues de l'application EcoTrack Local
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Min, Max, Count
from django.utils import timezone
from io import BytesIO
from datetime import datetime
from decimal import Decimal, InvalidOperation
import requests
import uuid
import os
import traceback

# ReportLab pour le PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from .models import Depense, Quartier, TypeDepense, Sondage
from .forms import DepenseForm


def accueil(request):
    """Page d'accueil avec statistiques générales"""
    depenses_valides = Depense.objects.filter(est_valide=True)
    
    stats = {
        'total_depenses': depenses_valides.count(),
        'total_quartiers': Quartier.objects.count(),
        'total_types': TypeDepense.objects.count(),
        'derniere_depense': depenses_valides.first(),
    }
    
    return render(request, 'depenses/accueil.html', {'stats': stats})


def ajouter_depense(request):
    """Formulaire d'ajout de dépense"""
    if request.method == 'POST':
        form = DepenseForm(request.POST, request.FILES)
        if form.is_valid():
            depense = form.save()
            messages.success(
                request, 
                f'Dépense ajoutée avec succès! ({depense.type_depense} - {depense.prix} FCFA)'
            )
            return redirect('liste_depenses')
        else:
            messages.error(request, 'Erreur dans le formulaire. Vérifiez les champs.')
    else:
        form = DepenseForm()
    
    return render(request, 'depenses/ajouter.html', {'form': form})


def liste_depenses(request):
    """Liste de toutes les dépenses avec filtres"""
    depenses = Depense.objects.filter(est_valide=True).select_related('type_depense', 'quartier')
    
    # Filtres optionnels
    quartier_id = request.GET.get('quartier')
    type_id = request.GET.get('type')
    categorie = request.GET.get('categorie')
    
    if quartier_id:
        depenses = depenses.filter(quartier_id=quartier_id)
    if type_id:
        depenses = depenses.filter(type_depense_id=type_id)
    if categorie:
        depenses = depenses.filter(type_depense__categorie=categorie)
    
    context = {
        'depenses': depenses,
        'quartiers': Quartier.objects.all(),
        'types': TypeDepense.objects.all(),
        'categories': TypeDepense.CATEGORIES,
    }
    
    return render(request, 'depenses/liste.html', context)


def dashboard(request):
    """Dashboard avec visualisations et statistiques"""
    depenses = Depense.objects.filter(est_valide=True)
    
    # Statistiques par quartier
    stats_quartier = depenses.values('quartier__nom').annotate(
        moyenne=Avg('prix'),
        minimum=Min('prix'),
        maximum=Max('prix'),
        nombre=Count('id')
    ).order_by('-moyenne')
    
    # Statistiques par type de dépense
    stats_type = depenses.values('type_depense__nom', 'type_depense__categorie').annotate(
        moyenne=Avg('prix'),
        nombre=Count('id')
    ).order_by('-moyenne')
    
    # Statistiques par catégorie
    stats_categorie = depenses.values('type_depense__categorie').annotate(
        moyenne=Avg('prix'),
        minimum=Min('prix'),
        maximum=Max('prix'),
        nombre=Count('id')
    ).order_by('-moyenne')
    
    # Statistiques globales
    stats_globales = depenses.aggregate(
        prix_moyen=Avg('prix'),
        prix_min=Min('prix'),
        prix_max=Max('prix'),
        total_depenses=Count('id')
    )
    
    context = {
        'stats_quartier': stats_quartier,
        'stats_type': stats_type,
        'stats_categorie': stats_categorie,
        'stats_globales': stats_globales,
        'depenses_recentes': depenses.order_by('-date')[:10],
    }
    
    return render(request, 'depenses/dashboard.html', context)


def comparaison(request):
    """Page de comparaison entre quartiers"""
    quartiers = Quartier.objects.all()
    
    # Récupérer les IDs des quartiers à comparer
    q1_id = request.GET.get('q1')
    q2_id = request.GET.get('q2')
    
    comparaison_data = None
    
    if q1_id and q2_id:
        q1 = get_object_or_404(Quartier, id=q1_id)
        q2 = get_object_or_404(Quartier, id=q2_id)
        
        # Statistiques pour le quartier 1
        stats_q1 = Depense.objects.filter(quartier=q1, est_valide=True).aggregate(
            moyenne=Avg('prix'),
            minimum=Min('prix'),
            maximum=Max('prix'),
            nombre=Count('id')
        )
        
        # Statistiques pour le quartier 2
        stats_q2 = Depense.objects.filter(quartier=q2, est_valide=True).aggregate(
            moyenne=Avg('prix'),
            minimum=Min('prix'),
            maximum=Max('prix'),
            nombre=Count('id')
        )
        
        # Statistiques par catégorie pour Q1
        stats_cat_q1 = Depense.objects.filter(
            quartier=q1, est_valide=True
        ).values('type_depense__categorie').annotate(
            moyenne=Avg('prix'),
            nombre=Count('id')
        )
        
        # Statistiques par catégorie pour Q2
        stats_cat_q2 = Depense.objects.filter(
            quartier=q2, est_valide=True
        ).values('type_depense__categorie').annotate(
            moyenne=Avg('prix'),
            nombre=Count('id')
        )
        
        comparaison_data = {
            'q1': {
                'nom': q1.nom,
                'stats': stats_q1,
                'par_categorie': stats_cat_q1
            },
            'q2': {
                'nom': q2.nom,
                'stats': stats_q2,
                'par_categorie': stats_cat_q2
            },
        }
        
        # Calculer la différence
        if stats_q1['moyenne'] and stats_q2['moyenne']:
            comparaison_data['difference_pourcent'] = (
                (stats_q1['moyenne'] - stats_q2['moyenne']) / stats_q2['moyenne'] * 100
            )
    
    context = {
        'quartiers': quartiers,
        'comparaison': comparaison_data,
    }
    
    return render(request, 'depenses/comparaison.html', context)


# ============ FONCTIONS UTILITAIRES POUR Kobo ============

def to_int(value):
    """Convertir en entier"""
    try:
        return int(value) if value else None
    except:
        return None


def to_decimal(value):
    """Convertir en Decimal"""
    try:
        return Decimal(value) if value else None
    except InvalidOperation:
        return None


def parse_datetime(value):
    """Parser une date"""
    if not value:
        return timezone.now()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except:
        return timezone.now()


def create_depenses_from_sondage(sondage):
    """Créer les dépenses à partir d'un sondage"""
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
    
    # 4. Internet
    if sondage.dep_internet and sondage.dep_internet > 0:
        type_dep, _ = TypeDepense.objects.get_or_create(
            nom="Internet",
            defaults={"categorie": "SERVICES"}
        )
        Depense.objects.create(
            type_depense=type_dep,
            quartier=sondage.city,
            prix=sondage.dep_internet,
            lieu="Abonnement mensuel",
            date=date,
            commentaire="Coût mensuel d'internet",
            sondage=sondage,
            est_valide=True,
            est_mensuel=True,
        )
    
    # 5. Loisirs
    if sondage.dep_loisirs and sondage.dep_loisirs > 0:
        type_dep, _ = TypeDepense.objects.get_or_create(
            nom="Loisirs",
            defaults={"categorie": "SERVICES"}
        )
        Depense.objects.create(
            type_depense=type_dep,
            quartier=sondage.city,
            prix=sondage.dep_loisirs,
            lieu="Activités récréatives",
            date=date,
            commentaire="Dépenses mensuelles de loisirs",
            sondage=sondage,
            est_valide=True,
            est_mensuel=True,
        )
    
    # 6. Santé
    if sondage.dep_sante and sondage.dep_sante > 0:
        type_dep, _ = TypeDepense.objects.get_or_create(
            nom="Santé",
            defaults={"categorie": "SERVICES"}
        )
        Depense.objects.create(
            type_depense=type_dep,
            quartier=sondage.city,
            prix=sondage.dep_sante,
            lieu="Soins médicaux",
            date=date,
            commentaire="Dépenses mensuelles de santé",
            sondage=sondage,
            est_valide=True,
            est_mensuel=True,
        )
    
    # 7. Autres dépenses
    if sondage.autres_dep and sondage.autres_dep > 0:
        type_dep, _ = TypeDepense.objects.get_or_create(
            nom="Autres dépenses",
            defaults={"categorie": "AUTRES"}
        )
        Depense.objects.create(
            type_depense=type_dep,
            quartier=sondage.city,
            prix=sondage.autres_dep,
            lieu="Divers",
            date=date,
            commentaire="Autres dépenses mensuelles",
            sondage=sondage,
            est_valide=True,
            est_mensuel=True,
        )


def create_sondage(data):
    """Créer un nouveau sondage - PAS DE VÉRIFICATION D'EXISTANCE"""
    try:
        kobo_id = data.get("_id")
        
        sondage_data = {
            "kobo_id": kobo_id,
            "uuid": data.get("_uuid", ""),
            "submission_time": parse_datetime(data.get("_submission_time")),
            "validation_status": data.get("_validation_status", {}).get("uid", ""),
            "notes": data.get("_notes", ""),
            "submitted_by": data.get("_submitted_by", ""),
            "version": data.get("__version__", ""),
            "nom_et_prenom": data.get("Nom_et_prenom", ""),
            "age": to_int(data.get("Age")),
            "gender": data.get("gender", ""),
            "status": data.get("status", ""),
            "study": data.get("study", ""),
            "logement": data.get("logement", ""),
            "coloc": to_int(data.get("coloc")),
            "loyer": to_decimal(data.get("loyer")),
            "charges": to_decimal(data.get("charges")),
            "logement_satisfaction": data.get("logement_satisfaction", ""),
            "transport": data.get("transport", ""),
            "dep_transport": to_decimal(data.get("dep_transport")),
            "temps_trajet": to_int(data.get("temps_trajet")),
            "diff_transport_cout": data.get("diff_transport/cout") == "1",
            "diff_transport_insecurite": data.get("diff_transport/insecurite") == "1",
            "diff_transport_retards": data.get("diff_transport/retards") == "1",
            "diff_transport_autre": data.get("diff_transport/autre", ""),
            "freq_repas": data.get("freq_repas", ""),
            "dep_alim": to_decimal(data.get("dep_alim")),
            "lieu_repas": data.get("lieu_repas", ""),
            "satisfaction_repas": data.get("satisfaction_repas", ""),
            "dep_internet": to_decimal(data.get("dep_internet")),
            "dep_loisirs": to_decimal(data.get("dep_loisirs")),
            "dep_sante": to_decimal(data.get("dep_sante")),
            "autres_dep": to_decimal(data.get("autres_dep")),
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
        create_depenses_from_sondage(sondage)
        
        return True
        
    except Exception as e:
        print(f"Erreur création sondage: {e}")
        return False


@staff_member_required
def import_kobo(request):
    """Import des données Kobo via interface web - REMPLACE TOUTES LES DONNÉES"""
    try:
        # ==== CONFIGURATION Kobo (variables d'environnement) ====
        ASSET_UID = os.environ.get("KOBO_ASSET_UID", "")
        API_TOKEN = os.environ.get("KOBO_API_TOKEN", "")

        if not API_TOKEN or not ASSET_UID:
            return JsonResponse({
                'success': False,
                'message': "Token API Kobo non configuré (définir KOBO_ASSET_UID et KOBO_API_TOKEN)"
            })
        
        # ÉTAPE 1: SUPPRIMER TOUTES LES DONNÉES EXISTANTES
        ancien_compte_sondages = Sondage.objects.count()
        ancien_compte_depenses = Depense.objects.filter(sondage__isnull=False).count()
        
        # Supprimer toutes les dépenses liées aux sondages
        Depense.objects.filter(sondage__isnull=False).delete()
        
        # Supprimer tous les sondages
        Sondage.objects.all().delete()
        
        # ÉTAPE 2: RÉCUPÉRER LES NOUVELLES DONNÉES
        url = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_UID}/data.json"
        headers = {"Authorization": f"Token {API_TOKEN}"}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return JsonResponse({
                'success': False,
                'message': f'Erreur API Kobo: {response.status_code} - {response.text[:200]}'
            })
        
        submissions = response.json().get("results", [])
        
        if not submissions:
            return JsonResponse({
                'success': True,
                'message': 'Aucune donnée disponible sur KoboToolbox',
                'imported': 0,
                'updated': 0,
                'total': 0,
                'anciens_sondages': ancien_compte_sondages,
                'anciennes_depenses': ancien_compte_depenses
            })
        
        imported_count = 0
        
        # ÉTAPE 3: IMPORTER TOUTES LES NOUVELLES DONNÉES
        for submission in submissions:
            if create_sondage(submission):
                imported_count += 1
        
        # ÉTAPE 4: COMPTER LES NOUVELLES DÉPENSES
        nouveau_compte_depenses = Depense.objects.filter(sondage__isnull=False).count()
        
        return JsonResponse({
            'success': True,
            'message': f'Synchronisation COMPLÈTE réussie! {imported_count} nouveaux sondages importés',
            'imported': imported_count,
            'updated': 0,  # Pas de mise à jour, tout est remplacé
            'total': len(submissions),
            'anciens_sondages': ancien_compte_sondages,
            'anciennes_depenses': ancien_compte_depenses,
            'nouveaux_sondages': imported_count,
            'nouvelles_depenses': nouveau_compte_depenses,
            'supprime': True
        })
        
    except Exception as e:
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}',
            'details': error_details[:500]
        })


def synchroniser_kobo(request):
    """Page de synchronisation avec avertissement"""
    # Compter les données actuelles pour affichage
    sondages_count = Sondage.objects.count()
    depenses_kobo_count = Depense.objects.filter(sondage__isnull=False).count()
    
    context = {
        'sondages_count': sondages_count,
        'depenses_kobo_count': depenses_kobo_count,
    }
    
    return render(request, 'depenses/synchroniser.html', context)


def config_rapport(request):
    """Page de configuration du rapport PDF"""
    return render(request, 'depenses/config_rapport.html')


def generer_rapport_pdf(request):
    """Générer un rapport PDF avec logo ISSEA"""
    
    # Récupérer les paramètres
    professeur = request.GET.get('professeur', 'Prof. [Nom du Professeur]')
    etudiants = request.GET.get('etudiants', 'Étudiant 1, Étudiant 2, Étudiant 3, Étudiant 4')
    promotion = request.GET.get('promotion', 'AS3 2025')
    
    # Créer le buffer PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.HexColor('#2c3e50')
    )
    
    sub_style = ParagraphStyle(
        'CustomSub',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor('#3498db')
    )
    
    # Header avec logo
    try:
        logo_path = os.path.join('static', 'logo_issea.png')
        if os.path.exists(logo_path):
            img = Image(logo_path, width=1.5*inch, height=1.5*inch)
            elements.append(img)
            elements.append(Spacer(1, 10))
    except:
        pass
    
    # Titre de l'établissement
    elements.append(Paragraph("INSTITUT SOUS-RÉGIONAL DE STATISTIQUE ET D'ÉCONOMIE APPLIQUÉE", 
                             ParagraphStyle('Title', parent=styles['Title'], fontSize=16, alignment=TA_CENTER)))
    elements.append(Paragraph("(ISSEA)", ParagraphStyle('SubTitle', parent=styles['Title'], fontSize=14, alignment=TA_CENTER)))
    elements.append(Paragraph("ÉCOLE INTER-ÉTATS", styles['Normal']))
    elements.append(Paragraph(f"Yaoundé - {datetime.now().year}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Titre du rapport
    elements.append(Paragraph("RAPPORT DE COLLECTE DE DONNÉES", title_style))
    elements.append(Paragraph("ÉcoTrack Local - Suivi des coûts de vie étudiants", sub_style))
    elements.append(Spacer(1, 20))
    
    # Informations de l'équipe
    info_data = [
        [Paragraph("<b>Professeur encadrant:</b>", styles['Normal']), Paragraph(professeur, styles['Normal'])],
        [Paragraph("<b>Étudiants:</b>", styles['Normal']), Paragraph(etudiants, styles['Normal'])],
        [Paragraph("<b>Promotion:</b>", styles['Normal']), Paragraph(promotion, styles['Normal'])],
        [Paragraph("<b>Date de génération:</b>", styles['Normal']), 
         Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M"), styles['Normal'])],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 30))
    
    # Récupérer les statistiques
    depenses = Depense.objects.filter(est_valide=True)
    sondages = Sondage.objects.all()
    
    # Statistiques globales
    stats_globales = depenses.aggregate(
        total=Count('id'),
        moyenne=Avg('prix'),
        minimum=Min('prix'),
        maximum=Max('prix')
    )
    
    # Tableau des statistiques globales
    stats_data = [
        ['Statistiques Globales', 'Valeur'],
        ['Nombre total de dépenses', f"{stats_globales['total'] or 0}"],
        ['Prix moyen', f"{stats_globales['moyenne'] or 0:.0f} FCFA"],
        ['Prix minimum', f"{stats_globales['minimum'] or 0:.0f} FCFA"],
        ['Prix maximum', f"{stats_globales['maximum'] or 0:.0f} FCFA"],
        ['Nombre de sondages Kobo', f"{sondages.count()}"],
        ['Nombre de quartiers couverts', f"{Quartier.objects.count()}"],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 3*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ]))
    
    elements.append(Paragraph("Statistiques de Collecte", styles['Heading2']))
    elements.append(Spacer(1, 10))
    elements.append(stats_table)
    elements.append(Spacer(1, 30))
    
    # Statistiques par quartier
    stats_quartier = depenses.values('quartier__nom').annotate(
        moyenne=Avg('prix'),
        nombre=Count('id')
    ).order_by('-moyenne')
    
    if stats_quartier:
        quartier_data = [['Quartier', 'Nombre', 'Prix Moyen (FCFA)']]
        for stat in stats_quartier:
            quartier_data.append([
                stat['quartier__nom'],
                str(stat['nombre']),
                f"{stat['moyenne']:.0f}"
            ])
        
        quartier_table = Table(quartier_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        quartier_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ]))
        
        elements.append(Paragraph("Répartition par Quartier", styles['Heading2']))
        elements.append(Spacer(1, 10))
        elements.append(quartier_table)
        elements.append(Spacer(1, 30))
    
    # Statistiques par catégorie
    stats_categorie = depenses.values('type_depense__categorie').annotate(
        moyenne=Avg('prix'),
        nombre=Count('id')
    ).order_by('-nombre')
    
    if stats_categorie:
        categorie_data = [['Catégorie', 'Nombre', 'Prix Moyen (FCFA)']]
        for stat in stats_categorie:
            categorie_data.append([
                stat['type_depense__categorie'],
                str(stat['nombre']),
                f"{stat['moyenne']:.0f}"
            ])
        
        categorie_table = Table(categorie_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        categorie_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ]))
        
        elements.append(Paragraph("Répartition par Catégorie", styles['Heading2']))
        elements.append(Spacer(1, 10))
        elements.append(categorie_table)
        elements.append(Spacer(1, 30))
    
    # Dépenses récentes
    depenses_recentes = depenses.order_by('-date')[:10]
    if depenses_recentes:
        recentes_data = [['Date', 'Type', 'Quartier', 'Prix (FCFA)']]
        for dep in depenses_recentes:
            recentes_data.append([
                dep.date.strftime("%d/%m/%Y"),
                dep.type_depense.nom[:20],
                dep.quartier.nom,
                f"{dep.prix:.0f}"
            ])
        
        recentes_table = Table(recentes_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
        recentes_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(Paragraph("Dépenses Récentes (10 dernières)", styles['Heading2']))
        elements.append(Spacer(1, 10))
        elements.append(recentes_table)
        elements.append(Spacer(1, 30))
    
    # Conclusion
    elements.append(Paragraph("Conclusion", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    conclusion_text = """
    Ce rapport présente les données collectées par le système ÉcoTrack Local pour le suivi des coûts de vie étudiants à Yaoundé.
    Les données ont été collectées de manière participative et permettent d'analyser les tendances de prix selon les quartiers
    et les types de dépenses. Le système continue d'évoluer pour offrir des analyses plus fines et des visualisations améliorées.
    """
    
    elements.append(Paragraph(conclusion_text, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Pied de page
    footer_text = f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | Projet AS3 ISSEA 2025 | ÉcoTrack Local"
    elements.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey
    )))
    
    # Générer le PDF
    doc.build(elements)
    
    # Récupérer la valeur du buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Créer la réponse HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_ecotrack_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    response.write(pdf)
    
    return response