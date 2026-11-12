"""Stockage SQLite : articles (titre, extrait, lien), vecteurs et extractions en cache."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from .modeles import Article

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    media_id TEXT NOT NULL,
    titre TEXT NOT NULL,
    extrait TEXT NOT NULL,
    url TEXT NOT NULL,
    publie_le TEXT NOT NULL,
    collecte_le TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS articles_date ON articles (publie_le);
CREATE TABLE IF NOT EXISTS vecteurs (
    article_id TEXT NOT NULL,
    modele TEXT NOT NULL,
    vecteur BLOB NOT NULL,
    PRIMARY KEY (article_id, modele)
);
CREATE TABLE IF NOT EXISTS extractions (
    signature TEXT PRIMARY KEY,
    cree_le TEXT NOT NULL,
    reponse TEXT NOT NULL
);
"""


class Base:
    def __init__(self, chemin: Path | str) -> None:
        if chemin != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self.cx = sqlite3.connect(chemin)
        self.cx.executescript(SCHEMA)

    def fermer(self) -> None:
        self.cx.close()

    # ── articles ──
    def ajouter_articles(self, articles: list[Article]) -> int:
        """Insère les articles inconnus ; renvoie le nombre de nouveaux."""
        maintenant = datetime.now(timezone.utc).isoformat()
        avant = self.cx.total_changes
        self.cx.executemany(
            "INSERT OR IGNORE INTO articles VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(a.id, a.media_id, a.titre, a.extrait, a.url, a.publie_le.isoformat(), maintenant) for a in articles],
        )
        self.cx.commit()
        return self.cx.total_changes - avant

    def articles_depuis(self, debut: datetime, fin: datetime | None = None, medias: set[str] | None = None) -> list[Article]:
        fin = fin or datetime.now(timezone.utc)
        lignes = self.cx.execute(
            "SELECT id, media_id, titre, extrait, url, publie_le FROM articles "
            "WHERE publie_le >= ? AND publie_le <= ? ORDER BY publie_le DESC, id",
            (debut.isoformat(), fin.isoformat()),
        ).fetchall()
        articles = [Article(i, m, t, e, u, datetime.fromisoformat(p)) for i, m, t, e, u, p in lignes]
        return [a for a in articles if medias is None or a.media_id in medias]

    def purger(self, jours: int) -> int:
        limite = (datetime.now(timezone.utc) - timedelta(days=jours)).isoformat()
        avant = self.cx.total_changes
        self.cx.execute("DELETE FROM articles WHERE publie_le < ?", (limite,))
        self.cx.execute("DELETE FROM vecteurs WHERE article_id NOT IN (SELECT id FROM articles)")
        self.cx.execute("DELETE FROM extractions WHERE cree_le < ?", (limite,))
        self.cx.commit()
        return self.cx.total_changes - avant

    # ── vecteurs ──
    def vecteurs(self, ids: list[str], modele: str) -> dict[str, np.ndarray]:
        trouves: dict[str, np.ndarray] = {}
        for debut in range(0, len(ids), 500):
            lot = ids[debut : debut + 500]
            marques = ",".join("?" * len(lot))
            for article_id, blob in self.cx.execute(
                f"SELECT article_id, vecteur FROM vecteurs WHERE modele = ? AND article_id IN ({marques})",
                (modele, *lot),
            ):
                trouves[article_id] = np.frombuffer(blob, dtype=np.float32)
        return trouves

    def enregistrer_vecteurs(self, modele: str, vecteurs: dict[str, np.ndarray]) -> None:
        self.cx.executemany(
            "INSERT OR REPLACE INTO vecteurs VALUES (?, ?, ?)",
            [(i, modele, v.astype(np.float32).tobytes()) for i, v in vecteurs.items()],
        )
        self.cx.commit()

    # ── extractions (réponses brutes du LLM, une par sujet) ──
    def extraction(self, signature: str) -> dict | None:
        ligne = self.cx.execute("SELECT reponse FROM extractions WHERE signature = ?", (signature,)).fetchone()
        return json.loads(ligne[0]) if ligne else None

    def enregistrer_extraction(self, signature: str, reponse: dict) -> None:
        self.cx.execute(
            "INSERT OR REPLACE INTO extractions VALUES (?, ?, ?)",
            (signature, datetime.now(timezone.utc).isoformat(), json.dumps(reponse, ensure_ascii=False)),
        )
        self.cx.commit()
