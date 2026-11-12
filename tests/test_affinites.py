"""Contrôle du classement par la couverture : calcul, seuils et garde-fous."""

import copy
import json

import pytest
from conftest import article

from revue.affinites import analyser, ecrire_couvertures, en_markdown, lire_couvertures, proximite
from revue.modeles import Sujet

GAUCHE = ["humanite", "liberation", "mediapart"]
CENTRE = ["franceinfo", "rfi", "bfmtv"]
DROITE = ["lefigaro", "cnews", "europe1"]


@pytest.fixture
def cfg_test(cfg, tmp_path, monkeypatch):
    monkeypatch.setenv("REVUE_DONNEES", str(tmp_path))
    c = copy.copy(cfg)
    c.reglages = copy.deepcopy(cfg.reglages)
    c.reglages["affinites"] = {"min_editions": 3, "min_sujets": 4, "marge": 0.05}
    return c


def historique(deserteur: str | None = None) -> dict[str, set[str]]:
    """Chaque bloc a ses 6 sujets propres, plus 4 sujets communs à tous.

    `deserteur` : un média qui couvre les sujets propres à la droite au lieu de ceux de son bloc.
    """
    par_media: dict[str, set[str]] = {}
    for bloc, medias in (("g", GAUCHE), ("c", CENTRE), ("d", DROITE)):
        for media in medias:
            propre = "d" if media == deserteur else bloc
            par_media[media] = {f"{propre}{i}" for i in range(6)} | {f"commun{i}" for i in range(4)}
    return par_media


def test_proximite():
    assert proximite({"a", "b"}, {"a", "b"}) == 1
    assert proximite({"a"}, {"b"}) == 0
    assert proximite(set(), {"a"}) == 0
    assert proximite({"a", "b", "c", "d"}, {"a"}) == 0.5  # 1 / sqrt(4 × 1)


def test_un_media_conforme_a_son_bloc_n_est_pas_signale(cfg_test):
    rapport = analyser(5, historique(), cfg_test)
    assert rapport.concluant and rapport.signales == []
    profil = next(p for p in rapport.profils if p.media == "humanite")
    assert profil.bloc == profil.bloc_proche == "gauche"
    assert profil.par_bloc["gauche"] == 1 and profil.par_bloc["droite"] == pytest.approx(0.4)


def test_un_media_qui_couvre_les_sujets_d_un_autre_bloc_est_signale(cfg_test):
    rapport = analyser(5, historique(deserteur="mediapart"), cfg_test)
    (signale,) = rapport.signales
    assert (signale.media, signale.bloc, signale.bloc_proche) == ("mediapart", "gauche", "droite")
    assert signale.ecart() == pytest.approx(0.6)
    assert signale.voisins[0][0] in DROITE


def test_le_signalement_ne_change_aucun_classement(cfg_test):
    avant = {m.id: m.orientation for m in cfg_test.medias.values()}
    analyser(5, historique(deserteur="mediapart"), cfg_test)
    assert {m.id: m.orientation for m in cfg_test.medias.values()} == avant


def test_historique_trop_court_est_declare_non_concluant(cfg_test):
    rapport = analyser(1, historique(deserteur="mediapart"), cfg_test)
    assert not rapport.concluant
    texte = en_markdown(rapport, cfg_test)
    assert "Historique insuffisant" in texte and "non concluants" in texte and "Médias à relire" not in texte
    assert "Médias à relire" in en_markdown(analyser(3, historique(deserteur="mediapart"), cfg_test), cfg_test)


def test_media_avec_trop_peu_de_sujets_est_ecarte_du_calcul(cfg_test):
    par_media = historique()
    par_media["politis"] = {"d0", "d1"}  # deux sujets « de droite » : trop peu pour conclure
    par_media["inconnu"] = {"g0", "g1", "g2", "g3", "g4"}  # absent de medias.yaml
    rapport = analyser(5, par_media, cfg_test)
    assert rapport.ignores == [("politis", 2)]
    assert "politis" not in {p.media for p in rapport.profils} and rapport.signales == []
    assert "inconnu" not in {p.media for p in rapport.profils}


def test_archive_des_couvertures_relue_sur_plusieurs_editions(cfg_test):
    a = Sujet(articles=[article("humanite", "Titre A"), article("lefigaro", "Titre A bis"), article("humanite", "A ter")], signature="aaa")
    b = Sujet(articles=[article("rfi", "Titre B"), article("lefigaro", "Titre B bis")], signature="bbb")
    chemin = ecrire_couvertures([a, b], cfg_test, "2026-11-11")
    ecrire_couvertures([a], cfg_test, "2026-11-12")  # le même sujet le lendemain ne compte qu'une fois
    assert json.loads(chemin.read_text(encoding="utf-8"))["sujets"][0] == {"id": "aaa", "titre": "Titre A", "medias": ["humanite", "lefigaro"]}
    nb, par_media = lire_couvertures(chemin.parent)
    assert nb == 2 and par_media == {"humanite": {"aaa"}, "lefigaro": {"aaa", "bbb"}, "rfi": {"bbb"}}
    assert lire_couvertures(chemin.parent / "absent") == (0, {})
