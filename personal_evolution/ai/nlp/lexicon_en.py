"""Lexique anglais : mots clés vers dimensions et catégories.

Les catégories sont nommées par leur libellé français, qui sert d'identifiant
commun aux deux langues : une activité dictée en anglais ou en français tombe
dans la même catégorie. CATEGORY_EN donne le libellé anglais affiché.
"""
from __future__ import annotations

LEXICON_EN: list[tuple[str, str, str, int]] = [
    # Spirituel
    (r"bible|biblical|scripture|gospel|psalm|proverb|verse", "spirituel", "Lecture biblique", 5),
    (r"pray(?:s|ed|ing|er|ers)?\b", "spirituel", "Prière", 5),
    (r"meditat", "spirituel", "Méditation", 4),
    (r"fast(?:ing|ed)?\b", "spirituel", "Jeûne", 5),
    (r"worship|praise|hymn|choir", "spirituel", "Louange", 5),
    (r"church|\bmass\b|fellowship|prayer group|cell group", "spirituel", "Vie communautaire", 5),
    (r"devotion|quiet time|\bgod\b|\blord\b|jesus", "spirituel", "Dévotion", 4),
    # Physique
    (r"football|soccer|\bmatch\b", "loisirs", "Football", 5),
    (r"sport|workout|work out|training session|exercis(?:e|ed|ing)\b", "physique", "Sport", 3),
    (r"\brun\b|running|\bran\b|jog(?:ging|ged)?\b", "physique", "Course", 5),
    (r"walk(?:ed|ing|s)?\b|stroll|hik(?:e|ing)", "physique", "Marche", 4),
    (r"weights|strength training|push.?ups|sit.?ups|\babs\b|plank|\bgym\b", "physique", "Musculation", 5),
    (r"yoga|stretch", "physique", "Étirements", 5),
    (r"swim", "physique", "Natation", 5),
    (r"\bbike\b|cycling|biking", "physique", "Vélo", 5),
    (r"sleep|\bnap\b|go to bed early", "physique", "Sommeil", 4),
    (r"\bcook|healthy meal|eat healthy|\bdiet\b|drink water|hydrat", "physique", "Alimentation", 4),
    # Études
    (r"machine learning|\bml\b|scikit|sklearn", "etudes", "Machine Learning", 6),
    (r"deep learning|neural network|pytorch|tensorflow", "etudes", "Deep Learning", 6),
    (r"pandas", "etudes", "Pandas", 6),
    (r"numpy|scipy", "etudes", "Python scientifique", 6),
    (r"python", "etudes", "Python", 5),
    (r"\bsql\b|database", "etudes", "SQL", 5),
    (r"statistic|econometric|probabilit|regression|time series", "etudes", "Statistiques", 5),
    (r"\bmaths?\b|mathematics|algebra|calculus", "etudes", "Mathématiques", 5),
    (r"(?:scientific |research )?(?:article|paper)s?\b|publication", "etudes", "Article scientifique", 5),
    (r"\bbook|novel|chapter|reading|\bread\b", "etudes", "Lecture", 2),
    (r"course|lesson|\bclass\b|module|mooc|tutorial|lecture", "etudes", "Cours", 3),
    (r"exercises|homework|assignment|problem set", "etudes", "Exercices", 3),
    (r"revis(?:e|ion)|review for|\bexam|test prep|thesis|dissertation", "etudes", "Révisions", 4),
    (r"stud(?:y|ied|ying)|\blearn|research", "etudes", "Études", 2),
    (r"english|french|language|vocabulary", "etudes", "Langues", 5),
    # Professionnel
    (r"job application|apply for|applied for|cover letter|\bcv\b|resume", "professionnel", "Candidatures", 6),
    (r"interview", "professionnel", "Entretiens", 5),
    (r"meeting|stand.?up|team call", "professionnel", "Réunions", 5),
    (r"portfolio|github|linkedin", "professionnel", "Portfolio", 5),
    (r"networking|network event", "professionnel", "Réseautage", 5),
    (r"certification|certificate", "professionnel", "Certifications", 5),
    (r"client|internship|report|deliverable|\boffice\b|mission", "professionnel", "Travail", 3),
    (r"project", "professionnel", "Projet", 2),
    (r"\bwork(?:ed|ing|s)?\b|\bjob\b", "professionnel", "Travail", 1),
    # Relationnel
    (r"\bcall(?:ed|ing)?\b|\bphone", "relationnel", "Appels", 4),
    (r"\bmom\b|\bmum\b|mother|\bdad\b|father|parents|brother|sister|family|cousin|aunt|uncle", "relationnel", "Famille", 5),
    (r"friend", "relationnel", "Amis", 4),
    (r"mentor|supervisor|professor|teacher", "relationnel", "Mentors", 4),
    (r"visit|meet up|\bmet\b", "relationnel", "Rencontres", 3),
    (r"colleague|coworker|co.worker", "relationnel", "Collègues", 4),
    # Loisirs et créativité
    (r"music|guitar|piano|\bsing|compose", "loisirs", "Musique", 5),
    (r"photo", "loisirs", "Photographie", 5),
    (r"\bwrit(?:e|ing)\b|\bblog|poem", "loisirs", "Écriture", 4),
    (r"movie|\bfilm|series|cinema", "loisirs", "Films", 4),
    (r"outing|\btrip\b|travel|excursion", "loisirs", "Sorties", 4),
    (r"\bdraw|paint|creative", "loisirs", "Création", 4),
    (r"\bgames?\b|\bplay(?:ed|ing)?\b", "loisirs", "Jeux", 2),
    # Personnel
    (r"journal|introspection", "personnel", "Journal", 4),
    (r"\btidy|cleaning|housework|laundry", "personnel", "Organisation", 4),
    (r"budget|finances|expenses|savings", "personnel", "Finances", 5),
    (r"groceries|grocery|shopping", "personnel", "Courses", 3),
    (r"plan my|planning", "personnel", "Planification", 4),
]

EMOTIONS_EN: dict[str, tuple[str, int]] = {
    "tired": ("fatigue", -1), "exhausted": ("fatigue", -1), "worn out": ("fatigue", -1),
    "stressed": ("stress", -1), "anxious": ("stress", -1), "worried": ("stress", -1),
    "sad": ("tristesse", -1), "discouraged": ("decouragement", -1), "unmotivated": ("decouragement", -1),
    "frustrated": ("frustration", -1), "angry": ("colere", -1), "annoyed": ("colere", -1), "sick": ("sante", -1),
    "happy": ("joie", 1), "glad": ("joie", 1), "joyful": ("joie", 1), "satisfied": ("satisfaction", 1),
    "proud": ("fierte", 1), "motivated": ("motivation", 1), "calm": ("serenite", 1), "peaceful": ("serenite", 1),
    "grateful": ("gratitude", 1), "focused": ("concentration", 1), "energetic": ("energie", 1),
    "productive": ("satisfaction", 1),
}

# Libellé anglais de chaque catégorie (identifiant = libellé français).
CATEGORY_EN: dict[str, str] = {
    "Lecture biblique": "Bible reading", "Prière": "Prayer", "Méditation": "Meditation", "Jeûne": "Fasting",
    "Louange": "Worship", "Vie communautaire": "Church community", "Dévotion": "Devotion", "Football": "Football",
    "Sport": "Sport", "Course": "Running", "Marche": "Walking", "Musculation": "Strength training",
    "Étirements": "Stretching", "Natation": "Swimming", "Vélo": "Cycling", "Sommeil": "Sleep",
    "Alimentation": "Nutrition", "Machine Learning": "Machine Learning", "Deep Learning": "Deep Learning",
    "Pandas": "Pandas", "Python scientifique": "Scientific Python", "Python": "Python", "SQL": "SQL",
    "Statistiques": "Statistics", "Mathématiques": "Mathematics", "Article scientifique": "Scientific article",
    "Lecture": "Reading", "Cours": "Course", "Exercices": "Exercises", "Révisions": "Revision", "Études": "Study",
    "Langues": "Languages", "Candidatures": "Job applications", "Entretiens": "Interviews", "Réunions": "Meetings",
    "Portfolio": "Portfolio", "Réseautage": "Networking", "Certifications": "Certifications", "Travail": "Work",
    "Projet": "Project", "Appels": "Calls", "Famille": "Family", "Amis": "Friends", "Mentors": "Mentors",
    "Rencontres": "Meetups", "Collègues": "Colleagues", "Musique": "Music", "Photographie": "Photography",
    "Écriture": "Writing", "Films": "Movies", "Sorties": "Outings", "Création": "Creative work", "Jeux": "Games",
    "Journal": "Journaling", "Organisation": "Housekeeping", "Finances": "Finances", "Courses": "Groceries",
    "Planification": "Planning",
}

DIMENSION_LABELS_EN = {
    "spirituel": "Spiritual", "physique": "Physical", "etudes": "Studies", "professionnel": "Professional",
    "personnel": "Personal", "relationnel": "Relationships", "loisirs": "Leisure and creativity",
}
