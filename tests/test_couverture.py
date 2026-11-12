"""Répartition gauche / centre / droite et asymétrie de couverture entre les deux bords."""

from revue.couverture import asymetrie, effectifs, repartition

GAUCHE = ["humanite", "liberation", "mediapart", "politis", "reporterre", "basta"]  # 6 médias
DROITE = ["lefigaro", "cnews", "europe1", "lejdd", "valeursactuelles", "causeur", "atlantico", "sudradio", "bvoltaire"]  # 9
CENTRE = ["franceinfo", "rfi", "lcp", "bfmtv"]
EFFECTIF = {"gauche": 6, "droite": 9}


def test_repartition_compte_les_medias_pas_les_articles(cfg):
    resultat = repartition(["humanite", "humanite", "lefigaro", "franceinfo", "lemonde"], cfg)
    assert resultat == {"gauche": ["humanite", "lemonde"], "centre": ["franceinfo"], "droite": ["lefigaro"]}


def test_effectifs_comptent_les_medias_presents_par_bord(cfg):
    assert effectifs(GAUCHE + DROITE + CENTRE + ["lemonde", "lexpress", "humanite"], cfg) == EFFECTIF


def test_asymetrie_compare_des_parts_et_non_des_nombres(cfg):
    """Deux médias de gauche sur 6 pèsent autant que trois médias de droite sur 9."""
    a = asymetrie(["humanite", "liberation", "lefigaro", "cnews", "europe1", "franceinfo"], EFFECTIF, cfg)
    assert a["gauche"] == {"medias": ["humanite", "liberation"], "total": 6, "part": 0.333}
    assert a["droite"]["part"] == 0.333
    assert a["ecart"] == 0 and a["bord_dominant"] is None and not a["notable"]


def test_asymetrie_notable_quand_un_bord_couvre_nettement_plus(cfg):
    a = asymetrie(["humanite", "liberation", "mediapart", "franceinfo"], EFFECTIF, cfg)
    assert a["ecart"] == 0.5 and a["bord_dominant"] == "gauche" and a["notable"]
    b = asymetrie(["lefigaro", "cnews", "europe1", "lejdd", "rfi", "humanite"], EFFECTIF, cfg)
    assert b["ecart"] == round(1 / 6 - 4 / 9, 3) and b["bord_dominant"] == "droite" and b["notable"]
    # un média = une voix, quel que soit son nombre d'articles
    assert asymetrie(["humanite"] * 5 + ["liberation", "mediapart"], EFFECTIF, cfg)["ecart"] == 0.5


def test_asymetrie_sous_les_seuils_n_est_pas_notable(cfg):
    # un seul média : écart de 17 points, sous le seuil
    assert not asymetrie(["humanite", "franceinfo", "rfi"], EFFECTIF, cfg)["notable"]
    # écart de 33 − 11 = 22 points : un seul média de différence, sous le seuil
    assert not asymetrie(["humanite", "liberation", "lefigaro", "franceinfo"], EFFECTIF, cfg)["notable"]
    # le centre seul ne penche d'aucun côté
    assert asymetrie(CENTRE, EFFECTIF, cfg)["ecart"] == 0


def test_min_medias_bord_ecarte_un_bord_reduit_a_un_media(cfg):
    """Si un bord n'a que 3 médias présents, un seul d'entre eux fait 33 points : pas notable pour autant."""
    a = asymetrie(["humanite", "franceinfo", "rfi"], {"gauche": 3, "droite": 9}, cfg)
    assert a["ecart"] == 0.333 and not a["notable"]


def test_centre_gauche_et_centre_droit_ne_font_pas_un_bord(cfg):
    """Rangés à gauche et à droite à l'affichage, ils ne comptent pour aucun bord ici."""
    medias = ["humanite", "lemonde", "huffpost", "lexpress", "franceinfo"]
    assert len(repartition(medias, cfg)["gauche"]) == 3
    a = asymetrie(medias, EFFECTIF, cfg)
    assert a["gauche"]["medias"] == ["humanite"] and a["droite"]["medias"] == []


def test_bord_sans_media_present_ne_fait_pas_d_erreur(cfg):
    a = asymetrie(["lefigaro", "cnews", "europe1"], {"gauche": 0, "droite": 9}, cfg)
    assert a["gauche"]["part"] == 0 and a["ecart"] == -0.333


def test_les_bords_viennent_de_la_configuration(cfg):
    import copy

    large = copy.copy(cfg)
    large.reglages = copy.deepcopy(cfg.reglages)
    large.reglages["couverture"]["asymetrie"]["bords"]["gauche"].append("centre-gauche")
    assert asymetrie(["humanite", "lemonde", "franceinfo"], EFFECTIF, large)["gauche"]["medias"] == ["humanite", "lemonde"]


def test_la_frontiere_des_blocs_vient_de_la_configuration(cfg):
    """Aucun classement en dur : déplacer une orientation dans reglages.yaml change le bloc."""
    import copy

    autre = copy.copy(cfg)
    autre.reglages = copy.deepcopy(cfg.reglages)
    assert cfg.bloc("lemonde") == "gauche"  # centre-gauche → gauche par défaut
    autre.reglages["couverture"]["blocs"] = {
        "gauche": ["extreme-gauche", "gauche"],
        "centre": ["centre-gauche", "centre", "centre-droit"],
        "droite": ["droite", "extreme-droite"],
    }
    assert autre.bloc("lemonde") == "centre"
