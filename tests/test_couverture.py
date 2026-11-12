"""Répartition gauche / centre / droite et angles morts."""

from revue.couverture import angle_mort, repartition

def test_repartition_compte_les_medias_pas_les_articles(cfg):
    resultat = repartition(["humanite", "humanite", "lefigaro", "franceinfo", "lemonde"], cfg)
    assert resultat == {"gauche": ["humanite", "lemonde"], "centre": ["franceinfo"], "droite": ["lefigaro"]}


def test_angle_mort_quand_un_bord_domine_et_l_autre_est_absent(cfg):
    gauche = ["humanite", "liberation", "mediapart", "politis"]
    assert angle_mort([*gauche, "franceinfo"], cfg) == {"bord_dominant": "gauche", "bord_absent": "droite", "part": 0.8}
    assert angle_mort(["lefigaro", "cnews", "europe1", "franceinfo", "rfi"], cfg)["bord_absent"] == "gauche"
    assert angle_mort([*gauche, *gauche, "franceinfo"], cfg)["part"] == 0.8  # un média = une voix


def test_pas_d_angle_mort_si_couverture_partagee_ou_trop_mince(cfg):
    assert angle_mort(["humanite", "liberation", "mediapart", "franceinfo", "rfi", "lefigaro", "cnews"], cfg) is None
    assert angle_mort(["franceinfo", "rfi", "lcp", "bfmtv", "lacroix", "20minutes"], cfg) is None  # le centre n'est pas un « bord »
    assert angle_mort(["humanite", "liberation", "mediapart"], cfg) is None  # moins de 4 médias : on ne conclut pas
    # 22 % à droite : couvert par l'autre bord
    assert angle_mort(["humanite", "liberation", "mediapart", "politis", "basta", "franceinfo", "rfi", "lefigaro", "cnews"], cfg) is None


def test_centre_gauche_et_centre_droit_ne_font_pas_un_bord(cfg):
    """Rangés à gauche et à droite à l'affichage, ils ne suffisent pas à créer un angle mort."""
    medias = ["humanite", "lemonde", "huffpost", "franceinfo"]
    assert len(repartition(medias, cfg)["gauche"]) == 3
    assert angle_mort(medias, cfg) is None
    assert angle_mort(["lefigaro", "cnews", "lexpress", "lopinion", "franceinfo"], cfg) is None  # 40 % de droite
    # … et ne comptent pas non plus comme couverture du bord d'en face
    assert angle_mort(["humanite", "liberation", "mediapart", "lexpress"], cfg)["bord_absent"] == "droite"


def test_les_bords_viennent_de_la_configuration(cfg):
    import copy

    large = copy.copy(cfg)
    large.reglages = copy.deepcopy(cfg.reglages)
    large.reglages["couverture"]["angle_mort"]["bords"]["gauche"].append("centre-gauche")
    assert angle_mort(["humanite", "lemonde", "huffpost", "franceinfo"], large)["bord_absent"] == "droite"


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
