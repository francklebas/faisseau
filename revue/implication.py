"""Implication textuelle : le texte d'une source (titre et extrait) affirme-t-il un fait ?

Modèle multilingue exécuté en local sur CPU. Plus lent qu'une proximité de vecteurs, il
n'est appelé que pour les faits candidats au niveau « commun » (voir faits.verifier).
"""

from __future__ import annotations

from typing import Any


class Juge:
    """Charge le modèle à la première utilisation."""

    def __init__(self, nom: str, seuil: float = 0.5, fils_cpu: int = 4, lot: int = 16) -> None:
        self.nom = nom
        self.seuil = seuil
        self.fils_cpu = fils_cpu
        self.lot = lot
        self._modele: Any = None
        self._jetons: Any = None
        self._indice = 0

    def scores(self, paires: list[tuple[str, str]]) -> list[float]:
        """Pour chaque (texte de la source, fait), probabilité que le texte implique le fait."""
        if not paires:
            return []
        import torch

        if self._modele is None:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            torch.set_num_threads(self.fils_cpu)
            self._jetons = AutoTokenizer.from_pretrained(self.nom)
            self._modele = AutoModelForSequenceClassification.from_pretrained(self.nom).eval()
            self._indice = {v.lower(): k for k, v in self._modele.config.id2label.items()}["entailment"]
        resultats: list[float] = []
        for debut in range(0, len(paires), self.lot):
            lot = paires[debut : debut + self.lot]
            entrees = self._jetons([p for p, _ in lot], [f for _, f in lot], padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.no_grad():
                probabilites = torch.softmax(self._modele(**entrees).logits, dim=-1)
            resultats += probabilites[:, self._indice].tolist()
        return resultats

    def affirme(self, paires: list[tuple[str, str]]) -> list[bool]:
        return [s >= self.seuil for s in self.scores(paires)]


def juge_depuis(config) -> Juge | None:
    reglage = config.reglages["faits"].get("implication")
    if not reglage:
        return None
    return Juge(reglage["modele"], reglage.get("seuil", 0.5), config.reglages["embeddings"]["fils_cpu"])
