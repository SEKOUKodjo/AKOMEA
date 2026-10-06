"""Données de démonstration réalistes, pour découvrir le tableau de bord.

À utiliser sur une base séparée : python run.py demo --db data/demo.db
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .. import models as m

TEMPLATES = [
    # (dimension, catégorie, description, minutes prévues, ratio réel moyen, probabilité de base)
    ("spirituel", "Lecture biblique", "Lire un chapitre de la Bible", 20, 1.0, 0.85),
    ("spirituel", "Prière", "Temps de prière", 15, 1.1, 0.8),
    ("physique", "Sport", "Faire 30 minutes de sport", 30, 1.0, 0.55),
    ("physique", "Marche", "Marcher 40 minutes", 40, 0.9, 0.65),
    ("etudes", "Python", "Travailler sur mon projet Python", 120, 1.35, 0.7),
    ("etudes", "Machine Learning", "Étudier le Machine Learning", 60, 1.25, 0.6),
    ("etudes", "Article scientifique", "Lire un article scientifique", 45, 1.4, 0.5),
    ("etudes", "Statistiques", "Réviser les statistiques", 60, 1.1, 0.6),
    ("professionnel", "Candidatures", "Envoyer une candidature", 45, 1.5, 0.45),
    ("professionnel", "Portfolio", "Améliorer mon portfolio GitHub", 60, 1.3, 0.5),
    ("relationnel", "Famille", "Appeler maman", 20, 1.2, 0.75),
    ("loisirs", "Musique", "Pratiquer la guitare", 30, 1.0, 0.5),
    ("personnel", "Finances", "Faire le point sur mon budget", 30, 0.9, 0.55),
]
REASONS = ["fatigue", "manque de temps", "imprévu familial", "réunion qui a débordé", "procrastination",
           "pas motivé", "trop d'objectifs dans la journée"]
LEARNINGS = ["J'ai compris le principe des arbres de décision.", "J'ai appris à utiliser groupby avec Pandas.",
             "J'ai compris la différence entre corrélation et causalité.", "J'ai appris la validation croisée.",
             "J'ai compris comment fonctionne la régularisation L2."]
EVENTS = ["Belle discussion avec un mentor sur ma carrière.", "Culte très édifiant ce dimanche.",
          "Projet Python présenté à des amis.", "Match de football avec les amis du quartier.",
          "Réussite de l'examen de statistiques.", "Visite surprise de mon frère."]
VERSES = [("Proverbes 16:3", "Recommande à l'Éternel tes œuvres, et tes projets réussiront."),
          ("Josué 1:9", "Fortifie toi et prends courage."), ("Philippiens 4:13", "Je puis tout par celui qui me fortifie.")]


def seed(session: Session, n_days: int = 150, seed_value: int = 42) -> dict:
    rng = random.Random(seed_value)
    today = date.today()
    start = today - timedelta(days=n_days - 1)

    vision = m.Goal(title="Devenir un data scientist reconnu au service de mon pays", horizon="vision",
                    dimension="professionnel", start_date=start)
    session.add(vision)
    session.flush()
    long_goal = m.Goal(title="Maîtriser le Machine Learning appliqué", horizon="long_terme", dimension="etudes",
                       parent_id=vision.id, start_date=start)
    session.add(long_goal)
    session.flush()
    annual = m.Goal(title="Terminer trois projets de data science publiés sur GitHub", horizon="annuel",
                    dimension="etudes", parent_id=long_goal.id, start_date=start, metric="projets", target_value=3)
    spirit = m.Goal(title="Lire toute la Bible en un an", horizon="annuel", dimension="spirituel", start_date=start)
    health = m.Goal(title="Faire du sport trois fois par semaine", horizon="mensuel", dimension="physique",
                    start_date=start)
    job = m.Goal(title="Envoyer dix candidatures ciblées", horizon="mensuel", dimension="professionnel",
                 parent_id=vision.id, start_date=start, metric="candidatures", target_value=10)
    session.add_all([annual, spirit, health, job])
    session.flush()
    goal_for = {"Python": annual.id, "Machine Learning": annual.id, "Lecture biblique": spirit.id,
                "Sport": health.id, "Candidatures": job.id}

    skills = {name: m.Skill(name=name, dimension="etudes", category="Data science", target_level=5, keywords=kw)
              for name, kw in [("Python", "python"), ("Machine Learning", "machine learning, scikit"),
                               ("Statistiques", "statistiques, regression")]}
    session.add_all(skills.values())
    session.flush()

    n_int = 0
    for k in range(n_days):
        d = start + timedelta(days=k)
        if rng.random() < 0.08:  # quelques jours sans saisie
            continue
        sleep = round(min(9.5, max(4.5, rng.gauss(7, 1.0))), 1)
        energy = int(min(5, max(1, round(2 + (sleep - 5.5) * 0.7 + rng.gauss(0, 0.7)))))
        weekend = d.weekday() >= 5
        day = m.Day(date=d, sleep_hours=sleep, energy=energy, motivation=int(min(5, max(1, round(energy + rng.gauss(0, 0.8))))),
                    stress=int(min(5, max(1, round(rng.gauss(2.8, 1))))), screen_minutes=int(max(30, rng.gauss(210, 60))),
                    steps=int(max(1000, rng.gauss(6500, 2500))), water_liters=round(max(0.5, rng.gauss(1.8, 0.4)), 1))
        session.add(day)
        session.flush()
        n = rng.choice([2, 3, 3, 4, 4, 5, 5, 6, 7])
        chosen = rng.sample(TEMPLATES, n)
        ml = TEMPLATES[5]
        if ml not in chosen and rng.random() < 0.6:
            chosen[-1] = ml
        late = k > n_days - 21
        done_count = 0
        for pos, (dim, cat, desc, est, ratio, base_p) in enumerate(chosen):
            p = base_p + 0.06 * (energy - 3) - 0.09 * max(0, n - 4) + (0.05 if weekend and dim != "professionnel" else 0)
            if cat == "Machine Learning" and late:
                p -= 0.35  # baisse récente, détectable comme tendance
            p = min(0.97, max(0.05, p))
            it = m.Intention(day_id=day.id, dimension=dim, category=cat, description=desc, priority=rng.choice([1, 2, 2, 3]),
                             estimated_minutes=est, position=pos, goal_id=goal_for.get(cat))
            r = rng.random()
            if r < p:
                actual = int(max(5, est * ratio * rng.lognormvariate(0, 0.2)))
                if cat == "Machine Learning" and late:
                    actual = int(actual * 0.45)
                it.status = "realise" if rng.random() > 0.2 else "partiel"
                if it.status == "partiel":
                    actual = int(actual * 0.6)
                it.actual_minutes = actual
                if cat in ("Python", "Machine Learning", "Statistiques") and rng.random() < 0.4:
                    it.result = rng.choice(["Exercices terminés", "Chapitre compris", "Module terminé", "Bug corrigé"])
                done_count += 1
            else:
                it.status = rng.choice(["non_realise", "non_realise", "abandonne", "reporte"])
                it.reason = "fatigue" if energy <= 2 and rng.random() < 0.6 else rng.choice(REASONS)
            it.reviewed_at = m.now()
            session.add(it)
            session.flush()
            n_int += 1
            if it.status in ("realise", "partiel"):
                session.add(m.Activity(day_id=day.id, intention_id=it.id, dimension=dim, category=cat, description=desc,
                                       duration_minutes=it.actual_minutes, result=it.result, planned=True,
                                       skill_id=skills[cat].id if cat in skills else None))
        if rng.random() < 0.25:
            session.add(m.Activity(day_id=day.id, dimension="loisirs", category="Football", description="Match de football",
                                   duration_minutes=rng.choice([60, 90, 120])))
        day.mood = int(min(5, max(1, round(2.2 + done_count / max(n, 1) * 2 + rng.gauss(0, 0.6)))))
        if rng.random() < 0.3:
            session.add(m.Reflection(day_id=day.id, kind="apprentissage", dimension="etudes", content=rng.choice(LEARNINGS)))
        if rng.random() < 0.12:
            ev = rng.choice(EVENTS)
            day.highlight = ev
            session.add(m.Reflection(day_id=day.id, kind="evenement", content=ev))
        if rng.random() < 0.15:
            ref, verse = rng.choice(VERSES)
            session.add(m.Reflection(day_id=day.id, kind="passage", dimension="spirituel", content=verse, reference=ref))
        if rng.random() < 0.2:
            session.add(m.Reflection(day_id=day.id, kind="gratitude", content="Reconnaissant pour la santé et la famille."))
        day.morning_done_at = m.now()
        day.evening_done_at = m.now()

    for i, (name, skill) in enumerate(skills.items()):
        level = 2.0 + 0.3 * i
        for month in range(0, n_days, 30):
            level = min(5, level + rng.uniform(0.05, 0.35))
            session.add(m.SkillProgress(skill_id=skill.id, date=start + timedelta(days=month), self_rating=round(level, 1),
                                        objective_score=round(min(100, level * 18 + rng.gauss(0, 5)), 0),
                                        evidence_type=rng.choice(["exercice", "projet", "test"]),
                                        evidence=f"Évaluation {name} du mois"))
    session.add(m.Decision(date=start + timedelta(days=20), title="Me concentrer sur la data science plutôt que le web",
                           dimension="professionnel", context="Deux pistes de spécialisation possibles.",
                           reasons="Goût pour les statistiques, demande croissante.", alternatives="Développement web",
                           choice="Data science", expected_outcome="Premier projet publié en trois mois", confidence=4,
                           review_date=start + timedelta(days=110), outcome="Deux projets publiés", outcome_rating=4,
                           lessons="Choisir un domaine aligné avec ses forces accélère la progression."))
    session.add(m.Decision(date=today - timedelta(days=10), title="Réduire le nombre d'objectifs quotidiens à quatre",
                           dimension="personnel", reasons="Trop d'abandons les jours chargés", confidence=3,
                           review_date=today + timedelta(days=20)))
    session.add(m.Experiment(title="Quatre objectifs maximum", hypothesis="Je suis plus régulier lorsque je fixe au maximum quatre objectifs importants par jour.",
                             intervention="Limiter les intentions du matin à quatre", metric="completion_rate",
                             start_date=today - timedelta(days=30)))
    mom = m.Person(name="Maman", relation="famille", contact_every_days=3)
    mentor = m.Person(name="Mentor", relation="mentor", contact_every_days=30)
    session.add_all([mom, mentor])
    session.flush()
    for k in range(0, n_days, 4):
        session.add(m.Interaction(person_id=mom.id, date=start + timedelta(days=k), kind="appel"))
    session.add(m.Interaction(person_id=mentor.id, date=today - timedelta(days=45), kind="rencontre",
                              note="Conseils sur le portfolio"))
    session.commit()
    return {"days": n_days, "intentions": n_int}
