"""Lexique français : mots clés vers dimensions et catégories d'activités.

Chaque entrée : (motif regex, dimension, catégorie, poids). Le poids départage
les ambiguïtés : "lire un chapitre de la Bible" relève du spirituel car "bible"
pèse plus que "lire". Le lexique est volontairement éditable.
"""
from __future__ import annotations

LEXICON: list[tuple[str, str, str, int]] = [
    # Spirituel
    (r"bible|biblique|evangile|psaume|proverbe|verset", "spirituel", "Lecture biblique", 5),
    (r"pri(e|er|ere|eres)\b|oraison|intercession", "spirituel", "Prière", 5),
    (r"medit(er|ation)", "spirituel", "Méditation", 4),
    (r"jeun(e|er)\b", "spirituel", "Jeûne", 5),
    (r"louange|adoration|chorale|cantique", "spirituel", "Louange", 5),
    (r"culte|eglise|messe|communaute|cellule de priere", "spirituel", "Vie communautaire", 5),
    (r"devotion|culte personnel|moment avec dieu|dieu|seigneur|jesus", "spirituel", "Dévotion", 4),
    # Physique
    (r"football|foot\b|match", "loisirs", "Football", 5),
    (r"sport|entrainement|seance", "physique", "Sport", 3),
    (r"courir|course\b|footing|jogging|running", "physique", "Course", 5),
    (r"marche\b|marcher|promenade|randonnee", "physique", "Marche", 4),
    (r"musculation|muscu|pompes|abdos|gainage|gym|salle", "physique", "Musculation", 5),
    (r"yoga|etirement|stretching", "physique", "Étirements", 5),
    (r"natation|nager|piscine", "physique", "Natation", 5),
    (r"velo|cyclisme", "physique", "Vélo", 5),
    (r"dormir|sieste|sommeil|coucher tot", "physique", "Sommeil", 4),
    (r"cuisiner|repas sain|manger sain|alimentation|boire de l.eau|hydrat", "physique", "Alimentation", 4),
    # Études
    (r"machine learning|apprentissage automatique|\bml\b|scikit|sklearn", "etudes", "Machine Learning", 6),
    (r"deep learning|reseau(x)? de neurones|pytorch|tensorflow", "etudes", "Deep Learning", 6),
    (r"pandas", "etudes", "Pandas", 6),
    (r"numpy|scipy", "etudes", "Python scientifique", 6),
    (r"python", "etudes", "Python", 5),
    (r"\bsql\b|base de donnees", "etudes", "SQL", 5),
    (r"statisti|econometr|probabilit|regression|serie temporelle", "etudes", "Statistiques", 5),
    (r"math(s|ematique)?|algebre|analyse reelle", "etudes", "Mathématiques", 5),
    (r"article( scientifique)?|papier de recherche|publication", "etudes", "Article scientifique", 5),
    (r"livre|roman|chapitre|lecture|lire", "etudes", "Lecture", 2),
    (r"cours|lecon|module|mooc|formation en ligne|tutoriel", "etudes", "Cours", 3),
    (r"exercice|td\b|tp\b|probleme", "etudes", "Exercices", 3),
    (r"revis(er|ion)|examen|devoir|memoire|these", "etudes", "Révisions", 4),
    (r"etudi(er|e)|apprendre|recherche", "etudes", "Études", 2),
    (r"anglais|english|langue", "etudes", "Langues", 5),
    # Professionnel
    (r"candidature|postuler|lettre de motivation|\bcv\b", "professionnel", "Candidatures", 6),
    (r"entretien d.embauche|entretien", "professionnel", "Entretiens", 5),
    (r"reunion|meeting|point d.equipe", "professionnel", "Réunions", 5),
    (r"portfolio|github|linkedin", "professionnel", "Portfolio", 5),
    (r"reseautage|networking|contact pro", "professionnel", "Réseautage", 5),
    (r"certification|certificat", "professionnel", "Certifications", 5),
    (r"mission|client|stage|rapport|livrable|boulot|bureau", "professionnel", "Travail", 3),
    (r"projet", "professionnel", "Projet", 2),
    (r"travail(ler)?", "professionnel", "Travail", 1),
    # Relationnel
    (r"appel(er)?|telephoner|coup de fil", "relationnel", "Appels", 4),
    (r"maman|papa|mere|pere|parents|frere|soeur|famille|cousin|tante|oncle", "relationnel", "Famille", 5),
    (r"ami(e|s)?\b|copain|copine", "relationnel", "Amis", 4),
    (r"mentor|encadreur|professeur", "relationnel", "Mentors", 4),
    (r"visite|rendre visite|rencontr(e|er)", "relationnel", "Rencontres", 3),
    (r"collegue", "relationnel", "Collègues", 4),
    # Loisirs et créativité
    (r"musique|guitare|piano|chanter|chant\b|composer", "loisirs", "Musique", 5),
    (r"photo(graphie)?", "loisirs", "Photographie", 5),
    (r"ecrire|ecriture|blog|poeme", "loisirs", "Écriture", 4),
    (r"film|serie|cinema", "loisirs", "Films", 4),
    (r"sortie|balade|voyage|excursion", "loisirs", "Sorties", 4),
    (r"dessin|peinture|creati", "loisirs", "Création", 4),
    (r"jeux?\b|jouer", "loisirs", "Jeux", 2),
    # Personnel
    (r"journal|introspection", "personnel", "Journal", 4),
    (r"ranger|menage|lessive|linge", "personnel", "Organisation", 4),
    (r"budget|finances|depenses|epargne", "personnel", "Finances", 5),
    (r"courses|marche alimentaire", "personnel", "Courses", 3),
    (r"planifier|planning|organiser ma", "personnel", "Planification", 4),
]

# Vocabulaire émotionnel pour repérer l'état exprimé dans un bilan.
EMOTIONS: dict[str, tuple[str, int]] = {
    "fatigue": ("fatigue", -1), "epuise": ("fatigue", -1), "creve": ("fatigue", -1),
    "stresse": ("stress", -1), "angoisse": ("stress", -1), "anxieux": ("stress", -1), "inquiet": ("stress", -1),
    "triste": ("tristesse", -1), "decourage": ("decouragement", -1), "demotive": ("decouragement", -1),
    "frustre": ("frustration", -1), "enerve": ("colere", -1), "malade": ("sante", -1),
    "content": ("joie", 1), "heureux": ("joie", 1), "joyeux": ("joie", 1), "satisfait": ("satisfaction", 1),
    "fier": ("fierte", 1), "motive": ("motivation", 1), "serein": ("serenite", 1), "paisible": ("serenite", 1),
    "reconnaissant": ("gratitude", 1), "concentre": ("concentration", 1), "en forme": ("energie", 1),
    "productif": ("satisfaction", 1),
}
