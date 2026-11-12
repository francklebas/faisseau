"""Répartition de la couverture par bloc (gauche, centre, droite) et angles morts."""

from __future__ import annotations

from .config import BLOCS, Config

OPPOSE = {"gauche": "droite", "droite": "gauche"}


def repartition(media_ids: list[str], config: Config) -> dict[str, list[str]]:
    """Médias distincts ayant couvert le sujet, rangés par bloc."""
    blocs: dict[str, list[str]] = {b: [] for b in BLOCS}
    for media_id in dict.fromkeys(media_ids):
        blocs[config.bloc(media_id)].append(media_id)
    return blocs


def angle_mort(media_ids: list[str], config: Config) -> dict | None:
    """Sujet couvert surtout par un bord et presque pas par l'autre.

    Renvoie {"bord_dominant", "bord_absent", "part"} ou None. Les parts sont calculées sur
    le nombre de médias distincts, pas d'articles : un média très prolixe ne pèse qu'une fois.
    Les bords sont ceux de couverture.angle_mort.bords, plus étroits que les blocs affichés.
    """
    reglage = config.reglages["couverture"]["angle_mort"]
    medias = list(dict.fromkeys(media_ids))
    if len(medias) < reglage["min_medias"]:
        return None
    bords = [config.bord(m) for m in medias]
    for bord, oppose in OPPOSE.items():
        part = bords.count(bord) / len(medias)
        if part >= reglage["part_dominante"] and bords.count(oppose) / len(medias) <= reglage["part_opposee_max"]:
            return {"bord_dominant": bord, "bord_absent": oppose, "part": round(part, 2)}
    return None
