from django.urls import path
from . import views

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('ajouter/', views.ajouter_depense, name='ajouter_depense'),
    path('liste/', views.liste_depenses, name='liste_depenses'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('comparaison/', views.comparaison, name='comparaison'),
    
    # Nouvelles URLs
    path('import-kobo/', views.import_kobo, name='import_kobo'),
    path('synchroniser/', views.synchroniser_kobo, name='synchroniser_kobo'),
    path('config-rapport/', views.config_rapport, name='config_rapport'),
    path('rapport-pdf/', views.generer_rapport_pdf, name='rapport_pdf'),
]