"""Compare des façons de décider qu'une phrase de source énonce un fait.

Jeu de référence : tests/donnees/paires_fait_source.json (paires relues à la main).
Pour chaque méthode : faux positifs (phrase acceptée alors qu'elle n'énonce pas le fait)
et faux négatifs (phrase refusée alors qu'elle l'énonce).

Les modèles d'implication sont jugés dans deux conditions, chacune contre les verdicts relus
dans cette condition : la phrase la plus proche seule (« enonce »), puis le titre et l'extrait
entiers de l'article (« enonce_contexte »), qui est ce que fait le pipeline.

    uv run python scripts/comparer_controles.py
    uv run python scripts/comparer_controles.py --implication MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from revue import config as configuration
from revue.faits import propositions
from revue.plongements import encodeur_depuis

RACINE = Path(__file__).resolve().parent.parent


def bilan(nom: str, acceptes: list[bool], verite: list[bool], duree: float | None = None) -> str:
    fp = sum(a and not v for a, v in zip(acceptes, verite))
    fn = sum(v and not a for a, v in zip(acceptes, verite))
    temps = f" | {duree * 1000 / len(verite):.0f} ms/paire" if duree is not None else ""
    return f"{nom:<58} FP {fp:>2}/{verite.count(False)}  FN {fn:>2}/{verite.count(True)}  erreurs {fp + fn:>2}{temps}"


def meilleur_seuil(scores: np.ndarray, verite: list[bool]) -> float:
    """Seuil qui minimise les erreurs sur ce jeu (optimiste : choisi sur les données qu'il juge)."""
    candidats = [s / 100 for s in range(5, 100)]
    return min(candidats, key=lambda s: sum((x >= s) != v for x, v in zip(scores, verite)))


def texte_entier(paire: dict) -> str:
    """Titre et extrait, assemblés comme Article.texte."""
    return f"{paire['titre']}. {paire['extrait']}" if paire["extrait"] else paire["titre"]


def implication(nom: str, premisses: list[str], faits: list[str], fils: int) -> tuple[np.ndarray, np.ndarray]:
    """Probabilités (implication, contradiction) que la prémisse dise le fait (hypothèse)."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.set_num_threads(fils)
    jetons = AutoTokenizer.from_pretrained(nom)
    modele = AutoModelForSequenceClassification.from_pretrained(nom).eval()
    etiquettes = {v.lower(): k for k, v in modele.config.id2label.items()}
    lots = []
    for debut in range(0, len(faits), 16):
        entrees = jetons(premisses[debut : debut + 16], faits[debut : debut + 16], padding=True, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            lots.append(torch.softmax(modele(**entrees).logits, dim=-1).numpy())
    probabilites = np.concatenate(lots)
    return probabilites[:, etiquettes["entailment"]], probabilites[:, etiquettes["contradiction"]]


def main() -> None:
    analyse = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyse.add_argument("--implication", action="append", default=[], help="modèle d'implication textuelle (répétable)")
    options = analyse.parse_args()

    cfg = configuration.charger()
    paires = json.loads((RACINE / "tests/donnees/paires_fait_source.json").read_text(encoding="utf-8"))["paires"]
    verite = [p["enonce"] for p in paires]
    encodeur = encodeur_depuis(cfg)
    print(f"{len(paires)} paires, {verite.count(True)} où la phrase énonce le fait\n")

    entiere = np.array([p["proximite_solon"] for p in paires])
    for seuil in (0.55, 0.65):
        print(bilan(f"proximité phrase entière ≥ {seuil}", list(entiere >= seuil), verite))

    t0 = time.time()
    decoupee = []
    for p in paires:
        morceaux = propositions(p["phrase"])
        v = encodeur.encoder([p["fait"]] + morceaux)
        decoupee.append(float((v[0] @ v[1:].T).max()))
    decoupee = np.array(decoupee)
    duree = time.time() - t0
    for seuil in (0.55, 0.65, 0.75):
        print(bilan(f"proximité par propositions ≥ {seuil}", list(decoupee >= seuil), verite, duree))
    s = meilleur_seuil(decoupee, verite)
    print(bilan(f"proximité par propositions ≥ {s} (meilleur seuil)", list(decoupee >= s), verite))
    s = meilleur_seuil(entiere, verite)
    print(bilan(f"proximité phrase entière ≥ {s} (meilleur seuil)", list(entiere >= s), verite))

    faits = [p["fait"] for p in paires]
    conditions = [
        ("phrase seule", "", [p["phrase"] for p in paires], verite),
        ("titre et extrait", "_contexte", [texte_entier(p) for p in paires], [p["enonce_contexte"] for p in paires]),
    ]
    for nom in options.implication:
        court = nom.split("/")[-1]
        for condition, suffixe, premisses, attendu in conditions:
            t0 = time.time()
            oui, non = implication(nom, premisses, faits, cfg.reglages["embeddings"]["fils_cpu"])
            duree = time.time() - t0
            print(f"\n{court}, {condition} ({attendu.count(True)} paires vraies sur {len(attendu)})")
            print(bilan("implication ≥ 0.5", list(oui >= 0.5), attendu, duree))
            s = meilleur_seuil(oui, attendu)
            print(bilan(f"implication ≥ {s} (meilleur seuil)", list(oui >= s), attendu))
            print(bilan("pas de contradiction (< 0.5)", list(non < 0.5), attendu))
            for p, x in zip(paires, oui):
                p[court + suffixe] = round(float(x), 3)
    sortie = RACINE / "data" / "comparaison_controles.json"
    sortie.write_text(json.dumps(paires, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nScores par paire : {sortie}")


if __name__ == "__main__":
    main()
