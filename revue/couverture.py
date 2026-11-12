"""Répartition de la couverture par bloc (gauche, centre, droite) et angles morts."""

from __future__ import annotations

from .config import BLOCS, Config

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


def asymetrie(media_ids: list[str], effectif: dict[str, int], config: Config) -> dict:
    """Écart de couverture d'un sujet entre les médias de gauche et ceux de droite.

    Pour chaque bord : la part de ses médias qui couvrent le sujet (`effectif` donne le
    nombre de médias du bord ayant publié ce jour-là). `ecart` = part à gauche − part à
    droite, entre −1 et 1. Comparer des parts plutôt que des nombres neutralise le
    déséquilibre d'effectif entre les deux bords. Un média ne compte qu'une fois.

    `notable` : l'écart dépasse le bruit (voir couverture.asymetrie dans reglages.yaml).
    """
    reglage = config.reglages["couverture"]["asymetrie"]
    couvrent = {b: [m for m in dict.fromkeys(media_ids) if config.bord(m) == b] for b in BORDS}
    part = {b: len(couvrent[b]) / effectif[b] if effectif.get(b) else 0.0 for b in BORDS}
    ecart = part["gauche"] - part["droite"]
    dominant = "gauche" if ecart > 0 else "droite" if ecart < 0 else None
    notable = (
        dominant is not None
        and abs(ecart) >= reglage["ecart_min"] - 1e-9
        and len(couvrent[dominant]) >= reglage["min_medias_bord"]
    )
    return {
        **{b: {"medias": couvrent[b], "total": effectif.get(b, 0), "part": round(part[b], 3)} for b in BORDS},
        "ecart": round(ecart, 3),
        "bord_dominant": dominant,
        "notable": notable,
    }
