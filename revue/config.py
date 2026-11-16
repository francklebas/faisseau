"""Chargement de la configuration (config/reglages.yaml, config/medias.yaml, .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ORIENTATIONS = (
    "extreme-gauche",
    "gauche",
    "centre-gauche",
    "centre",
    "centre-droit",
    "droite",
    "extreme-droite",
)
BLOCS = ("gauche", "centre-gauche", "centre", "centre-droit", "droite")
BORDS = ("gauche", "droite")  # les deux blocs comparés dans la mesure d'asymétrie
STATUTS = ("a_valider", "valide")
TYPES_SOURCE = ("ligne_revendiquee", "propriete", "etude", "presse", "audience")
VERDICTS = ("confirme", "contredit", "ne tranche pas")


def racine() -> Path:
    """Racine du dépôt (surcharge : REVUE_RACINE)."""
    return Path(os.environ.get("REVUE_RACINE", Path(__file__).resolve().parent.parent))


@dataclass(frozen=True)
class Media:
    id: str
    nom: str
    site: str
    flux: tuple[str, ...]
    orientation: str
    justification: str
    statut: str = "a_valider"
    actif: bool = True
    note: str = ""
    sources: tuple[dict, ...] = ()  # sources externes sur la ligne éditoriale
    audience: dict | None = None  # orientation du public : information, jamais un critère


@dataclass
class Config:
    reglages: dict[str, Any]
    medias: dict[str, Media]
    racine: Path = field(default_factory=racine)

    # ── chemins ──
    @property
    def dossier_donnees(self) -> Path:
        return Path(os.environ.get("REVUE_DONNEES", self.racine / "data"))

    @property
    def base(self) -> Path:
        return self.dossier_donnees / "revue.db"

    @property
    def dossier_editions(self) -> Path:
        return self.dossier_donnees / "editions"

    # ── médias ──
    @property
    def medias_actifs(self) -> list[Media]:
        return [m for m in self.medias.values() if m.actif]

    def bloc(self, media_id: str) -> str:
        """Bloc d'un média (un des cinq de BLOCS), d'après reglages.yaml."""
        orientation = self.medias[media_id].orientation
        for bloc, orientations in self.reglages["couverture"]["blocs"].items():
            if orientation in orientations:
                return bloc
        raise ValueError(f"orientation « {orientation} » absente de couverture.blocs")

    def bord(self, media_id: str) -> str | None:
        """Bord (gauche, droite) d'un média pour la mesure d'asymétrie, None s'il est au milieu."""
        bloc = self.bloc(media_id)
        return bloc if bloc in BORDS else None

    # ── embeddings ──
    @property
    def modele_embeddings(self) -> dict[str, Any]:
        e = self.reglages["embeddings"]
        cle = os.environ.get("REVUE_EMBEDDINGS", e["modele"])
        if cle not in e["modeles"]:
            raise ValueError(f"modèle d'embeddings inconnu : {cle} (voir reglages.yaml)")
        return {"cle": cle, **e["modeles"][cle]}

    @property
    def fils_cpu(self) -> int:
        """Fils PyTorch pour les modèles locaux (surcharge : REVUE_FILS_CPU, utile sur un runner)."""
        valeur = os.environ.get("REVUE_FILS_CPU", self.reglages["embeddings"]["fils_cpu"])
        try:
            fils = int(valeur)
        except (TypeError, ValueError):
            raise ValueError(f"REVUE_FILS_CPU doit être un entier positif, pas « {valeur} »") from None
        if fils < 1:
            raise ValueError(f"REVUE_FILS_CPU doit être un entier positif, pas « {valeur} »")
        return fils

    # ── LLM ──
    @property
    def fournisseur_llm(self) -> str:
        return os.environ.get("REVUE_LLM", self.reglages["faits"]["fournisseur"])


def charger_env(chemin: Path) -> None:
    """Lit un fichier .env minimal (CLE=valeur) sans écraser l'environnement."""
    if not chemin.exists():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip().strip("\"'"))


def lire_medias(chemin: Path) -> dict[str, Media]:
    brut = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    medias: dict[str, Media] = {}
    for entree in brut["medias"]:
        flux = entree["flux"]
        media = Media(
            id=entree["id"],
            nom=entree["nom"],
            site=entree["site"],
            flux=tuple([flux] if isinstance(flux, str) else flux),
            orientation=entree["orientation"],
            justification=entree["justification"].strip(),
            statut=entree.get("statut", "a_valider"),
            actif=entree.get("actif", True),
            note=(entree.get("note") or "").strip(),
            sources=tuple(entree.get("sources") or ()),
            audience=entree.get("audience"),
        )
        if media.id in medias:
            raise ValueError(f"médias en double : {media.id}")
        if media.orientation not in ORIENTATIONS:
            raise ValueError(f"{media.id} : orientation inconnue « {media.orientation} »")
        if media.statut not in STATUTS:
            raise ValueError(f"{media.id} : statut inconnu « {media.statut} »")
        if not media.justification:
            raise ValueError(f"{media.id} : justification manquante")
        for source in media.sources:
            if not str(source.get("url", "")).startswith("https://") or not source.get("citation"):
                raise ValueError(f"{media.id} : source sans lien https ou sans citation")
            if source.get("type") not in TYPES_SOURCE or source.get("verdict") not in VERDICTS:
                raise ValueError(f"{media.id} : type ou verdict de source inconnu ({source.get('url')})")
            if source["verdict"] == "contredit" and not source.get("note"):
                raise ValueError(f"{media.id} : une source qui contredit doit dire en quoi (note)")
            # Wikipédia est un point d'entrée vers d'autres sources, pas une preuve.
            if "wikipedia.org" in source["url"] and source["verdict"] != "ne tranche pas":
                raise ValueError(f"{media.id} : Wikipédia ne peut ni confirmer ni contredire un classement")
        medias[media.id] = media
    return medias


def charger(racine_depot: Path | None = None) -> Config:
    base = racine_depot or racine()
    charger_env(base / ".env")
    reglages = yaml.safe_load((base / "config" / "reglages.yaml").read_text(encoding="utf-8"))
    medias = lire_medias(base / "config" / "medias.yaml")
    return Config(reglages=reglages, medias=medias, racine=base)
