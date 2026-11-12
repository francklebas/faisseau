from datetime import datetime, timezone
from pathlib import Path

import pytest

from revue import config as configuration
from revue.collecte import identifiant
from revue.modeles import Article

RACINE = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def cfg():
    return configuration.charger(RACINE)


@pytest.fixture
def reglage_faits(cfg):
    return dict(cfg.reglages["faits"])


def article(media: str, titre: str, extrait: str = "") -> Article:
    url = f"https://{media}.example/{abs(hash((media, titre)))}"
    return Article(identifiant(url), media, titre, extrait, url, datetime(2026, 11, 11, 8, 0, tzinfo=timezone.utc))


class FauxLLM:
    """Client LLM de test : renvoie des réponses préparées et compte les appels."""

    nom = "faux#test"

    def __init__(self, *reponses: str) -> None:
        self.reponses = list(reponses)
        self.appels = 0

    def completer(self, systeme: str, utilisateur: str) -> str:
        self.appels += 1
        return self.reponses[min(self.appels, len(self.reponses)) - 1]
