"""Regroupement : deux sujets proches ne doivent pas être fusionnés."""

import json
import os
from collections import Counter

import numpy as np
import pytest
from conftest import RACINE, article
from sklearn.cluster import AgglomerativeClustering

from revue.regroupement import construire_sujets, regrouper, signature


def _unitaire(v):
    return v / np.linalg.norm(v)


def deux_sujets_voisins_et_un_pont():
    """Deux sujets A et B (similarité interne 0,8 ; croisée 0,48) et un article « pont »
    à 0,8 de chaque article de A et de B : le cas typique de deux affaires voisines
    reliées par un article de synthèse."""
    d = 12
    e = np.eye(d)
    centre_b = 0.6 * e[0] + 0.8 * e[1]
    a = [_unitaire(np.sqrt(0.8) * e[0] + np.sqrt(0.2) * e[2 + i]) for i in range(3)]
    b = [_unitaire(np.sqrt(0.8) * centre_b + np.sqrt(0.2) * e[5 + i]) for i in range(3)]
    pont = _unitaire(e[0] + centre_b)
    return np.array(a + b + [pont], dtype=np.float32)


def test_deux_sujets_proches_ne_fusionnent_pas_par_chainage():
    vecteurs = deux_sujets_voisins_et_un_pont()
    assert vecteurs[0] @ vecteurs[3] < 0.58 < vecteurs[0] @ vecteurs[6]  # le pont relie, A et B non

    groupes = regrouper(vecteurs, seuil=0.58)
    groupe_de = {i: n for n, g in enumerate(groupes) for i in g}
    assert groupe_de[0] == groupe_de[1] == groupe_de[2]
    assert groupe_de[3] == groupe_de[4] == groupe_de[5]
    assert groupe_de[0] != groupe_de[3]

    # Contre-épreuve : un simple seuil sur le plus proche voisin souderait les deux sujets.
    naif = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage="single", distance_threshold=0.42)
    assert len(set(naif.fit_predict(vecteurs))) == 1


def test_seuil_respecte():
    e = np.eye(4, dtype=np.float32)
    proches = np.array([e[0], _unitaire(e[0] + 0.5 * e[1]), e[2], e[3]], dtype=np.float32)
    assert sorted(map(sorted, regrouper(proches, 0.8))) == [[0, 1], [2], [3]]
    assert len(regrouper(proches, 0.95)) == 4
    assert regrouper(np.zeros((0, 4)), 0.5) == []
    assert regrouper(e[:1], 0.5) == [[0]]


def test_un_sujet_exige_plusieurs_medias_distincts():
    """Trois articles identiques d'un même média ne font pas un sujet."""
    e = np.eye(3, dtype=np.float32)
    articles = [article("alpha", f"Titre {i}") for i in range(3)] + [article(m, "Autre") for m in ("alpha", "beta", "gamma")]
    vecteurs = np.array([e[0]] * 3 + [e[1]] * 3)
    sujets = construire_sujets(articles, vecteurs, seuil=0.9, min_medias=3)
    assert len(sujets) == 1
    assert sujets[0].medias == ["alpha", "beta", "gamma"]


def test_articles_par_media_plafonnes_et_signature_stable():
    e = np.eye(2, dtype=np.float32)
    articles = [article("alpha", f"Alpha {i}") for i in range(5)] + [article("beta", "B"), article("gamma", "G")]
    vecteurs = np.array([e[0]] * 7)
    sujet = construire_sujets(articles, vecteurs, 0.9, min_medias=3, max_articles_par_media=2)[0]
    assert Counter(a.media_id for a in sujet.articles) == {"alpha": 2, "beta": 1, "gamma": 1}
    assert sujet.signature == signature(list(reversed(sujet.articles)))


# ───────── Test d'intégration : vrai modèle, vrais titres relevés le 2026-11-11 ─────────

VOISINS = [
    # Trois annonces de la même campagne présidentielle, toutes titrées « Présidentielle 2027 : … »
    ("riner-candidature", "zemmour-candidature"),
    ("riner-candidature", "retailleau-primaire"),
    ("zemmour-candidature", "retailleau-primaire"),
    # Deux affaires impliquant l'Iran le même jour
    ("cyberattaque-frigos-iran", "iran-menace-bases"),
    # Deux sujets sur la guerre en Ukraine
    ("pourparlers-abou-dhabi", "melenchon-ukraine"),
    # Deux actualités espagnoles
    ("greve-generale-espagne", "tiktok-enquete-espagne"),
    # Deux actualités russes
    ("russie-interdit-deputes-journalistes", "ambassadeur-russe-mort"),
]


def _modele_en_cache(nom: str) -> bool:
    try:
        from huggingface_hub import try_to_load_from_cache

        return isinstance(try_to_load_from_cache(nom, "config.json"), str)
    except Exception:
        return False


@pytest.mark.modele
def test_sujets_proches_reels_restent_separes(cfg):
    modele = cfg.modele_embeddings
    if not (_modele_en_cache(modele["nom"]) or os.environ.get("REVUE_TESTS_MODELE")):
        pytest.skip(f"modèle {modele['nom']} absent du cache (REVUE_TESTS_MODELE=1 pour le télécharger)")
    from revue.plongements import encodeur_depuis

    donnees = json.loads((RACINE / "tests" / "donnees" / "titres_etiquetes.json").read_text(encoding="utf-8"))
    titres, etiquettes = [], []
    for sujet in donnees["sujets"]:
        for t in sujet["titres"]:
            titres.append(t["titre"])
            etiquettes.append(sujet["id"])
    vecteurs = encodeur_depuis(cfg).encoder(titres)
    groupes = regrouper(vecteurs, modele["seuil"], cfg.reglages["regroupement"]["liaison"])
    groupe_de = {i: n for n, g in enumerate(groupes) for i in g}
    groupes_du_sujet = {s: {groupe_de[i] for i, e in enumerate(etiquettes) if e == s} for s in set(etiquettes)}

    # 1. Deux sujets voisins ne partagent aucun groupe.
    for a, b in VOISINS:
        assert not groupes_du_sujet[a] & groupes_du_sujet[b], f"{a} et {b} ont été fusionnés"

    # 2. Aucun groupe ne mélange deux sujets étrangers l'un à l'autre (hors même famille).
    famille = {s["id"]: s.get("famille") or s["id"] for s in donnees["sujets"]}
    for groupe in groupes:
        assert len({famille[etiquettes[i]] for i in groupe}) == 1

    # 3. Un sujet net (mêmes faits, formulations variées) est entièrement réuni.
    assert len(groupes_du_sujet["ambassadeur-russe-mort"]) == 1
    assert len(groupes_du_sujet["iran-menace-bases"]) == 1
