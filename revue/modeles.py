"""Structures de données partagées par les étapes du pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Article:
    """Ce qu'on garde d'un article : son titre, un extrait court et son lien. Jamais le texte."""

    id: str
    media_id: str
    titre: str
    extrait: str
    url: str
    publie_le: datetime

    @property
    def texte(self) -> str:
        """Texte soumis à l'analyse (embeddings, LLM, ancrage)."""
        return f"{self.titre}. {self.extrait}" if self.extrait else self.titre


@dataclass
class Fait:
    texte: str
    article_ids: list[str]
    medias: list[str]  # identifiants de médias distincts, dans l'ordre de citation
    statut: str  # commun | recoupe | isole


@dataclass
class Extraction:
    """Résultat de l'analyse d'un sujet par le LLM, après vérification par le code."""

    titre: str = ""
    resume: str = ""
    faits: list[Fait] = field(default_factory=list)
    hors_sujet: list[str] = field(default_factory=list)  # identifiants d'articles écartés
    rejets: list[str] = field(default_factory=list)  # faits refusés, avec le motif
    rapproches: int = 0  # sources ajoutées par le sens seul (reformulations)
    declasses: int = 0  # faits candidats au niveau commun redescendus après contrôle par implication
    etat: str = "ok"  # ok | indisponible | echec


@dataclass
class Sujet:
    articles: list[Article]
    signature: str
    extraction: Extraction | None = None

    @property
    def medias(self) -> list[str]:
        return list(dict.fromkeys(a.media_id for a in self.articles))
