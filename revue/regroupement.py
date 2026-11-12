"""Regroupement des articles par sujet à partir de leurs embeddings."""

from __future__ import annotations

import hashlib
from collections import defaultdict

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from .modeles import Article, Sujet


def regrouper(vecteurs: np.ndarray, seuil: float, liaison: str = "average") -> list[list[int]]:
    """Classification ascendante hiérarchique sur la distance cosinus.

    Deux groupes ne fusionnent que si leur similarité (moyenne des paires pour `average`,
    pire paire pour `complete`) atteint `seuil`. Contrairement à un seuil sur le plus proche
    voisin, cela évite les chaînes A~B~C qui finissent par souder deux sujets voisins.
    Renvoie les groupes d'indices, du plus grand au plus petit.
    """
    n = len(vecteurs)
    if n == 0:
        return []
    if n == 1:
        return [[0]]
    etiquettes = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage=liaison,
        distance_threshold=1.0 - seuil,
    ).fit_predict(vecteurs)
    groupes: dict[int, list[int]] = defaultdict(list)
    for indice, etiquette in enumerate(etiquettes):
        groupes[int(etiquette)].append(indice)
    return sorted(groupes.values(), key=lambda g: (-len(g), g[0]))


def signature(articles: list[Article]) -> str:
    """Empreinte stable d'un sujet : dépend uniquement des articles qui le composent."""
    return hashlib.sha1("|".join(sorted(a.id for a in articles)).encode()).hexdigest()[:12]


def _limiter_par_media(indices: list[int], articles: list[Article], vecteurs: np.ndarray, maximum: int) -> list[int]:
    """Garde au plus `maximum` articles par média : les plus proches du centre du sujet."""
    centre = vecteurs[indices].mean(axis=0)
    proximite = {i: float(vecteurs[i] @ centre) for i in indices}
    par_media: dict[str, list[int]] = defaultdict(list)
    for i in sorted(indices, key=lambda i: -proximite[i]):
        if len(par_media[articles[i].media_id]) < maximum:
            par_media[articles[i].media_id].append(i)
    gardes = [i for groupe in par_media.values() for i in groupe]
    return sorted(gardes, key=lambda i: -proximite[i])


def construire_sujets(
    articles: list[Article],
    vecteurs: np.ndarray,
    seuil: float,
    liaison: str = "average",
    min_medias: int = 3,
    max_sujets: int | None = None,
    max_articles_par_media: int = 3,
) -> list[Sujet]:
    """Sujets couverts par au moins `min_medias` médias distincts, les plus couverts d'abord.

    Dans chaque sujet, les articles sont triés du plus central au plus périphérique.
    """
    sujets: list[Sujet] = []
    for groupe in regrouper(vecteurs, seuil, liaison):
        if len({articles[i].media_id for i in groupe}) < min_medias:
            continue
        gardes = _limiter_par_media(groupe, articles, vecteurs, max_articles_par_media)
        membres = [articles[i] for i in gardes]
        sujets.append(Sujet(articles=membres, signature=signature(membres)))
    sujets.sort(key=lambda s: (-len(s.medias), -len(s.articles), s.signature))
    return sujets[:max_sujets] if max_sujets else sujets
