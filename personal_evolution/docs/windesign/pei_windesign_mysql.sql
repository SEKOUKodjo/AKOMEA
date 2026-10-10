-- Personal Evolution Intelligence (PEI)
-- Script SQL pour la rétroconception dans WinDesign (SGBD cible : MySQL)
-- Généré le 10/10/2026 à partir de backend/models.py
-- 15 tables, 17 associations. Chaque clé étrangère porte le nom de l'association du MCD.

SET FOREIGN_KEY_CHECKS = 0;

-- Entité JOUR : Une journée vécue et ses indicateurs déclarés (sommeil, énergie, humeur...).
CREATE TABLE days (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant de la journée',
  date DATE NOT NULL COMMENT 'Date calendaire, unique',
  sleep_hours FLOAT NULL COMMENT 'Durée de sommeil en heures (0 à 24)',
  sleep_quality INTEGER NULL COMMENT 'Qualité du sommeil (1 à 5)',
  energy INTEGER NULL COMMENT 'Niveau d''énergie déclaré (1 à 5)',
  motivation INTEGER NULL COMMENT 'Motivation déclarée (1 à 5)',
  mood INTEGER NULL COMMENT 'Humeur déclarée (1 à 5)',
  stress INTEGER NULL COMMENT 'Niveau de stress (1 à 5)',
  fatigue INTEGER NULL COMMENT 'Fatigue (1 à 5)',
  screen_minutes INTEGER NULL COMMENT 'Temps d''écran en minutes',
  sedentary_minutes INTEGER NULL COMMENT 'Temps sédentaire en minutes',
  water_liters FLOAT NULL COMMENT 'Eau bue en litres',
  steps INTEGER NULL COMMENT 'Nombre de pas',
  professional_contribution TEXT NULL COMMENT 'Réponse à « Qu''ai je fait aujourd''hui pour mon évolution professionnelle ? »',
  highlight TEXT NULL COMMENT 'Ce qui a marqué la journée',
  general_comment TEXT NULL COMMENT 'Commentaire libre du soir',
  morning_done_at DATETIME NULL COMMENT 'Horodatage de la validation du matin',
  evening_done_at DATETIME NULL COMMENT 'Horodatage du bilan du soir',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  updated_at DATETIME NOT NULL COMMENT 'Date de dernière modification',
  PRIMARY KEY (id),
  UNIQUE KEY UK_DAYS_DATE (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='JOUR : Une journée vécue et ses indicateurs déclarés (sommeil, énergie, humeur...).';

-- Entité OBJECTIF : Objectif hiérarchique, de la vision jusqu'à l'objectif hebdomadaire.
CREATE TABLE goals (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant de l''objectif',
  parent_id INTEGER NULL COMMENT 'Objectif parent (décomposition)',
  title VARCHAR(300) NOT NULL COMMENT 'Intitulé',
  description TEXT NULL COMMENT 'Description détaillée',
  dimension VARCHAR(40) NULL COMMENT 'Dimension de vie',
  horizon VARCHAR(30) NOT NULL COMMENT 'vision, long_terme, annuel, mensuel ou hebdomadaire',
  status VARCHAR(30) NOT NULL COMMENT 'actif, atteint, en_pause, abandonne',
  start_date DATE NULL COMMENT 'Date de début',
  target_date DATE NULL COMMENT 'Échéance visée',
  completed_at DATE NULL COMMENT 'Date d''atteinte',
  metric VARCHAR(200) NULL COMMENT 'Indicateur de réussite (ex. nombre de projets)',
  target_value FLOAT NULL COMMENT 'Valeur cible de l''indicateur',
  abandon_reason TEXT NULL COMMENT 'Raison d''un abandon',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OBJECTIF : Objectif hiérarchique, de la vision jusqu''à l''objectif hebdomadaire.';

-- Entité INTENTION : Ce que je veux faire un jour donné (niveau Intention).
CREATE TABLE intentions (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant de l''intention',
  day_id INTEGER NOT NULL COMMENT 'Journée concernée',
  goal_id INTEGER NULL COMMENT 'Objectif auquel elle contribue',
  dimension VARCHAR(40) NULL COMMENT 'Dimension de vie',
  category VARCHAR(120) NULL COMMENT 'Type d''activité (Python, Sport...)',
  description TEXT NOT NULL COMMENT 'Intention formulée',
  priority INTEGER NOT NULL COMMENT '1 haute, 2 normale, 3 basse',
  estimated_minutes INTEGER NULL COMMENT 'Durée prévue en minutes',
  status VARCHAR(20) NOT NULL COMMENT 'prevu, realise, partiel, non_realise, abandonne, reporte',
  actual_minutes INTEGER NULL COMMENT 'Durée réellement consacrée',
  result TEXT NULL COMMENT 'Résultat obtenu',
  reason TEXT NULL COMMENT 'Raison d''un abandon ou d''un écart',
  position INTEGER NOT NULL COMMENT 'Ordre d''affichage dans la journée',
  source_id INTEGER NULL COMMENT 'Source d''origine (saisie du matin)',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  reviewed_at DATETIME NULL COMMENT 'Date du bilan de cette intention',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='INTENTION : Ce que je veux faire un jour donné (niveau Intention).';

-- Entité ACTIVITE : Ce que j'ai réellement fait et ce que cela a produit (niveaux Action et Résultat).
CREATE TABLE activities (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant de l''activité',
  day_id INTEGER NOT NULL COMMENT 'Journée où elle a eu lieu',
  intention_id INTEGER NULL COMMENT 'Intention qu''elle concrétise (vide si non prévue)',
  skill_id INTEGER NULL COMMENT 'Compétence exercée',
  dimension VARCHAR(40) NULL COMMENT 'Dimension de vie',
  category VARCHAR(120) NULL COMMENT 'Type d''activité',
  description TEXT NOT NULL COMMENT 'Ce qui a été fait',
  start_time VARCHAR(5) NULL COMMENT 'Heure de début (HH:MM)',
  end_time VARCHAR(5) NULL COMMENT 'Heure de fin (HH:MM)',
  duration_minutes INTEGER NULL COMMENT 'Durée en minutes',
  result TEXT NULL COMMENT 'Ce que l''activité a produit',
  planned BOOL NOT NULL COMMENT 'Vrai si l''activité était prévue',
  source_id INTEGER NULL COMMENT 'Source d''origine',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ACTIVITE : Ce que j''ai réellement fait et ce que cela a produit (niveaux Action et Résultat).';

-- Entité REFLEXION : Réflexion typée : apprentissage, gratitude, difficulté, passage biblique...
CREATE TABLE reflections (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  day_id INTEGER NOT NULL COMMENT 'Journée concernée',
  dimension VARCHAR(40) NULL COMMENT 'Dimension de vie',
  kind VARCHAR(30) NOT NULL COMMENT 'reflexion, apprentissage, difficulte, gratitude, idee, evenement, passage, engagement...',
  content TEXT NOT NULL COMMENT 'Texte de la réflexion',
  reference VARCHAR(200) NULL COMMENT 'Référence (passage biblique, livre, lien)',
  tags VARCHAR(300) NULL COMMENT 'Mots clés libres',
  source_type VARCHAR(20) NOT NULL COMMENT 'texte ou audio',
  source_id INTEGER NULL COMMENT 'Source d''origine',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='REFLEXION : Réflexion typée : apprentissage, gratitude, difficulté, passage biblique...';

-- Entité MEDIA : Métadonnées d'un fichier audio, vidéo, image ou document conservé dans storage/.
CREATE TABLE media (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant du média',
  day_id INTEGER NULL COMMENT 'Journée de rattachement',
  type VARCHAR(20) NOT NULL COMMENT 'audio, video, image, document',
  moment VARCHAR(20) NULL COMMENT 'matin, journee, soir',
  dimension VARCHAR(40) NULL COMMENT 'Dimension de vie',
  file_path VARCHAR(500) NOT NULL COMMENT 'Chemin du fichier, relatif à storage/',
  original_name VARCHAR(300) NULL COMMENT 'Nom d''origine du fichier',
  mime_type VARCHAR(100) NULL COMMENT 'Type MIME',
  size_bytes INTEGER NULL COMMENT 'Taille en octets',
  sha256 VARCHAR(64) NULL COMMENT 'Empreinte d''intégrité du fichier',
  caption TEXT NULL COMMENT 'Légende',
  transcription TEXT NULL COMMENT 'Texte transcrit (audio, vidéo)',
  transcription_status VARCHAR(20) NULL COMMENT 'en_attente, en_cours, termine, indisponible, erreur',
  transcription_engine VARCHAR(80) NULL COMMENT 'Moteur utilisé (ex. faster-whisper:small)',
  transcription_error TEXT NULL COMMENT 'Message d''erreur éventuel',
  created_at DATETIME NOT NULL COMMENT 'Date d''enregistrement',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MEDIA : Métadonnées d''un fichier audio, vidéo, image ou document conservé dans storage/.';

-- Entité SOURCE : Donnée brute d'origine (texte saisi, audio transcrit, formulaire), jamais modifiée.
CREATE TABLE sources (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant de la source',
  day_id INTEGER NULL COMMENT 'Journée concernée',
  kind VARCHAR(30) NOT NULL COMMENT 'texte, audio, video, formulaire',
  moment VARCHAR(20) NULL COMMENT 'matin, journee, soir',
  raw_text TEXT NULL COMMENT 'Texte brut d''origine ou transcription',
  media_id INTEGER NULL COMMENT 'Média d''origine (si audio ou vidéo)',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='SOURCE : Donnée brute d''origine (texte saisi, audio transcrit, formulaire), jamais modifiée.';

-- Entité EXTRACTION : Proposition de l'IA sur une source, puis sa version validée ou corrigée.
CREATE TABLE extractions (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  source_id INTEGER NOT NULL COMMENT 'Source analysée',
  engine VARCHAR(80) NOT NULL COMMENT 'Moteur d''extraction',
  engine_version VARCHAR(20) NOT NULL COMMENT 'Version du moteur',
  proposed TEXT NOT NULL COMMENT 'Proposition de l''IA (JSON)',
  validated TEXT NULL COMMENT 'Version validée par l''utilisateur (JSON)',
  status VARCHAR(20) NOT NULL COMMENT 'propose, valide, corrige, rejete',
  created_at DATETIME NOT NULL COMMENT 'Date de la proposition',
  validated_at DATETIME NULL COMMENT 'Date de validation',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='EXTRACTION : Proposition de l''IA sur une source, puis sa version validée ou corrigée.';

-- Entité PREDICTION : Estimation émise par un modèle, conservée pour être comparée à la réalité.
CREATE TABLE predictions (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  target VARCHAR(60) NOT NULL COMMENT 'Ce qui est prédit : completion, duree...',
  subject_type VARCHAR(40) NULL COMMENT 'Type d''objet concerné (ex. intention)',
  subject_id INTEGER NULL COMMENT 'Identifiant de l''objet concerné',
  value FLOAT NOT NULL COMMENT 'Valeur prédite (probabilité, minutes...)',
  lower FLOAT NULL COMMENT 'Borne basse de l''intervalle',
  upper FLOAT NULL COMMENT 'Borne haute de l''intervalle',
  model VARCHAR(80) NOT NULL COMMENT 'Modèle utilisé',
  n_training INTEGER NULL COMMENT 'Taille de l''historique d''apprentissage',
  features TEXT NULL COMMENT 'Variables utilisées (JSON)',
  actual FLOAT NULL COMMENT 'Valeur réellement observée ensuite',
  created_at DATETIME NOT NULL COMMENT 'Date de la prédiction',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='PREDICTION : Estimation émise par un modèle, conservée pour être comparée à la réalité.';

-- Entité COMPETENCE : Compétence suivie dans le temps.
CREATE TABLE skills (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  name VARCHAR(120) NOT NULL COMMENT 'Nom de la compétence, unique',
  category VARCHAR(120) NULL COMMENT 'Famille (ex. Data science)',
  dimension VARCHAR(40) NULL COMMENT 'Dimension de vie',
  description TEXT NULL COMMENT 'Description',
  target_level INTEGER NULL COMMENT 'Niveau visé (1 à 5)',
  keywords VARCHAR(300) NULL COMMENT 'Mots clés reliant automatiquement les activités',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id),
  UNIQUE KEY UK_SKILLS_NAME (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='COMPETENCE : Compétence suivie dans le temps.';

-- Entité EVALUATION : Point d'évaluation d'une compétence : ressenti et preuve objective.
CREATE TABLE skill_progress (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  skill_id INTEGER NOT NULL COMMENT 'Compétence évaluée',
  date DATE NOT NULL COMMENT 'Date de l''évaluation',
  self_rating FLOAT NULL COMMENT 'Auto évaluation (0 à 5)',
  objective_score FLOAT NULL COMMENT 'Score objectif (0 à 100)',
  evidence_type VARCHAR(40) NULL COMMENT 'exercice, projet, test, formation, production',
  evidence TEXT NULL COMMENT 'Description de la preuve',
  comment TEXT NULL COMMENT 'Commentaire',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='EVALUATION : Point d''évaluation d''une compétence : ressenti et preuve objective.';

-- Entité DECISION : Décision importante : contexte, raisons, choix, puis résultat observé.
CREATE TABLE decisions (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  date DATE NOT NULL COMMENT 'Date de la décision',
  title VARCHAR(300) NOT NULL COMMENT 'Décision',
  dimension VARCHAR(40) NULL COMMENT 'Dimension de vie',
  context TEXT NULL COMMENT 'Contexte',
  reasons TEXT NULL COMMENT 'Raisons',
  alternatives TEXT NULL COMMENT 'Alternatives envisagées',
  choice TEXT NULL COMMENT 'Choix effectué',
  expected_outcome TEXT NULL COMMENT 'Résultat attendu',
  confidence INTEGER NULL COMMENT 'Confiance (1 à 5)',
  review_date DATE NULL COMMENT 'Date prévue pour juger le résultat',
  outcome TEXT NULL COMMENT 'Résultat observé',
  outcome_rating INTEGER NULL COMMENT 'Appréciation du résultat (1 à 5)',
  lessons TEXT NULL COMMENT 'Leçon tirée',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DECISION : Décision importante : contexte, raisons, choix, puis résultat observé.';

-- Entité EXPERIENCE : Expérience personnelle : hypothèse testée sur une période.
CREATE TABLE experiments (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  title VARCHAR(300) NOT NULL COMMENT 'Titre',
  hypothesis TEXT NOT NULL COMMENT 'Hypothèse testée',
  intervention TEXT NULL COMMENT 'Ce qui est changé',
  metric VARCHAR(60) NOT NULL COMMENT 'Indicateur observé (colonne de la série quotidienne)',
  start_date DATE NOT NULL COMMENT 'Début',
  end_date DATE NULL COMMENT 'Fin (vide si en cours)',
  status VARCHAR(20) NOT NULL COMMENT 'en_cours, termine',
  conclusion TEXT NULL COMMENT 'Conclusion',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='EXPERIENCE : Expérience personnelle : hypothèse testée sur une période.';

-- Entité PERSONNE : Personne de l'entourage (famille, ami, mentor...).
CREATE TABLE people (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  name VARCHAR(200) NOT NULL COMMENT 'Nom',
  relation VARCHAR(60) NULL COMMENT 'famille, ami, collègue, mentor, communauté',
  notes TEXT NULL COMMENT 'Notes',
  contact_every_days INTEGER NULL COMMENT 'Rythme de contact souhaité en jours',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='PERSONNE : Personne de l''entourage (famille, ami, mentor...).';

-- Entité ECHANGE : Échange avec une personne : appel, visite, rencontre, message.
CREATE TABLE interactions (
  id INTEGER NOT NULL AUTO_INCREMENT COMMENT 'Identifiant',
  person_id INTEGER NOT NULL COMMENT 'Personne concernée',
  date DATE NOT NULL COMMENT 'Date de l''échange',
  kind VARCHAR(30) NOT NULL COMMENT 'appel, visite, message, rencontre, conversation',
  note TEXT NULL COMMENT 'Note sur l''échange',
  created_at DATETIME NOT NULL COMMENT 'Date de création',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ECHANGE : Échange avec une personne : appel, visite, rencontre, message.';

-- Associations du MCD (une clé étrangère par association)
-- DECOMPOSER : OBJECTIF (0,n) / OBJECTIF (0,1). Un objectif peut se décomposer en plusieurs sous objectifs ; un objectif a au plus un objectif parent.
ALTER TABLE goals ADD CONSTRAINT FK_DECOMPOSER FOREIGN KEY (parent_id) REFERENCES goals (id) ON DELETE SET NULL;

-- CONTRIBUER : OBJECTIF (0,n) / INTENTION (0,1). Un objectif reçoit la contribution de zéro ou plusieurs intentions ; une intention contribue à au plus un objectif.
ALTER TABLE intentions ADD CONSTRAINT FK_CONTRIBUER FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE SET NULL;

-- PREVOIR : JOUR (0,n) / INTENTION (1,1). Une journée comporte zéro ou plusieurs intentions ; une intention est prévue pour exactement une journée.
ALTER TABLE intentions ADD CONSTRAINT FK_PREVOIR FOREIGN KEY (day_id) REFERENCES days (id) ON DELETE CASCADE;

-- CONCERNER : INTENTION (0,n) / PREDICTION (0,1). Une intention peut faire l'objet de plusieurs prédictions ; une prédiction concerne au plus une intention.
ALTER TABLE predictions ADD CONSTRAINT FK_CONCERNER FOREIGN KEY (subject_id) REFERENCES intentions (id) ON DELETE SET NULL;
-- Remarque : dans l'application, ce lien est polymorphe (subject_type, subject_id) ;
-- il est déclaré ici vers INTENTION pour que WinDesign affiche l'association du MCD.

-- EXPRIMER : SOURCE (0,n) / INTENTION (0,1). Une source peut exprimer plusieurs intentions ; une intention provient d'au plus une source.
ALTER TABLE intentions ADD CONSTRAINT FK_EXPRIMER FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE SET NULL;

-- REALISER : JOUR (0,n) / ACTIVITE (1,1). Une journée comporte zéro ou plusieurs activités ; une activité a lieu exactement un jour.
ALTER TABLE activities ADD CONSTRAINT FK_REALISER FOREIGN KEY (day_id) REFERENCES days (id) ON DELETE CASCADE;

-- CONCRETISER : INTENTION (0,n) / ACTIVITE (0,1). Une intention peut être concrétisée par plusieurs activités ; une activité concrétise au plus une intention.
ALTER TABLE activities ADD CONSTRAINT FK_CONCRETISER FOREIGN KEY (intention_id) REFERENCES intentions (id) ON DELETE SET NULL;

-- RELATER : SOURCE (0,n) / ACTIVITE (0,1). Une source peut relater plusieurs activités ; une activité provient d'au plus une source.
ALTER TABLE activities ADD CONSTRAINT FK_RELATER FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE SET NULL;

-- SAISIR : JOUR (0,n) / SOURCE (0,1). Une journée regroupe zéro ou plusieurs sources ; une source est rattachée à au plus une journée.
ALTER TABLE sources ADD CONSTRAINT FK_SAISIR FOREIGN KEY (day_id) REFERENCES days (id) ON DELETE SET NULL;

-- NOTER : JOUR (0,n) / REFLEXION (1,1). Une journée comporte zéro ou plusieurs réflexions ; une réflexion appartient exactement à une journée.
ALTER TABLE reflections ADD CONSTRAINT FK_NOTER FOREIGN KEY (day_id) REFERENCES days (id) ON DELETE CASCADE;

-- CONSIGNER : SOURCE (0,n) / REFLEXION (0,1). Une source peut consigner plusieurs réflexions ; une réflexion provient d'au plus une source.
ALTER TABLE reflections ADD CONSTRAINT FK_CONSIGNER FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE SET NULL;

-- ATTACHER : JOUR (0,n) / MEDIA (0,1). Une journée peut avoir plusieurs médias ; un média est rattaché à au plus une journée.
ALTER TABLE media ADD CONSTRAINT FK_ATTACHER FOREIGN KEY (day_id) REFERENCES days (id) ON DELETE SET NULL;

-- TRANSCRIRE : MEDIA (0,n) / SOURCE (0,1). Un média peut donner lieu à des sources (sa transcription) ; une source provient d'au plus un média.
ALTER TABLE sources ADD CONSTRAINT FK_TRANSCRIRE FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE SET NULL;

-- ANALYSER : SOURCE (0,n) / EXTRACTION (1,1). Une source peut être analysée plusieurs fois ; une extraction porte sur exactement une source.
ALTER TABLE extractions ADD CONSTRAINT FK_ANALYSER FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE;

-- EXERCER : COMPETENCE (0,n) / ACTIVITE (0,1). Une compétence est exercée par zéro ou plusieurs activités ; une activité exerce au plus une compétence.
ALTER TABLE activities ADD CONSTRAINT FK_EXERCER FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE SET NULL;

-- EVALUER : COMPETENCE (0,n) / EVALUATION (1,1). Une compétence reçoit zéro ou plusieurs évaluations ; une évaluation concerne exactement une compétence.
ALTER TABLE skill_progress ADD CONSTRAINT FK_EVALUER FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE;

-- ECHANGER : PERSONNE (0,n) / ECHANGE (1,1). Une personne a zéro ou plusieurs échanges ; un échange concerne exactement une personne.
ALTER TABLE interactions ADD CONSTRAINT FK_ECHANGER FOREIGN KEY (person_id) REFERENCES people (id) ON DELETE CASCADE;

SET FOREIGN_KEY_CHECKS = 1;
