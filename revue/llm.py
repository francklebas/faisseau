"""Client LLM : API Mistral ou modèle local KoboldCpp, tous deux au format OpenAI."""

from __future__ import annotations

import os
from typing import Protocol

import httpx

from .config import Config


class ClientLLM(Protocol):
    nom: str

    def completer(self, systeme: str, utilisateur: str) -> str: ...


class ClientOpenAI:
    """Appelle `POST {url}/chat/completions` (Mistral, KoboldCpp, ou tout serveur compatible)."""

    def __init__(self, url: str, modele: str, cle: str = "", temperature: float = 0.1, max_jetons: int = 900, delai: float = 600, nom: str = "") -> None:
        self.url = url.rstrip("/")
        self.modele = modele
        self.cle = cle
        self.temperature = temperature
        self.max_jetons = max_jetons
        self.delai = delai
        self.nom = nom or f"{self.url}#{modele}"  # sert de clé de cache : un autre modèle retraite les sujets
        # Consommation déclarée par le serveur (champ `usage`), cumulée sur le passage.
        self.appels = 0
        self.jetons_entree = 0
        self.jetons_sortie = 0

    def _entetes(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.cle}"} if self.cle else {}

    def disponible(self) -> bool:
        try:
            return httpx.get(f"{self.url}/models", headers=self._entetes(), timeout=10).status_code == 200
        except httpx.HTTPError:
            return False

    def completer(self, systeme: str, utilisateur: str) -> str:
        reponse = httpx.post(
            f"{self.url}/chat/completions",
            headers=self._entetes(),
            timeout=self.delai,
            json={
                "model": self.modele,
                "messages": [
                    {"role": "system", "content": systeme},
                    {"role": "user", "content": utilisateur},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_jetons,
                "response_format": {"type": "json_object"},
            },
        )
        reponse.raise_for_status()
        corps = reponse.json()
        usage = corps.get("usage") or {}
        self.appels += 1
        self.jetons_entree += usage.get("prompt_tokens") or 0
        self.jetons_sortie += usage.get("completion_tokens") or 0
        return corps["choices"][0]["message"]["content"]


# Le repli sur le modèle local n'est jamais automatique : il change le modèle, donc les faits.
REPLI = " — repli local : REVUE_LLM=koboldcpp (ou make quotidien LLM=koboldcpp)"


def creer_client(config: Config) -> tuple[ClientOpenAI | None, str]:
    """Renvoie (client, message). Client None = pas d'extraction, le message dit pourquoi."""
    faits = config.reglages["faits"]
    fournisseur = config.fournisseur_llm
    if fournisseur == "aucun":
        return None, "extraction des faits désactivée (fournisseur « aucun »)"
    if fournisseur not in faits["fournisseurs"]:
        raise ValueError(f"fournisseur LLM inconnu : {fournisseur} (voir reglages.yaml)")
    f = faits["fournisseurs"][fournisseur]
    url = f["url"]
    cle = ""
    if fournisseur == "koboldcpp":
        url = os.environ.get("KOBOLDCPP_URL", url)
    if f.get("variable_cle"):
        cle = os.environ.get(f["variable_cle"], "")
        if not cle:
            return None, f"{fournisseur} : variable {f['variable_cle']} absente de l'environnement et de .env{REPLI}"
    modele = os.environ.get("REVUE_LLM_MODELE", f["modele"])
    client = ClientOpenAI(url, modele, cle, faits["temperature"], faits["max_jetons"], faits["delai_secondes"], nom=f"{fournisseur}:{modele}")
    if not client.disponible():
        return None, f"{fournisseur} injoignable ou clé refusée ({url}){REPLI if fournisseur != 'koboldcpp' else ''}"
    return client, f"{fournisseur} ({modele})"
