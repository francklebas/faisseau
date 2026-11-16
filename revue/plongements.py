"""Embeddings calculés en local sur CPU (sentence-transformers), avec cache en base."""

from __future__ import annotations

from typing import Any

import numpy as np

from .base import Base
from .modeles import Article


class Encodeur:
    """Charge le modèle à la première utilisation (le chargement prend quelques secondes)."""

    def __init__(self, nom: str, prefixe: str = "", fils_cpu: int = 4, lot: int = 32) -> None:
        self.nom = nom
        self.prefixe = prefixe
        self.fils_cpu = fils_cpu
        self.lot = lot
        self._modele: Any = None

    def encoder(self, textes: list[str]) -> np.ndarray:
        """Vecteurs normalisés (le produit scalaire vaut la similarité cosinus)."""
        if self._modele is None:
            import torch
            from sentence_transformers import SentenceTransformer

            torch.set_num_threads(self.fils_cpu)
            self._modele = SentenceTransformer(self.nom, device="cpu")
        vecteurs = self._modele.encode(
            [self.prefixe + t for t in textes],
            batch_size=self.lot,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vecteurs, dtype=np.float32)


def encodeur_depuis(config) -> Encodeur:
    m = config.modele_embeddings
    e = config.reglages["embeddings"]
    return Encodeur(m["nom"], m.get("prefixe", ""), config.fils_cpu, e["lot"])


def vecteurs_articles(base: Base, encodeur: Encodeur, articles: list[Article]) -> np.ndarray:
    """Matrice (n, d) alignée sur `articles` ; seuls les articles nouveaux sont encodés."""
    connus = base.vecteurs([a.id for a in articles], encodeur.nom)
    manquants = [a for a in articles if a.id not in connus]
    if manquants:
        nouveaux = encodeur.encoder([a.texte for a in manquants])
        ajout = {a.id: v for a, v in zip(manquants, nouveaux)}
        base.enregistrer_vecteurs(encodeur.nom, ajout)
        connus.update(ajout)
    return np.vstack([connus[a.id] for a in articles]) if articles else np.zeros((0, 1), dtype=np.float32)
