"""Répartition gauche / centre / droite et asymétrie de couverture entre les deux bords."""

from dataclasses import replace

from conftest import article

from revue.couverture import asymetrie, depeches, effectifs, est_sport, repartition

GAUCHE = ["humanite", "liberation", "mediapart", "politis", "reporterre", "basta"]  # 6 médias
DROITE = ["lefigaro", "cnews", "europe1", "lejdd", "valeursactuelles", "causeur", "atlantico", "sudradio", "bvoltaire"]  # 9
CENTRE = ["franceinfo", "rfi", "lcp", "bfmtv"]
EFFECTIF = {"gauche": 6, "droite": 9}


TITRES = [
    "La mairie ferme la piscine", "Budget voté dans la douleur", "Un pont menace de céder", "Les agriculteurs bloquent la rocade",
    "Nouvelle ligne de tramway", "Le musée rouvre ses portes", "Tempête sur le littoral", "Grève dans les écoles",
    "Le marché déménage", "Un chantier prend du retard", "Record de fréquentation au zoo", "La gare change de nom",
]  # fmt: skip


def arts(medias: list[str]):
    """Un article par mention de média, chacun avec un titre propre (aucune dépêche reprise)."""
    return [article(m, TITRES[i % len(TITRES)]) for i, m in enumerate(medias)]


def test_repartition_compte_les_medias_pas_les_articles(cfg):
    resultat = repartition(["humanite", "humanite", "lefigaro", "franceinfo", "lemonde"], cfg)
    assert resultat == {"gauche": ["humanite"], "centre-gauche": ["lemonde"], "centre": ["franceinfo"], "centre-droit": [], "droite": ["lefigaro"]}


def test_effectifs_comptent_les_medias_presents_par_bord(cfg):
    assert effectifs(GAUCHE + DROITE + CENTRE + ["lemonde", "lexpress", "humanite"], cfg) == EFFECTIF


def test_asymetrie_compare_des_parts_et_non_des_nombres(cfg):
    """Deux médias de gauche sur 6 pèsent autant que trois médias de droite sur 9."""
    a = asymetrie(arts(["humanite", "liberation", "lefigaro", "cnews", "europe1", "franceinfo"]), EFFECTIF, cfg)
    assert a["gauche"] == {"medias": ["humanite", "liberation"], "depeche": [], "total": 6, "part": 0.333}
    assert a["droite"]["part"] == 0.333
    assert a["ecart"] == 0 and a["bord_dominant"] is None and not a["notable"]


def test_asymetrie_notable_quand_un_bord_couvre_nettement_plus(cfg):
    a = asymetrie(arts(["humanite", "liberation", "mediapart", "franceinfo"]), EFFECTIF, cfg)
    assert a["ecart"] == 0.5 and a["bord_dominant"] == "gauche" and a["notable"]
    b = asymetrie(arts(["lefigaro", "cnews", "europe1", "lejdd", "rfi", "humanite"]), EFFECTIF, cfg)
    assert b["ecart"] == round(1 / 6 - 4 / 9, 3) and b["bord_dominant"] == "droite" and b["notable"]
    # un média = une voix, quel que soit son nombre d'articles
    assert asymetrie(arts(["humanite"] * 5 + ["liberation", "mediapart"]), EFFECTIF, cfg)["ecart"] == 0.5


def test_asymetrie_sous_les_seuils_n_est_pas_notable(cfg):
    # un seul média : écart de 17 points, sous le seuil
    assert not asymetrie(arts(["humanite", "franceinfo", "rfi"]), EFFECTIF, cfg)["notable"]
    # écart de 33 − 11 = 22 points : un seul média de différence, sous le seuil
    assert not asymetrie(arts(["humanite", "liberation", "lefigaro", "franceinfo"]), EFFECTIF, cfg)["notable"]
    # le centre seul ne penche d'aucun côté
    assert asymetrie(arts(CENTRE), EFFECTIF, cfg)["ecart"] == 0


def test_min_medias_bord_ecarte_un_bord_reduit_a_un_media(cfg):
    """Si un bord n'a que 3 médias présents, un seul d'entre eux fait 33 points : pas notable pour autant."""
    a = asymetrie(arts(["humanite", "franceinfo", "rfi"]), {"gauche": 3, "droite": 9}, cfg)
    assert a["ecart"] == 0.333 and not a["notable"]


def test_centre_gauche_et_centre_droit_ne_font_pas_un_bord(cfg):
    """La barre et la comparaison parlent de la même gauche : Le Monde n'y figure ni dans l'une ni dans l'autre."""
    medias = ["humanite", "lemonde", "huffpost", "lexpress", "franceinfo"]
    blocs = repartition(medias, cfg)
    a = asymetrie(arts(medias), EFFECTIF, cfg)
    assert blocs["gauche"] == a["gauche"]["medias"] == ["humanite"]
    assert blocs["droite"] == a["droite"]["medias"] == []
    assert blocs["centre-gauche"] == ["lemonde", "huffpost"] and blocs["centre-droit"] == ["lexpress"]


def test_sujet_de_sport_n_est_pas_classe(cfg):
    """Quatre médias de droite sur un match : l'écart existe, mais il tient à la rubrique."""
    sport = [replace(a, url=f"https://{a.media_id}.example/sport/football/{i}") for i, a in enumerate(arts(["lefigaro", "cnews", "europe1", "lejdd"]))]
    a = asymetrie(sport, EFFECTIF, cfg)
    assert a["ecart"] == -0.444 and a["ecarte"] == "sport" and not a["notable"]
    reglage = cfg.reglages["couverture"]["asymetrie"]["ecarter"]
    assert est_sport(sport, reglage) and not est_sport(arts(["lefigaro", "cnews"]), reglage)
    # un seul article de sport sur quatre : le sujet reste classé
    mixte = sport[:1] + arts(["cnews", "europe1", "lejdd"])
    assert asymetrie(mixte, EFFECTIF, cfg)["ecarte"] is None
    # « sport » doit être une rubrique de l'adresse, pas un mot du titre
    assert not est_sport([replace(a, url=f"https://x.example/politique/le-ministere-des-sports-{i}") for i, a in enumerate(sport)], reglage)


def test_depeche_reprise_ne_compte_pas_pour_un_bord(cfg):
    """Trois médias de droite publient le même titre d'agence : aucun choix éditorial à mesurer."""
    titre = "Sébastien Lecornu formalise la création de 5 000 places supplémentaires en licence"
    reprises = [article("lefigaro", "Colère lycéenne : " + titre), article("europe1", titre), article("sudradio", titre), article("franceinfo", titre)]
    a = asymetrie(reprises, EFFECTIF, cfg)
    assert a["droite"]["medias"] == [] and a["droite"]["depeche"] == ["lefigaro", "europe1", "sudradio"]
    assert a["ecart"] == 0 and not a["notable"]
    # un média qui ajoute un article au titre propre compte de nouveau
    avec_analyse = reprises + [article("lefigaro", "Pourquoi les universités manquent de places")]
    assert asymetrie(avec_analyse, EFFECTIF, cfg)["droite"]["medias"] == ["lefigaro"]
    # deux titres identiques du même média ne sont pas une reprise
    assert depeches([article("lefigaro", titre), article("lefigaro", titre)], 0.75) == set()


def test_bord_sans_media_present_ne_fait_pas_d_erreur(cfg):
    a = asymetrie(arts(["lefigaro", "cnews", "europe1"]), {"gauche": 0, "droite": 9}, cfg)
    assert a["gauche"]["part"] == 0 and a["ecart"] == -0.333


def test_la_frontiere_des_blocs_vient_de_la_configuration(cfg):
    """Aucun classement en dur : déplacer une orientation dans reglages.yaml change le bloc et le bord."""
    import copy

    autre = copy.copy(cfg)
    autre.reglages = copy.deepcopy(cfg.reglages)
    assert cfg.bloc("lemonde") == "centre-gauche" and cfg.bord("lemonde") is None
    blocs = autre.reglages["couverture"]["blocs"]
    blocs["centre-gauche"].remove("centre-gauche")
    blocs["gauche"].append("centre-gauche")
    assert autre.bloc("lemonde") == autre.bord("lemonde") == "gauche"
    assert asymetrie(arts(["humanite", "lemonde", "franceinfo"]), EFFECTIF, autre)["gauche"]["medias"] == ["humanite", "lemonde"]
