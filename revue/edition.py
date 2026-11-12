"""Assemblage d'une édition : sujets, faits, couverture → JSON lu par le site statique."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import BLOCS, Config
from .couverture import asymetrie, repartition
from .modeles import Sujet

PARIS = ZoneInfo("Europe/Paris")


def slug(texte: str, suffixe: str) -> str:
    plat = unicodedata.normalize("NFKD", re.sub(r"[’'‘]", " ", texte.lower())).encode("ascii", "ignore").decode()
    mots = re.sub(r"[^a-z0-9]+", "-", plat).strip("-")[:60].rstrip("-")
    return f"{mots}-{suffixe[:6]}" if mots else suffixe


def sujet_en_json(sujet: Sujet, config: Config, effectif: dict[str, int]) -> dict:
    extraction = sujet.extraction
    articles = [a for a in sujet.articles if a.id not in extraction.hors_sujet]
    blocs = repartition([a.media_id for a in articles], config)
    numero = {a.id: i for i, a in enumerate(articles, 1)}
    faits: dict[str, list[dict]] = {"commun": [], "recoupe": [], "isole": []}
    for fait in extraction.faits:
        sources = [numero[i] for i in fait.article_ids if i in numero]
        if sources:
            faits[fait.statut].append({"texte": fait.texte, "medias": fait.medias, "sources": sources})
    return {
        "id": sujet.signature,
        "slug": slug(extraction.titre, sujet.signature),
        "titre": extraction.titre,
        "titre_origine": "article" if extraction.titre == sujet.articles[0].titre else "synthese",
        "extraction": extraction.etat,
        "nb_articles": len(articles),
        "nb_medias": sum(len(m) for m in blocs.values()),
        "couverture": {b: blocs[b] for b in BLOCS},
        "asymetrie": asymetrie([a.media_id for a in articles], effectif, config),
        "faits_communs": faits["commun"],
        "faits_recoupes": faits["recoupe"],
        "affirmations_isolees": faits["isole"],
        "premiere_publication": min(a.publie_le for a in articles).isoformat(),
        "derniere_publication": max(a.publie_le for a in articles).isoformat(),
        # Les articles : titre et lien uniquement. Le numéro sert de renvoi depuis les faits.
        "articles": [
            {"n": numero[a.id], "media": a.media_id, "titre": a.titre, "url": a.url, "publie_le": a.publie_le.isoformat()}
            for a in articles
        ],
    }


def medias_en_json(config: Config) -> list[dict]:
    return [
        {
            "id": m.id,
            "nom": m.nom,
            "site": m.site,
            "orientation": m.orientation,
            "bloc": config.bloc(m.id),
            "justification": m.justification,
            "note": m.note,
            "statut": m.statut,
            "actif": m.actif,
            "sources": [{"url": s["url"], "type": s["type"], "titre": s["titre"]} for s in m.sources],
        }
        for m in config.medias.values()
    ]


def ecrire_edition(
    sujets: list[Sujet], config: Config, stats: dict, effectif: dict[str, int], maintenant: datetime | None = None
) -> Path:
    """Écrit data/editions/AAAA-MM-JJ.json et met à jour l'index des éditions."""
    maintenant = (maintenant or datetime.now(PARIS)).astimezone(PARIS)
    date = maintenant.date().isoformat()
    min_medias = config.reglages["regroupement"]["min_medias"]
    publies = [s for s in (sujet_en_json(s, config, effectif) for s in sujets) if s["nb_medias"] >= min_medias]
    publies.sort(key=lambda s: (-s["nb_medias"], -s["nb_articles"], s["id"]))
    edition = {
        "date": date,
        "genere_le": maintenant.isoformat(timespec="seconds"),
        "stats": {
            **stats,
            "nb_sujets": len(publies),
            "nb_asymetries": sum(1 for s in publies if s["asymetrie"]["notable"]),
            "effectif_bords": effectif,
        },
        "sujets": publies,
        "medias": medias_en_json(config),
    }
    dossier = config.dossier_editions
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{date}.json"
    chemin.write_text(json.dumps(edition, ensure_ascii=False, indent=1), encoding="utf-8")

    index = []
    for fichier in sorted(dossier.glob("????-??-??.json"), reverse=True):
        e = json.loads(fichier.read_text(encoding="utf-8"))
        index.append({"date": e["date"], "genere_le": e["genere_le"], "nb_sujets": len(e["sujets"])})
    (dossier / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin
