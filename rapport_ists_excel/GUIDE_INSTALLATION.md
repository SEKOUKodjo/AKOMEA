# Rapport ISTS automatique : deux versions prêtes à l'emploi

| Fichier | Contenu | Pour qui |
|---|---|---|
| `RAPPORT_ISTS_Macro.zip` | `Rapport_ISTS_Macro.xlsm` : la macro et les requêtes Power Query sont déjà intégrées. Un bouton « Importer les CSV » ouvre une fenêtre pour choisir les fichiers. | Coordonnateurs dont le poste autorise les macros |
| `RAPPORT_ISTS_PowerQuery.zip` | `Rapport_ISTS_PowerQuery.xlsx` : aucune macro. Il lit les CSV dans un dossier fixe et s'actualise à l'ouverture. | Postes où les macros sont bloquées |

Chaque zip contient un `LISEZ-MOI.txt` (les instructions détaillées) et deux CSV fictifs pour faire un essai.

## Version Power Query : organisation du dossier

Extrayez `RAPPORT_ISTS_PowerQuery.zip` directement dans `C:\`. Vous obtenez :

```
C:\RAPPORT_ISTS\
    Rapport_ISTS_PowerQuery.xlsx     <- le rapport
    CSV\TRANSPORT\                   <- déposez le CSV transport du mois
    CSV\REJETS\                      <- déposez le CSV rejections du mois
    EXEMPLES_FICTIFS\                <- CSV de test
```

Dans chaque dossier, c'est le CSV **le plus récent** qui est utilisé.

Chaque mois : déposez les 2 CSV, ouvrez le rapport, puis **Données > Actualiser tout** (l'actualisation se fait aussi à l'ouverture).

Pour utiliser un autre emplacement : **Données > Requêtes et connexions > Parametres > Modifier**, puis changez la ligne `Dossier`.

## Version macro

1. Extrayez le zip où vous voulez.
2. Faites un clic droit sur le `.xlsm` > **Propriétés** > cochez **Débloquer**.
3. Ouvrez le fichier et activez le contenu.
4. Cliquez sur **Importer les CSV et générer le rapport**, puis choisissez le CSV transport, puis le CSV rejections.

Si la macro ne se charge pas, le dossier `SECOURS\` contient le même classeur sans code et le module `ModuleImportCSV.bas` à importer avec Alt+F11. Les étapes sont dans le LISEZ-MOI.

## Ce que contiennent les deux classeurs

- **Requêtes Power Query intégrées** (16 au total, voir `Requetes_PowerQuery.txt`) :
  - import des CSV, qui convertit les types et calcule le mois à partir de `custom_month` ;
  - listes des régions et districts, couverture des FOSA ;
  - Tables 11 et 13 (rejets et intrants par FOSA) ;
  - données des graphiques par zone.
- **Feuilles 1_ à 14_** : les Tables 1 à 16 et les Figures 1 à 10 du rapport.
- **Graphiques par zone** : ils lisent les tables Power Query. Ils s'ajustent donc tout seuls au nombre de régions ou de districts, sans macro.
- **Zones automatiques** : par Région si le CSV contient plusieurs régions, sinon par District.
- **Mois automatique** : le dernier mois du CSV, comparé au mois précédent.
- **Sites pour les rejets** : PEPFAR par défaut. C'est modifiable sur la feuille Accueil.
- **Table 16** : remplissez une fois la feuille `Referentiel` avec le nombre de FOSA PEPFAR appuyées par zone.

Configuration requise : Excel 2016, 2019, 2021 ou Microsoft 365, sous Windows.
