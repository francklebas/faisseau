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


class FauxEncodeur:
    """Encodeur de test : deux textes sont proches s'ils portent la même étiquette de sens.

    `sens` associe un fragment de texte à une étiquette ; un texte sans étiquette n'est proche
    d'aucun autre.
    """

    def __init__(self, sens: dict[str, str]) -> None:
        self.sens = sens
        self.appels = 0

    def encoder(self, textes: list[str]):
        import numpy as np

        self.appels += 1
        etiquettes = sorted(set(self.sens.values()))
        vecteurs = np.zeros((len(textes), len(etiquettes) + len(textes)), dtype=np.float32)
        for i, texte in enumerate(textes):
            trouvee = next((e for fragment, e in self.sens.items() if fragment in texte), None)
            vecteurs[i, etiquettes.index(trouvee) if trouvee else len(etiquettes) + i] = 1.0
        return vecteurs
