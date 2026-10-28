# Rapport ISTS automatique (Excel + Power Query + VBA)

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `Rapport_ISTS_Modele.xlsx` | Le modèle : 14 feuilles de rapport (Tables 1 à 16, Figures 1 à 10). Il est livré avec des données **fictives** de démonstration. |
| `ModuleImportCSV.bas` | La macro VBA : bouton d'import des CSV, création des requêtes Power Query, mise en forme. |
| `Requetes_PowerQuery.txt` | Le code M de chaque requête Power Query, pour référence. La macro les crée toute seule. |
| `exemples_csv/` | Deux CSV fictifs au format de vos exports, pour faire un essai. |

## Installation (une seule fois, par la personne qui prépare le modèle, 5 minutes)

1. Ouvrez `Rapport_ISTS_Modele.xlsx` dans Excel 2016, 2019, 2021 ou Microsoft 365 (Windows).
2. Faites **Alt+F11** pour ouvrir l'éditeur VBA, puis **Fichier > Importer un fichier…** et choisissez `ModuleImportCSV.bas`. Fermez ensuite l'éditeur.
3. Faites **Fichier > Enregistrer sous** et choisissez le type **Classeur Excel prenant en charge les macros (*.xlsm)**.
4. Faites **Alt+F8**, sélectionnez `InstallerBoutons`, puis cliquez sur **Exécuter**. Deux boutons apparaissent sur la feuille *Accueil*.
5. Faites un essai : cliquez sur **Importer les CSV et générer le rapport** et choisissez les deux fichiers de `exemples_csv/`.
6. Remplissez une fois la feuille **Referentiel** : le nombre de FOSA PEPFAR appuyées par zone, utilisé dans la Table 16.
7. Enregistrez. C'est ce fichier `.xlsm` que vous distribuez aux coordonnateurs.

> Au premier import, Excel peut afficher un bandeau « Activer le contenu » (pour les macros) ou une question sur la confidentialité des données. Acceptez dans les deux cas.

## Utilisation mensuelle (coordonnateur)

1. Exportez le CSV **transport** et le CSV **rejections** de votre région.
2. Ouvrez le fichier `.xlsm` et cliquez sur **Importer les CSV et générer le rapport**.
3. Choisissez d'abord le CSV transport, puis le CSV rejections.
4. Attendez le message « Rapport mis à jour ». Toutes les feuilles `1_` à `14_` sont alors à jour.

## Paramètres (feuille Accueil, cellules jaunes)

- **Séparateur** : `,` par défaut. Mettez `;` si votre CSV utilise des points-virgules.
- **Mois du rapport** : laissez la cellule vide pour prendre le dernier mois du CSV. Sinon, tapez une date du mois voulu. Le mois précédent est calculé automatiquement.
- **Niveau d'analyse** : *Auto* fait les tableaux par **Région** si le CSV contient plusieurs régions, et par **District** sinon (cas d'un CSV régional). Vous pouvez aussi forcer *Région* ou *District*.
- **Sites pris en compte (rejets)** : *PEPFAR* (par défaut), *NON PEPFAR* ou *Tous*.

Après avoir changé un paramètre, cliquez sur **Actualiser le rapport (mêmes CSV)**.

## Comment ça marche

```
CSV transport ─┐                     ┌─ Donnees_Transport / Donnees_Rejets (tables chargées)
CSV rejections ┴─► Power Query ──────┼─ Listes des zones, couverture, nombre de FOSA
                                     └─ Tables 11 et 13 (rejets et intrants par FOSA)
                                               │
                                     Feuille Calc (une ligne par zone, formules SUMIFS)
                                               │
                        Feuilles 1_ à 14_ : tableaux triés + graphiques
```

- **Power Query** lit les CSV. Il garde les colonnes utiles dans un ordre fixe, convertit les nombres et les dates, et calcule la colonne **Periode**. Cette colonne vient de `custom_month` : la période 26/08–25/09 donne septembre.
- Les **formules** des feuilles du rapport se recalculent seules. Les zones sont triées de la plus grande à la plus petite valeur du mois.
- La **macro** fait trois choses : elle donne à Power Query le chemin des CSV, elle actualise les requêtes dans le bon ordre, puis elle masque les lignes vides et ajuste les graphiques au nombre de zones.

## Points à vérifier avec vos vraies données

- **Encodage** : les CSV sont lus en UTF-8. Si les accents s'affichent mal, signalez-le.
- **Articles (Table 12)** : les colonnes sont reconnues par mots-clés : `EDTA*`, `Vacutainer*`, `Glove*`, `Cryo*`, `Cotton*`, `Pasteur*`, `Pipette tip*`, `Alcoh*`. Tout le reste va dans *Other items*. La Table 13 (par FOSA) reprend tous les articles tels qu'ils sont écrits dans le CSV.
- **Délais (TAT)** : les moyennes du mois utilisent `duration_from_collection_days`, `duration_in_hub1_days`, `duration_in_hub2_days` et `duration_reception_to_pickup_days`. Les cellules vides sont ignorées.
- **Taux de rejet** : c'est le nombre de rejets divisé par le nombre d'échantillons transportés du mois, pour le même type de site.
- **Limite** : 40 zones par tableau au maximum, ce qui suffit pour les districts d'une région.
