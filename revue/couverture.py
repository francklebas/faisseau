"""Répartition de la couverture par bloc (gauche, centre, droite) et angles morts."""

from __future__ import annotations

from urllib.parse import urlparse

from .config import BLOCS, Config
from .faits import mots
from .modeles import Article

BORDS = ("gauche", "droite")


def repartition(media_ids: list[str], config: Config) -> dict[str, list[str]]:
    """Médias distincts ayant couvert le sujet, rangés par bloc."""
    blocs: dict[str, list[str]] = {b: [] for b in BLOCS}
    for media_id in dict.fromkeys(media_ids):
        blocs[config.bloc(media_id)].append(media_id)
    return blocs


def effectifs(media_ids, config: Config) -> dict[str, int]:
    """Nombre de médias de chaque bord parmi ceux donnés (ceux qui ont publié dans la fenêtre)."""
    bords = [config.bord(m) for m in set(media_ids)]
    return {b: bords.count(b) for b in BORDS}


def est_sport(articles: list[Article], reglage: dict) -> bool:
    """Vrai si le sujet relève de la rubrique sportive, d'après l'adresse de ses articles."""
    rubriques = set(reglage["rubriques_sport"])
    sportifs = sum(1 for a in articles if rubriques & set(urlparse(a.url).path.lower().split("/")))
    return bool(articles) and sportifs / len(articles) >= reglage["part_sport"]


def depeches(articles: list[Article], seuil: float) -> set[str]:
    """Identifiants des articles dont le titre est repris presque tel quel par un autre média.

    Deux médias qui publient le même titre reprennent en général la même dépêche d'agence.
    On ne sait pas lequel l'a écrite : les deux sont écartés.
    """
    titres = [(a, mots(a.titre)) for a in articles]
    repris = set()
    for a, ta in titres:
        for b, tb in titres:
            if a.media_id != b.media_id and ta and len(ta & tb) / len(ta | tb) >= seuil:
                repris.add(a.id)
                break
    return repris


def asymetrie(articles: list[Article], effectif: dict[str, int], config: Config) -> dict:
    """Écart de couverture d'un sujet entre les médias de gauche et ceux de droite.

    Pour chaque bord : la part de ses médias qui couvrent le sujet (`effectif` donne le
    nombre de médias du bord ayant publié ce jour-là). `ecart` = part à gauche − part à
    droite, entre −1 et 1. Comparer des parts plutôt que des nombres neutralise le
    déséquilibre d'effectif entre les deux bords. Un média ne compte qu'une fois, et
    seulement s'il publie autre chose qu'une dépêche reprise (`depeches`).

    `ecarte` : "sport" si le sujet n'est pas classé. `notable` : l'écart dépasse le bruit
    (voir couverture.asymetrie dans reglages.yaml).
    """
    reglage = config.reglages["couverture"]["asymetrie"]
    reprises = depeches(articles, reglage["ecarter"]["titre_repris"])
    tous = list(dict.fromkeys(a.media_id for a in articles))
    propres = list(dict.fromkeys(a.media_id for a in articles if a.id not in reprises))
    couvrent = {b: [m for m in propres if config.bord(m) == b] for b in BORDS}
    seulement_depeche = {b: [m for m in tous if m not in propres and config.bord(m) == b] for b in BORDS}
    part = {b: len(couvrent[b]) / effectif[b] if effectif.get(b) else 0.0 for b in BORDS}
    ecart = part["gauche"] - part["droite"]
    dominant = "gauche" if ecart > 0 else "droite" if ecart < 0 else None
    ecarte = "sport" if est_sport(articles, reglage["ecarter"]) else None
    notable = (
        ecarte is None
        and dominant is not None
        and abs(ecart) >= reglage["ecart_min"] - 1e-9
        and len(couvrent[dominant]) >= reglage["min_medias_bord"]
    )
    return {
        **{
            b: {"medias": couvrent[b], "depeche": seulement_depeche[b], "total": effectif.get(b, 0), "part": round(part[b], 3)}
            for b in BORDS
        },
        "ecart": round(ecart, 3),
        "bord_dominant": dominant,
        "ecarte": ecarte,
        "notable": notable,
    }
