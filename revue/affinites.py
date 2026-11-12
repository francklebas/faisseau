"""Contrôle du classement des médias par leur couverture : qui traite les mêmes sujets que qui ?

Ce n'est pas un classement. Deux médias qui couvrent les mêmes sujets ne partagent pas pour
autant une ligne : un quotidien généraliste et une chaîne d'information se ressemblent parce
qu'ils suivent tous deux l'agenda du jour. Le module signale seulement les médias dont le
comportement s'écarte de celui de leur bloc déclaré, pour inviter à relire leur fiche dans
config/medias.yaml. Il ne modifie rien.

Données : data/couvertures/AAAA-MM-JJ.json, écrit à chaque édition, qui liste tous les sujets
du jour (pas seulement ceux publiés) avec les médias qui les couvrent.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from .config import BLOCS, Config
from .modeles import Sujet


def ecrire_couvertures(sujets: list[Sujet], config: Config, date: str) -> Path:
    """Archive, pour une édition, les médias qui couvrent chaque sujet du jour."""
    dossier = config.dossier_donnees / "couvertures"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{date}.json"
    contenu = {
        "date": date,
        "sujets": [{"id": s.signature, "titre": s.articles[0].titre, "medias": s.medias} for s in sujets],
    }
    chemin.write_text(json.dumps(contenu, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin


def lire_couvertures(dossier: Path) -> tuple[int, dict[str, set[str]]]:
    """Renvoie (nombre d'éditions, sujets couverts par chaque média).

    Un même sujet suivi deux jours de suite garde sa signature tant que ses articles ne
    changent pas : il n'est compté qu'une fois.
    """
    par_media: dict[str, set[str]] = {}
    fichiers = sorted(dossier.glob("????-??-??.json")) if dossier.exists() else []
    for fichier in fichiers:
        for sujet in json.loads(fichier.read_text(encoding="utf-8"))["sujets"]:
            for media in sujet["medias"]:
                par_media.setdefault(media, set()).add(sujet["id"])
    return len(fichiers), par_media


def proximite(a: set[str], b: set[str]) -> float:
    """Cosinus entre deux ensembles de sujets : 1 si identiques, 0 si disjoints.

    Le cosinus pénalise moins qu'un indice de Jaccard l'écart de taille entre un média qui
    publie beaucoup et un média qui publie peu.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


@dataclass
class Profil:
    media: str
    bloc: str  # bloc déclaré (config)
    nb_sujets: int
    par_bloc: dict[str, float]  # proximité moyenne avec les médias de chaque bloc
    voisins: list[tuple[str, float]] = field(default_factory=list)  # médias les plus proches

    @property
    def bloc_proche(self) -> str:
        return max(self.par_bloc, key=lambda b: self.par_bloc[b])

    def ecart(self) -> float:
        """Avance du bloc le plus proche sur le bloc déclaré (0 si c'est le même)."""
        return self.par_bloc[self.bloc_proche] - self.par_bloc[self.bloc]


@dataclass
class Rapport:
    nb_editions: int
    profils: list[Profil]
    ignores: list[tuple[str, int]]  # médias écartés faute de sujets (identifiant, nombre)
    signales: list[Profil]
    concluant: bool  # assez d'éditions pour que les signalements méritent une relecture


def analyser(nb_editions: int, par_media: dict[str, set[str]], config: Config) -> Rapport:
    reglage = config.reglages["affinites"]
    connus = {m: s for m, s in par_media.items() if m in config.medias}
    retenus = {m: s for m, s in connus.items() if len(s) >= reglage["min_sujets"]}
    ignores = sorted(((m, len(s)) for m, s in connus.items() if m not in retenus), key=lambda x: -x[1])

    profils = []
    for media, sujets in retenus.items():
        autres = {m: proximite(sujets, s) for m, s in retenus.items() if m != media}
        par_bloc = {}
        for bloc in BLOCS:
            valeurs = [p for m, p in autres.items() if config.bloc(m) == bloc]
            par_bloc[bloc] = sum(valeurs) / len(valeurs) if valeurs else 0.0
        voisins = sorted(autres.items(), key=lambda x: -x[1])[:3]
        profils.append(Profil(media, config.bloc(media), len(sujets), par_bloc, voisins))
    profils.sort(key=lambda p: (BLOCS.index(p.bloc), p.media))

    signales = sorted((p for p in profils if p.ecart() >= reglage["marge"]), key=lambda p: -p.ecart())
    return Rapport(nb_editions, profils, ignores, signales, nb_editions >= reglage["min_editions"])


def en_markdown(rapport: Rapport, config: Config) -> str:
    reglage = config.reglages["affinites"]
    nom = lambda m: config.medias[m].nom  # noqa: E731
    lignes = [
        "# Couverture comparée des médias",
        "",
        f"{rapport.nb_editions} édition(s) analysée(s), {len(rapport.profils)} médias avec au moins "
        f"{reglage['min_sujets']} sujets.",
        "",
        "Ce tableau n'est pas un classement. Il mesure quels médias couvrent les mêmes sujets, pas ce "
        "qu'ils en disent. Il sert à repérer les fiches de `config/medias.yaml` à relire.",
        "",
    ]
    if not rapport.concluant:
        lignes += [
            f"**Historique insuffisant** : {rapport.nb_editions} édition(s), il en faut {reglage['min_editions']} "
            "pour que les signalements méritent une relecture. Les chiffres ci-dessous sont donnés pour "
            "vérifier le calcul ; n'en tirer aucune conclusion.",
            "",
        ]
    titre = "Médias à relire" if rapport.concluant else "Écarts observés (non concluants)"
    lignes += [f"## {titre}", ""]
    if rapport.signales:
        lignes += ["| Média | Bloc déclaré | Bloc le plus proche | Avance | Sujets |", "|---|---|---|---|---|"]
        for p in rapport.signales:
            lignes.append(f"| {nom(p.media)} | {p.bloc} | {p.bloc_proche} | {p.ecart():.2f} | {p.nb_sujets} |")
    else:
        lignes.append(f"Aucun média ne s'écarte de son bloc de plus de {reglage['marge']}.")
    lignes += [
        "",
        "## Tous les médias",
        "",
        "Proximité moyenne (0 à 1) avec les médias de chaque bloc, le média lui-même exclu.",
        "",
        "| Média | Bloc déclaré | Sujets | " + " | ".join(BLOCS) + " | Plus proches |",
        "|---|---|---|" + "---|" * len(BLOCS) + "---|",
    ]
    for p in rapport.profils:
        voisins = ", ".join(f"{nom(m)} ({v:.2f})" for m, v in p.voisins)
        parts = " | ".join(f"{p.par_bloc[b]:.2f}" for b in BLOCS)
        lignes.append(f"| {nom(p.media)} | {p.bloc} | {p.nb_sujets} | {parts} | {voisins} |")
    if rapport.ignores:
        lignes += ["", "Trop peu de sujets pour être comparés : " + ", ".join(f"{nom(m)} ({n})" for m, n in rapport.ignores) + "."]
    return "\n".join(lignes) + "\n"
