"""Compare les modèles d'embeddings sur un échantillon réel de titres de presse.

Vérité terrain : tests/donnees/titres_etiquetes.json (titres relevés dans les flux et
rangés à la main par sujet). Pour chaque modèle déclaré dans config/reglages.yaml :

  - vitesse (chargement, encodage) sur ce processeur ;
  - séparation des paires « même sujet » / « sujets différents » (AUC) ;
  - qualité du regroupement (précision, rappel, F1 sur les paires) selon le seuil,
    pour repérer le meilleur seuil et vérifier celui qui est configuré ; si une base
    locale existe, les autres articles du jour sont mêlés à l'échantillon (distracteurs) ;
  - si une base locale existe : nombre de sujets obtenus sur la collecte du jour.

Usage :
    uv run python scripts/comparer_embeddings.py [--avec-extraits] [--modeles solon e5-small]

--avec-extraits : ajoute au titre l'extrait RSS présent dans la base locale (c'est ce que
fait le pipeline). Sans cette option, ou sans base, seuls les titres sont comparés.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from itertools import combinations

import numpy as np
from sklearn.metrics import roc_auc_score

from revue import config as configuration
from revue.base import Base
from revue.plongements import Encodeur
from revue.regroupement import construire_sujets, regrouper


def charger_verite(chemin) -> tuple[list[str], list[str], list[str | None]]:
    """Renvoie (titres, sujet de chaque titre, famille de chaque titre)."""
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    titres, sujets, familles = [], [], []
    for sujet in donnees["sujets"]:
        for t in sujet["titres"]:
            titres.append(t["titre"])
            sujets.append(sujet["id"])
            familles.append(sujet.get("famille"))
    return titres, sujets, familles


def paires_evaluees(sujets: list[str], familles: list[str | None]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Indices (i, j) des paires notées et leur étiquette (1 = même sujet).

    Les paires de sujets différents mais de même famille sont écartées : les fusionner ou
    les séparer se défend dans les deux cas.
    """
    gauche, droite, etiquettes = [], [], []
    for i, j in combinations(range(len(sujets)), 2):
        meme = sujets[i] == sujets[j]
        if not meme and familles[i] and familles[i] == familles[j]:
            continue
        gauche.append(i)
        droite.append(j)
        etiquettes.append(int(meme))
    return np.array(gauche), np.array(droite), np.array(etiquettes)


def score_regroupement(groupes: list[list[int]], n: int, i: np.ndarray, j: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    appartenance = np.empty(n, dtype=int)
    for numero, groupe in enumerate(groupes):
        appartenance[groupe] = numero
    predit = appartenance[i] == appartenance[j]
    vrais = int((predit & (y == 1)).sum())
    precision = vrais / max(int(predit.sum()), 1)
    rappel = vrais / max(int((y == 1).sum()), 1)
    f1 = 2 * precision * rappel / max(precision + rappel, 1e-9)
    return precision, rappel, f1


def evaluer(cle: str, reglage: dict, textes: list[str], sujets, familles, cfg, distracteurs: list[str], base: Base | None) -> list[str]:
    lignes = [f"## {cle} — `{reglage['nom']}`", ""]
    e = cfg.reglages["embeddings"]
    encodeur = Encodeur(reglage["nom"], reglage.get("prefixe", ""), cfg.fils_cpu, e["lot"])
    t0 = time.perf_counter()
    encodeur.encoder(["mise en route"])
    chargement = time.perf_counter() - t0
    t0 = time.perf_counter()
    vecteurs = encodeur.encoder(textes)
    encodage = time.perf_counter() - t0
    # Les distracteurs (autres articles du jour) rendent l'exercice réaliste : un seuil trop
    # bas soude alors deux sujets voisins par l'intermédiaire d'articles tiers.
    ensemble = np.vstack([vecteurs, encodeur.encoder(distracteurs)]) if distracteurs else vecteurs
    lignes += [
        f"- Dimension : {vecteurs.shape[1]} ; chargement : {chargement:.1f} s ; "
        f"encodage : {len(textes) / encodage:.0f} textes/s ({cfg.fils_cpu} fils CPU)",
    ]

    i, j, y = paires_evaluees(sujets, familles)
    similarites = np.einsum("ij,ij->i", vecteurs[i], vecteurs[j])
    lignes += [
        f"- Paires notées : {len(y)} dont {int(y.sum())} « même sujet » ; {len(distracteurs)} autres articles mêlés comme distracteurs",
        f"- AUC (séparation des paires) : **{roc_auc_score(y, similarites):.4f}**",
        f"- Similarité médiane : même sujet {np.median(similarites[y == 1]):.3f}, "
        f"sujets différents {np.median(similarites[y == 0]):.3f}",
        "",
        "| liaison | seuil | précision | rappel | F1 | groupes |",
        "|---|---|---|---|---|---|",
    ]
    haut, fond = float(np.median(similarites[y == 1])), float(np.median(similarites[y == 0]))
    grille = sorted({round(float(s), 2) for s in np.linspace(fond + 0.35 * (haut - fond), haut, 10)} | {reglage["seuil"]})
    meilleur = (0.0, "", 0.0)
    for liaison in ("average", "complete"):
        for seuil in grille:
            groupes = regrouper(ensemble, seuil, liaison)
            p, r, f1 = score_regroupement(groupes, len(ensemble), i, j, y)
            marque = " ← configuré" if seuil == reglage["seuil"] and liaison == cfg.reglages["regroupement"]["liaison"] else ""
            lignes.append(f"| {liaison} | {seuil:.2f}{marque} | {p:.3f} | {r:.3f} | {f1:.3f} | {len(groupes)} |")
            if f1 > meilleur[0]:
                meilleur = (f1, liaison, seuil)
    lignes += ["", f"Meilleur F1 : **{meilleur[0]:.3f}** ({meilleur[1]}, seuil {meilleur[2]:.2f}) ; {len(set(sujets))} sujets dans la vérité terrain.", ""]

    if base is not None:
        r = cfg.reglages
        debut = datetime.now(timezone.utc) - timedelta(hours=r["collecte"]["fenetre_heures"])
        articles = base.articles_depuis(debut, medias={m.id for m in cfg.medias_actifs})
        if articles:
            from revue.plongements import vecteurs_articles

            t0 = time.perf_counter()
            matrice = vecteurs_articles(base, encodeur, articles)
            duree = time.perf_counter() - t0
            sujets_jour = construire_sujets(
                articles, matrice, reglage["seuil"], r["regroupement"]["liaison"], r["regroupement"]["min_medias"]
            )
            lignes += [
                f"Collecte locale : {len(articles)} articles → **{len(sujets_jour)} sujets** d'au moins "
                f"{r['regroupement']['min_medias']} médias au seuil configuré ({duree:.0f} s, cache compris).",
                "",
            ]
    return lignes


def main() -> None:
    analyse = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyse.add_argument("--modeles", nargs="*", help="clés de embeddings.modeles (défaut : toutes)")
    analyse.add_argument("--avec-extraits", action="store_true", help="titre + extrait RSS de la base locale")
    analyse.add_argument("--distracteurs", type=int, default=1500, help="nombre maximal d'articles de la base mêlés à l'échantillon")
    options = analyse.parse_args()

    cfg = configuration.charger()
    titres, sujets, familles = charger_verite(cfg.racine / "tests" / "donnees" / "titres_etiquetes.json")
    base = Base(cfg.base) if cfg.base.exists() else None

    textes, mode, distracteurs = titres, "titres seuls", []
    if base is not None:
        connus = dict(base.cx.execute("SELECT titre, extrait FROM articles"))
        autres = [(t, e) for t, e in connus.items() if t not in set(titres)][: options.distracteurs]
        distracteurs = [t for t, _ in autres]
        if options.avec_extraits:
            textes = [f"{t}. {connus[t]}" if connus.get(t) else t for t in titres]
            distracteurs = [f"{t}. {e}" if e else t for t, e in autres]
            trouves = sum(1 for t in titres if connus.get(t))
            mode = f"titres + extraits RSS ({trouves}/{len(titres)} extraits retrouvés dans la base locale)"

    rapport = [
        "# Comparaison des modèles d'embeddings",
        "",
        f"Généré le {datetime.now():%Y-%m-%d %H:%M}. Échantillon : {len(titres)} titres réels, "
        f"{len(set(sujets))} sujets étiquetés à la main. Textes comparés : {mode}.",
        "",
    ]
    modeles = cfg.reglages["embeddings"]["modeles"]
    for cle in options.modeles or list(modeles):
        rapport += evaluer(cle, modeles[cle], textes, sujets, familles, cfg, distracteurs, base)

    texte = "\n".join(rapport)
    print(texte)
    sortie = cfg.dossier_donnees / "comparaison_embeddings.md"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(texte + "\n", encoding="utf-8")
    print(f"\nRapport écrit dans {sortie}")


if __name__ == "__main__":
    main()
