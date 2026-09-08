# -*- coding: utf-8 -*-
"""Genere le rapport methodologique detaille (.docx)."""
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor, Inches

BASE = Path(__file__).parent.parent
DATA = BASE / "data"
FIG = Path(__file__).parent / "figures"
OUT = Path(__file__).parent / "Rapport_Methodologique_Economie_Numerique_Togo.docx"

META = json.loads((DATA / "meta.json").read_text())

GREEN = RGBColor(0x0B, 0x6E, 0x4F)
RED = RGBColor(0xD2, 0x10, 0x34)
YELLOW = RGBColor(0xB8, 0x8A, 0x00)
INK = RGBColor(0x1C, 0x2B, 0x27)


def nf(v, dec=0):
    return (f"{v:,.{dec}f}").replace(",", " ").replace(".", ",")


doc = Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.font.color.rgb = INK


def h1(t):
    p = doc.add_heading(level=1)
    r = p.add_run(t); r.font.color.rgb = GREEN; r.font.size = Pt(16); r.bold = True
    return p


def h2(t):
    p = doc.add_heading(level=2)
    r = p.add_run(t); r.font.color.rgb = RED; r.font.size = Pt(13); r.bold = True
    return p


def para(t, size=11, bold=False, italic=False, color=INK, align=None):
    p = doc.add_paragraph()
    r = p.add_run(t); r.font.size = Pt(size); r.bold = bold; r.italic = italic
    r.font.color.rgb = color
    if align:
        p.alignment = align
    return p


def bullet(t):
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(t)
    return p


def fig(name, width=6.1, caption=None):
    if (FIG / name).exists():
        doc.add_picture(str(FIG / name), width=Inches(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if caption:
            para(caption, size=9, italic=True, color=RGBColor(0x6b, 0x7b, 0x76),
                 align=WD_ALIGN_PARAGRAPH.CENTER)


def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, hh in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(hh); r.bold = True; r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        c._tc.get_or_add_tcPr()
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), "0B6E4F")
        c._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
            for pp in cells[i].paragraphs:
                for r in pp.runs:
                    r.font.size = Pt(9.5)
    return t


# ============================ PAGE DE GARDE ============================
para("REPUBLIQUE TOGOLAISE", size=13, bold=True, color=GREEN,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("Travail – Liberte – Patrie", size=10, italic=True, color=RED,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("Ministere de l'Economie Numerique et de la Transformation Digitale",
     size=10, bold=True, color=GREEN, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
para("RAPPORT METHODOLOGIQUE", size=22, bold=True, color=GREEN,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("Diagnostic de l'acces aux telecommunications et services numeriques au Togo",
     size=14, bold=True, color=INK, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Cartographie des infrastructures · Analyse de la couverture · "
     "Priorisation et estimation des investissements",
     size=11, italic=True, color=RGBColor(0x6b, 0x7b, 0x76),
     align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
para("Data Challenge — Economie Numerique · Togo AI Lab", size=11, bold=True,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("Auteur : Maurice Kodjo SEKOU — Analyste Statisticien", size=11,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("Outils : Python (pandas) · Shiny for Python · Highcharts / Highmaps",
     size=10, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

# ============================ SOMMAIRE (texte) ============================
h1("Sommaire")
for i, s in enumerate([
    "Contexte et objectifs", "Presentation des donnees",
    "Nettoyage et preparation des donnees", "Projection demographique 2026",
    "Methodologie d'analyse statistique", "Resultats et interpretation",
    "Score de priorite et priorisation territoriale",
    "Modele d'estimation des investissements",
    "Recommandations strategiques", "Limites et perspectives",
    "Architecture technique du tableau de bord"], 1):
    para(f"{i}.  {s}", size=11)
doc.add_page_break()

# ============================ 1. CONTEXTE ============================
h1("1. Contexte et objectifs")
para("Le present rapport accompagne le tableau de bord interactif developpe dans le "
     "cadre du Data Challenge sur l'economie numerique du Togo AI Lab. L'objectif est "
     "de dresser un diagnostic clair et territorialise de l'acces aux telecommunications "
     "et aux services numeriques au Togo, puis de formuler des recommandations "
     "d'investissement pour etendre la connectivite et l'inclusion numerique.")
h2("Objectifs specifiques")
for b in [
    "Cartographier la repartition spatiale des agences des operateurs (Togocom, Moov, CANAL+) et des centres de donnees.",
    "Analyser la couverture des services numeriques (agents mobile money) et son adequation avec la population.",
    "Mettre en regard la localisation des infrastructures avec la densite demographique par subdivision administrative.",
    "Identifier les zones blanches numeriques (localites non desservies).",
    "Proposer des recommandations ciblees et chiffrees pour etendre la connectivite."]:
    bullet(b)

# ============================ 2. DONNEES ============================
h1("2. Presentation des donnees")
para("Quatre familles de donnees ouvertes ont ete mobilisees. Le tableau ci-dessous "
     "en resume la nature, la source et la volumetrie apres traitement.")
table(["Jeu de donnees", "Source", "Niveau", "Volumetrie"], [
    ["Agences telecoms (Togocom, Moov)", "geodata.gouv.tg", "Point géolocalisé",
     f"{META['n_agences_telecom']} agences"],
    ["Agents mobile money", "geodata.gouv.tg", "Point géolocalisé",
     f"{nf(META['n_mobile_money'])} agents"],
    ["Centres de donnees (datacenters)", "geodata.gouv.tg", "Point géolocalisé",
     f"{META['n_datacenters']} etablissements"],
    ["Population (RGPH-5)", "RGPH-5, 2022", "Pays→region→prefecture→commune→canton",
     f"{nf(META['national_pop_2022'])} hab."],
    ["Limites administratives", "geoBoundaries", "adm1 (5) / adm2 (40) / adm3 (373)",
     "GeoJSON"],
])
para("")
para("Chaque enregistrement d'infrastructure comporte des coordonnees geographiques "
     "(format « [longitude, latitude] »), le rattachement administratif "
     "(region, prefecture, commune, canton, localite), ainsi que des attributs "
     "descriptifs (nom, adresse, annee de creation, statut d'activite, operateur).")
para("Point d'attention : le fichier CANAL+ fourni est vide (aucune agence recensee) ; "
     "le fichier « Agences Telecom » constitue l'union des reseaux Togocom (62) et "
     "Moov (28), soit 90 agences.", italic=True)

# ============================ 3. NETTOYAGE ============================
h1("3. Nettoyage et preparation des donnees")
para("Le pretraitement a ete entierement automatise en Python (pandas). Les etapes "
     "suivantes ont ete appliquees et sont reproductibles via le script "
     "« prepare_data.py ».")
h2("3.1 Operations de nettoyage")
for b in [
    "Extraction des coordonnees : conversion de la chaine « [lon, lat] » en couples numeriques (longitude, latitude) par expression reguliere ; suppression des enregistrements sans geolocalisation.",
    "Normalisation des libelles administratifs : passage en majuscules, suppression des accents et de la ponctuation, afin de creer des cles de jointure robustes entre sources heterogenes.",
    "Extraction de l'annee de creation des agences (nettoyage des mentions « Nsp », espaces parasites).",
    "Deduplication des categories d'operateurs a partir du champ « activite_categorie ».",
    "Consolidation des operateurs mobile money (Togocom, Moov, offres conjointes « Moov, Togocom », non specifie).",
]:
    bullet(b)
h2("3.2 Reconstruction de la hierarchie de population")
para("Le fichier de population du RGPH-5 se presente comme une liste a plat, sans "
     "colonne indiquant le niveau administratif (pays, region, prefecture, commune, "
     "canton). La hierarchie a ete reconstruite par un ensemble de regles :")
for b in [
    "« TOGO » identifie le total national ; les 5 noms de regions sont reconnus par un dictionnaire de reference.",
    "Une commune est detectee par le suffixe numerique de son libelle (ex. « TONE 1 »).",
    "Une prefecture est un libelle immediatement suivi d'une de ses communes (ex. « TONE » precede « TONE 1 ») ; les autres libelles sont des cantons (feuilles).",
    "Validation par les sommes : le total des prefectures reconcilie exactement le total national (8 095 498 hab.), garantissant la coherence de la reconstruction.",
    "Deux prefectures aux communes atypiques (Ave, Danyi) ont ete recuperees manuellement apres verification des sous-totaux.",
]:
    bullet(b)
para("La jointure population ↔ infrastructures couvre 39 des 40 prefectures "
     "(la commune de Lome etant integree au Golfe dans les donnees de terrain).",
     italic=True)

# ============================ 4. PROJECTION ============================
h1("4. Projection demographique 2026")
para("Le recensement de reference (RGPH-5) date de 2022. Pour rapporter l'offre de "
     "services (actuelle) a une population comparable, la population a ete projetee a "
     f"l'horizon 2026 selon un modele de croissance geometrique au taux moyen de "
     f"{META['taux_croissance']*100:.1f} %/an :")
para("Population(2026) = Population(2022) × (1 + 0,023)^(2026−2022) = "
     f"Population(2022) × {META['facteur_projection']}", bold=True, color=GREEN,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para(f"La population nationale projetee 2026 s'etablit ainsi a "
     f"{nf(META['national_pop_2026'])} habitants (contre "
     f"{nf(META['national_pop_2022'])} en 2022). Tous les indicateurs de densite du "
     "tableau de bord sont calcules sur cette base 2026.")
fig("fig_population.png", 6.0, "Figure 1 — Population 2022 (RGPH-5) et projection 2026 par region.")

# ============================ 5. METHODES ============================
h1("5. Methodologie d'analyse statistique")
para("L'analyse combine statistique descriptive, analyse de densite (rapport de "
     "l'offre a la population), analyse de concentration spatiale, analyse de "
     "correlation et construction d'un indicateur composite de priorite.")
h2("5.1 Indicateurs de densite (adequation offre / population)")
for b in [
    "Agents mobile money pour 1 000 habitants = (nb d'agents / population) × 1 000 — proxy de l'inclusion financiere numerique.",
    "Agences telecoms pour 100 000 habitants = (nb d'agences / population) × 100 000 — proxy de l'acces au service client / connectivite.",
    "Habitants par agent = population / nb d'agents — mesure d'accessibilite (plus la valeur est elevee, moins le service est accessible).",
]:
    bullet(b)
h2("5.2 Statistique descriptive et dispersion")
para("Pour chaque indicateur : minimum, maximum, moyenne, mediane, ecart-type et "
     "coefficient de variation (CV = ecart-type / moyenne) sont calcules afin de "
     "quantifier les inegalites territoriales.")
h2("5.3 Analyse de concentration et de correlation")
para("La concentration spatiale est mesuree par la part des agents detenue par les "
     "prefectures les mieux dotees. La relation entre population et nombre d'agents "
     "est evaluee par le coefficient de correlation de Pearson.")
h2("5.4 Analyse de couverture (zones blanches)")
para("Au niveau canton (adm3, 373 unites), une zone blanche numerique est definie "
     "comme un canton n'accueillant aucun agent mobile money. Le taux de couverture "
     "est le rapport des cantons desservis au total.")

# ============================ 6. RESULTATS ============================
h1("6. Resultats et interpretation")
h2("6.1 Volume et repartition de l'offre")
para(f"Le territoire compte {nf(META['n_mobile_money'])} agents mobile money, "
     f"{META['n_agences_telecom']} agences telecoms et seulement "
     f"{META['n_datacenters']} centres de donnees. La densite nationale s'etablit a "
     f"{nf(META['mm_pour_1000_national'],2)} agents pour 1 000 habitants et "
     f"{nf(META['agences_pour_100k_national'],2)} agence pour 100 000 habitants.")
fig("fig_mm_region.png", 5.6, "Figure 2 — Agents mobile money par region.")
fig("fig_operateurs.png", 3.6, "Figure 3 — Repartition des infrastructures par operateur.")
h2("6.2 De fortes inegalites territoriales")
para("La densite d'agents mobile money varie de 0,42 a 5,36 agents pour 1 000 "
     "habitants selon la prefecture, soit un rapport de 1 a 12,8. Avec une moyenne de "
     "1,98, une mediane de 1,52 et un coefficient de variation de 60,6 %, la "
     "dispersion territoriale est tres marquee.")
fig("fig_densite.png", 6.3, "Figure 4 — Prefectures les mieux et les moins servies (densite mobile money).")
h2("6.3 Concentration spatiale et role de la population")
for b in [
    "La correlation entre population et nombre d'agents est forte (r = 0,90) : l'offre suit globalement la demographie, mais les ecarts de densite revelent des sous-equipements relatifs.",
    "La seule prefecture du Golfe (Grand Lome) concentre 25,9 % des agents ; les 5 premieres prefectures en totalisent 54,4 %.",
    "Les 3 datacenters sont tous situes dans le Golfe : une centralisation extreme qui fragilise la resilience et freine la deconcentration numerique.",
    "12 prefectures sur 39 ne disposent d'aucune agence telecom physique.",
]:
    bullet(b)
h2("6.4 Zones blanches")
para(f"Sur {META['n_cantons']} cantons, {META['n_zones_blanches']} ne comptent aucun "
     f"agent mobile money, soit un taux de couverture de "
     f"{nf((META['n_cantons']-META['n_zones_blanches'])/META['n_cantons']*100,1)} %. "
     "Ces zones blanches se concentrent dans les regions des Plateaux, de la Centrale "
     "et de la Kara.")
fig("fig_zones_blanches.png", 5.8, "Figure 5 — Cantons couverts et zones blanches par region.")

# ============================ 7. PRIORITE ============================
h1("7. Score de priorite et priorisation territoriale")
para("Un indicateur composite de priorite (0 a 100) hierarchise les prefectures selon "
     "leur sous-equipement, pondere par le poids demographique. Il combine trois "
     "dimensions normalisees (min-max) :")
para("Score = 100 × [ 0,45 × deficit(densite mobile money) + 0,35 × "
     "deficit(densite agences) + 0,20 × poids(population) ]",
     bold=True, color=GREEN, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Un deficit eleve (offre faible au regard de la population) et un poids "
     "demographique important elevent le score, donc la priorite d'intervention.")
fig("fig_priorites.png", 6.0, "Figure 6 — Classement des prefectures prioritaires.")
PREF = __import__("pandas").read_parquet(DATA / "prefectures.parquet")
top = PREF.sort_values("score_priorite", ascending=False).head(10)
table(["Rang", "Prefecture", "Region", "Population 2026", "Agents MM",
       "MM/1000", "Score"],
      [[int(r.rang_priorite), r.prefecture, r.region, nf(r.population),
        nf(r.n_mobile_money), nf(r.mm_pour_1000, 2), nf(r.score_priorite, 1)]
       for r in top.itertuples()])

# ============================ 8. INVESTISSEMENT ============================
h1("8. Modele d'estimation des investissements")
para("Le tableau de bord integre un simulateur interactif : pour un territoire et un "
     "objectif de densite choisis, il calcule le nombre de points a creer et le budget "
     "correspondant, en FCFA et en euros.")
para("Besoin = max(0 ; objectif_densite × population − offre_actuelle)", bold=True,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("Cout = besoin(mobile money) × cout_unitaire_MM + besoin(agences) × "
     "cout_unitaire_agence", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Conversion en euros a la parite fixe : 1 € = 655,957 FCFA (arrimage du Franc "
     "CFA a l'euro).")
h2("8.1 Hypotheses de couts unitaires (parametrables)")
table(["Poste", "Cout unitaire (FCFA)", "Contenu"],
      [["Point agent mobile money", "250 000", "Kit, formation, fonds de roulement initial"],
       ["Agence telecom de proximite", "15 000 000", "Amenagement et equipement d'une agence"]])
h2("8.2 Chiffrage national (objectif : 3 agents/1000 hab. et 1,5 agence/100 000 hab.)")
para("Pour porter l'ensemble du territoire a ces cibles, le besoin s'eleve a environ "
     "6 800 nouveaux points mobile money et 43 nouvelles agences, pour un "
     "investissement total estime a :")
para("3 303 500 000 FCFA  ≈  5 036 153 €", size=14, bold=True, color=RED,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("Ce budget est entierement modulable dans le tableau de bord (objectifs et couts "
     "unitaires ajustables), et ventilable par prefecture prioritaire.", italic=True)

# ============================ 9. RECOMMANDATIONS ============================
h1("9. Recommandations strategiques")
for b in [
    "Cibler en priorite les prefectures a score eleve (Kpendjal, Mo, Kpendjal-Ouest, Tandjoare, Est-Mono) pour un effet maximal sur l'inclusion.",
    "Resorber les 78 zones blanches par des programmes d'agents mobile money de proximite, en priorisant les cantons peuples des Plateaux et de la Centrale.",
    "Deconcentrer les centres de donnees hors du Grand Lome (au moins un datacenter regional secondaire) pour la resilience et la souverainete des donnees.",
    "Ouvrir des agences telecoms dans les 12 prefectures qui en sont depourvues.",
    "Piloter les investissements par le simulateur : fixer des objectifs de densite realistes et suivre le budget FCFA/EUR par territoire.",
]:
    bullet(b)

# ============================ 10. LIMITES ============================
h1("10. Limites et perspectives")
for b in [
    "La couverture reseau cellulaire (2G/3G/4G) n'est pas disponible dans les donnees ouvertes ; les zones blanches sont approchees par l'absence d'agents mobile money.",
    "Les couts unitaires sont des ordres de grandeur ; ils doivent etre affines avec les operateurs et le regulateur.",
    "La population 2026 est une projection ; l'actualisation par des donnees infra-annuelles ameliorerait la precision.",
    "L'ajout de la fibre optique, des pylones et du haut debit fixe enrichirait le diagnostic.",
]:
    bullet(b)

# ============================ 11. ARCHITECTURE ============================
h1("11. Architecture technique du tableau de bord")
for b in [
    "Pretraitement Python (pandas) : nettoyage, fusion, indicateurs, scores — script prepare_data.py.",
    "Donnees pre-agregees stockees en .parquet (moins de 1 Mo) + GeoJSON simplifie : chargement de l'ordre de la seconde, aucun calcul lourd a l'execution.",
    "Interface Shiny for Python : bandeau et barre de navigation fixes, filtres en cascade region -> prefecture -> commune -> canton, 8 onglets thematiques.",
    "Visualisations interactives Highcharts / Highmaps embarquees localement (application autonome, sans dependance CDN).",
    "Simulateur d'investissement entierement reactif (FCFA et EUR).",
]:
    bullet(b)
doc.add_paragraph()
para("Fait par Maurice Kodjo SEKOU — Analyste Statisticien · "
     "Data Challenge Economie Numerique, Togo AI Lab.",
     size=10, italic=True, color=RGBColor(0x6b, 0x7b, 0x76),
     align=WD_ALIGN_PARAGRAPH.CENTER)

doc.save(str(OUT))
print("Rapport Word ecrit :", OUT.name)
