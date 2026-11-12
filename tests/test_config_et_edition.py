"""Fichier des médias et édition publiée."""

import json

from conftest import FauxLLM, article

from revue.config import ORIENTATIONS
from revue.edition import ecrire_edition, slug
from revue.faits import extraire
from revue.modeles import Sujet
from revue.regroupement import signature


def test_fichier_des_medias(cfg):
    actifs = cfg.medias_actifs
    assert 35 <= len(actifs) <= 60
    for media in cfg.medias.values():
        assert media.orientation in ORIENTATIONS
        assert media.justification, f"{media.id} : justification manquante"
        assert media.flux and all(u.startswith("https://") for u in media.flux)
    # Chaque bloc est représenté par au moins dix médias actifs.
    for bloc in ("gauche", "centre", "droite"):
        assert sum(1 for m in actifs if cfg.bloc(m.id) == bloc) >= 10


def test_edition_chaque_fait_renvoie_a_un_article_liste(cfg, tmp_path, monkeypatch):
    monkeypatch.setenv("REVUE_DONNEES", str(tmp_path))
    articles = [
        article("humanite", "Villeneuve : la piscine Jean-Moulin va fermer", "Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin."),
        article("liberation", "La piscine de Villeneuve fermée", "Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin. Coût des travaux : 4 millions d'euros."),
        article("mediapart", "Villeneuve ferme sa piscine", "Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin."),
        article("lemonde", "Fermeture votée pour la piscine Jean-Moulin de Villeneuve", ""),
        article("politis", "Tout autre chose : le marché de Noël ouvre", ""),
    ]  # fmt: skip
    reponse = json.dumps({
        "titre": "Villeneuve vote la fermeture de la piscine Jean-Moulin",
        "faits": [
            {"fait": "Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin.", "sources": [1, 2, 3]},
            {"fait": "Le coût des travaux est de 4 millions d'euros.", "sources": [2]},
        ],
        "hors_sujet": [5],
    })  # fmt: skip
    sujet = Sujet(articles=articles, signature=signature(articles))
    sujet.extraction = extraire(articles, FauxLLM(reponse), {}, cfg.reglages["faits"])

    chemin = ecrire_edition([sujet], cfg, {"nb_articles": 5}, {"gauche": 6, "droite": 10})
    edition = json.loads(chemin.read_text(encoding="utf-8"))
    (publie,) = edition["sujets"]

    numeros = {a["n"] for a in publie["articles"]}
    assert len(publie["articles"]) == 4  # l'article hors sujet n'est pas publié
    for fait in publie["faits_communs"] + publie["faits_recoupes"] + publie["affirmations_isolees"]:
        assert fait["sources"] and set(fait["sources"]) <= numeros
    assert [f["medias"] for f in publie["affirmations_isolees"]] == [["liberation"]]
    assert len(publie["faits_communs"]) == 1

    # Couverture : quatre médias du bloc gauche, aucun à droite. Pour l'asymétrie, Le Monde
    # (centre-gauche) ne compte pas : 3 médias de gauche sur 6 présents, 0 sur 10 à droite.
    assert publie["couverture"] == {"gauche": ["humanite", "liberation", "mediapart", "lemonde"], "centre": [], "droite": []}
    assert publie["asymetrie"]["gauche"] == {"medias": ["humanite", "liberation", "mediapart"], "total": 6, "part": 0.5}
    assert publie["asymetrie"]["droite"] == {"medias": [], "total": 10, "part": 0.0}
    assert publie["asymetrie"]["ecart"] == 0.5 and publie["asymetrie"]["notable"]
    assert edition["stats"]["nb_asymetries"] == 1 and edition["stats"]["effectif_bords"] == {"gauche": 6, "droite": 10}

    # Ce qui est publié : titres et liens, pas les extraits.
    assert set(publie["articles"][0]) == {"n", "media", "titre", "url", "publie_le"}
    assert all(m["statut"] in ("a_valider", "valide") for m in edition["medias"])
    index = json.loads((tmp_path / "editions" / "index.json").read_text(encoding="utf-8"))
    assert index[0]["date"] == edition["date"] and index[0]["nb_sujets"] == 1


def test_slug():
    assert slug("Présidentielle 2027 : l'État face à l'élection", "abcdef123") == "presidentielle-2027-l-etat-face-a-l-election-abcdef"
    assert slug("…", "abcdef123") == "abcdef123"


def test_sources_des_medias_sont_completes(cfg):
    """Chaque source a un lien, une citation, un type et un verdict connus ; un « contredit » s'explique."""
    sources = [(m.id, s) for m in cfg.medias.values() for s in m.sources]
    assert sources
    for media_id, s in sources:
        assert s["url"].startswith("https://") and s["citation"] and s["titre"], media_id
        assert s["verdict"] != "contredit" or s["note"], media_id
    # L'audience est une information : elle ne doit jamais servir au classement.
    assert all(m.statut == "a_valider" for m in cfg.medias.values())


def test_source_incomplete_refusee(tmp_path):
    import pytest

    from revue.config import lire_medias

    chemin = tmp_path / "medias.yaml"
    base = "medias:\n  - {id: a, nom: A, site: 'https://a.example', flux: 'https://a.example/rss', orientation: centre, justification: j, sources: [%s]}\n"
    chemin.write_text(base % "{url: 'https://x.example', type: presse, titre: t, citation: c, verdict: contredit}", encoding="utf-8")
    with pytest.raises(ValueError, match="contredit"):
        lire_medias(chemin)
    chemin.write_text(base % "{url: 'https://x.example', type: rumeur, titre: t, citation: c, verdict: confirme}", encoding="utf-8")
    with pytest.raises(ValueError, match="type ou verdict"):
        lire_medias(chemin)
