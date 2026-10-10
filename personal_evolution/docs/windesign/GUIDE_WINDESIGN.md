# Obtenir le MCD de PEI dans WinDesign

WinDesign sait reconstruire un modèle Merise à partir d'une base existante : c'est la
**rétroconception** (reverse engineering). Le fichier `pei_windesign_mysql.sql`, à côté de ce
guide, a été préparé pour cela.

## Ce que contient le script

* Les 15 tables de PEI, au format MySQL.
* Une clé étrangère par association du MCD. Chaque clé porte le nom de l'association
  (`FK_PREVOIR`, `FK_DECOMPOSER`, `FK_CONCRETISER`...), et WinDesign l'utilise comme nom
  de l'association.
* Un commentaire en français sur chaque table et chaque colonne : WinDesign le reprend
  comme description de l'entité ou de la propriété.
* La nature de chaque lien, que WinDesign traduit en cardinalités :
  * une clé obligatoire (`NOT NULL`) donne une cardinalité 1,1 ;
  * une clé facultative (`NULL`) donne une cardinalité 0,1 ;
  * l'autre côté de chaque lien est en 0,n.

## Méthode 1 : rétroconception directe du script

Les noms exacts des menus varient selon la version de WinDesign.

1. Ouvrir WinDesign, module **Database**, puis créer un nouveau modèle.
2. Choisir **MySQL** comme SGBD cible.
3. Lancer la **rétroconception** (selon la version : menu Base de données, Outils ou Fichier,
   puis Rétroconception ou Reverse).
4. Choisir comme source un **script SQL**, puis sélectionner `pei_windesign_mysql.sql`.
5. WinDesign crée le modèle logique (tables et liens).
6. Demander la génération du **MCD** à partir de ce modèle logique (commande du type
   Générer MCD, ou Remonter au conceptuel).

## Méthode 2 : passer par une base MySQL (si la version n'importe pas de script)

1. Installer MySQL ou MariaDB, par exemple avec XAMPP ou WampServer.
2. Créer une base vide, puis exécuter le script :
   ```sql
   CREATE DATABASE pei CHARACTER SET utf8mb4;
   USE pei;
   SOURCE chemin/vers/pei_windesign_mysql.sql;
   ```
3. Installer le pilote **ODBC MySQL** (MySQL Connector/ODBC), puis créer une source de données
   ODBC qui pointe vers la base `pei`.
4. Dans WinDesign, lancer la rétroconception en choisissant cette source ODBC.
5. Générer le MCD comme à l'étape 6 de la méthode 1.

## Après l'import : mise en forme

WinDesign reprend les noms techniques des tables (en anglais). Pour retrouver le MCD du
document `docs/MCD.pdf`, renommer les entités ainsi :

| Table | Entité du MCD |
|---|---|
| days | JOUR |
| goals | OBJECTIF |
| intentions | INTENTION |
| activities | ACTIVITE |
| reflections | REFLEXION |
| media | MEDIA |
| sources | SOURCE |
| extractions | EXTRACTION |
| predictions | PREDICTION |
| skills | COMPETENCE |
| skill_progress | EVALUATION |
| decisions | DECISION |
| experiments | EXPERIENCE |
| people | PERSONNE |
| interactions | ECHANGE |

Vérifier ensuite les 17 associations et leurs cardinalités :

| Association | Entité A | Card. A | Entité B | Card. B |
|---|---|---|---|---|
| DECOMPOSER | OBJECTIF (parent) | 0,n | OBJECTIF (enfant) | 0,1 |
| CONTRIBUER | OBJECTIF | 0,n | INTENTION | 0,1 |
| PREVOIR | JOUR | 0,n | INTENTION | 1,1 |
| CONCERNER | INTENTION | 0,n | PREDICTION | 0,1 |
| EXPRIMER | SOURCE | 0,n | INTENTION | 0,1 |
| REALISER | JOUR | 0,n | ACTIVITE | 1,1 |
| CONCRETISER | INTENTION | 0,n | ACTIVITE | 0,1 |
| RELATER | SOURCE | 0,n | ACTIVITE | 0,1 |
| SAISIR | JOUR | 0,n | SOURCE | 0,1 |
| NOTER | JOUR | 0,n | REFLEXION | 1,1 |
| CONSIGNER | SOURCE | 0,n | REFLEXION | 0,1 |
| ATTACHER | JOUR | 0,n | MEDIA | 0,1 |
| TRANSCRIRE | MEDIA | 0,n | SOURCE | 0,1 |
| ANALYSER | SOURCE | 0,n | EXTRACTION | 1,1 |
| EXERCER | COMPETENCE | 0,n | ACTIVITE | 0,1 |
| EVALUER | COMPETENCE | 0,n | EVALUATION | 1,1 |
| ECHANGER | PERSONNE | 0,n | ECHANGE | 1,1 |

Points d'attention :

* **DECOMPOSER** est une association réflexive. Si WinDesign ne nomme pas les rôles, ajouter
  « parent » sur la patte 0,n et « enfant » sur la patte 0,1.
* **CONCERNER** : dans l'application, ce lien est polymorphe (subject_type, subject_id). Dans
  le script, il est déclaré vers INTENTION uniquement pour que l'association apparaisse dans
  WinDesign.
* **DECISION** et **EXPERIENCE** n'ont aucune association : c'est voulu, elles se rattachent
  au temps par leurs propres dates.
* Au niveau conceptuel, les colonnes de clé étrangère (`day_id`, `goal_id`...) ne doivent
  pas apparaître comme propriétés des entités. WinDesign les retire normalement lors de la
  génération du MCD ; sinon, les supprimer des entités.

## Régénérer le script

Si le modèle de données change dans le code :

```bash
python scripts/exporter_windesign.py
```
