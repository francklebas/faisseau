"""Répartition gauche / centre / droite et angles morts."""

from revue.couverture import angle_mort, repartition

REGLAGE = {"min_medias": 4, "part_dominante": 0.6, "part_opposee_max": 0.1}


def blocs(gauche=0, centre=0, droite=0):
    return {"gauche": ["g"] * gauche, "centre": ["c"] * centre, "droite": ["d"] * droite}


def test_repartition_compte_les_medias_pas_les_articles(cfg):
    resultat = repartition(["humanite", "humanite", "lefigaro", "franceinfo", "lemonde"], cfg)
    assert resultat == {"gauche": ["humanite", "lemonde"], "centre": ["franceinfo"], "droite": ["lefigaro"]}


def test_angle_mort_quand_un_bord_domine_et_l_autre_est_absent():
    assert angle_mort(blocs(gauche=4, centre=1), REGLAGE) == {"bord_dominant": "gauche", "bord_absent": "droite", "part": 0.8}
    assert angle_mort(blocs(droite=3, centre=2), REGLAGE)["bord_absent"] == "gauche"


def test_pas_d_angle_mort_si_couverture_partagee_ou_trop_mince():
    assert angle_mort(blocs(gauche=3, centre=2, droite=2), REGLAGE) is None
    assert angle_mort(blocs(centre=6), REGLAGE) is None  # le centre seul n'est pas un « bord »
    assert angle_mort(blocs(gauche=3), REGLAGE) is None  # moins de 4 médias : on ne conclut pas
    assert angle_mort(blocs(gauche=5, centre=2, droite=2), REGLAGE) is None  # 22 % à droite


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
