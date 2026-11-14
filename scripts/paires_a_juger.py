"""Second avis sur le jeu de référence : des paires tirées au hasard, à juger sans aide.

    uv run python scripts/paires_a_juger.py tirer      # écrit tests/donnees/paires_a_juger.md
    uv run python scripts/paires_a_juger.py comparer   # une fois les verdicts remplis

Le fichier à remplir ne contient ni les verdicts de la première relecture ni les scores du
modèle. `comparer` confronte ensuite les trois : le second avis, la première relecture
(« enonce_contexte ») et le modèle d'implication du pipeline.
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
REFERENCE = RACINE / "tests/donnees/paires_fait_source.json"
A_JUGER = RACINE / "tests/donnees/paires_a_juger.md"
GRAINE = 20261114
NOMBRE = 20

ENTETE = """# Paires à juger

Pour chaque paire : le titre et l'extrait de l'article affirment-ils le fait ?
Écrire `oui` ou `non` après « Verdict : ». Ne rien changer d'autre.

« Affirmer » : un lecteur qui n'a que ce titre et cet extrait peut-il dire que le fait y est
écrit, avec tous ses détails (noms, chiffres, lieu, « contre qui ») ? Ce qui est seulement
probable ou sous-entendu ne compte pas.

Ensuite : `uv run python scripts/paires_a_juger.py comparer`
"""


def tirer() -> None:
    paires = json.loads(REFERENCE.read_text(encoding="utf-8"))["paires"]
    choisies = random.Random(GRAINE).sample(paires, NOMBRE)
    blocs = [ENTETE]
    for p in choisies:
        blocs.append(
            f"## Paire {p['n']}\n\n**Fait :** {p['fait']}\n\n**Titre :** {p['titre']}\n\n"
            f"**Extrait :** {p['extrait'] or '(aucun)'}\n\nVerdict : \n"
        )
    A_JUGER.write_text("\n".join(blocs), encoding="utf-8")
    print(f"{NOMBRE} paires sur {len(paires)} (graine {GRAINE}) : {A_JUGER}")


def comparer() -> None:
    from revue import config as configuration
    from revue.implication import juge_depuis

    paires = {p["n"]: p for p in json.loads(REFERENCE.read_text(encoding="utf-8"))["paires"]}
    avis: dict[int, bool] = {}
    for numero, verdict in re.findall(r"^## Paire (\d+)$.*?^Verdict :[ \t]*(\S*)", A_JUGER.read_text(encoding="utf-8"), flags=re.M | re.S):
        if verdict.lower() in ("oui", "non"):
            avis[int(numero)] = verdict.lower() == "oui"
    if not avis:
        sys.exit("Aucun verdict rempli (oui ou non après « Verdict : »).")
    juges = [paires[n] for n in avis]
    textes = [f"{p['titre']}. {p['extrait']}" if p["extrait"] else p["titre"] for p in juges]
    modele = juge_depuis(configuration.charger()).affirme([(t, p["fait"]) for t, p in zip(textes, juges)])
    print(f"{len(avis)} paires jugées\n")
    print(f"{'n°':>3}  second avis  première relecture  modèle  fait")
    for p, m in zip(juges, modele):
        a, r = avis[p["n"]], p["enonce_contexte"]
        marque = "  " if a == r == m else "≠ "
        print(f"{p['n']:>3}  {marque}{'oui' if a else 'non':<9}  {'oui' if r else 'non':<18}  {'oui' if m else 'non':<6}  {p['fait'][:70]}")
    accord = sum(avis[p["n"]] == p["enonce_contexte"] for p in juges)
    print(f"\nAccord entre les deux relectures : {accord}/{len(juges)}")
    for nom, verite in (("second avis", [avis[p["n"]] for p in juges]), ("première relecture", [p["enonce_contexte"] for p in juges])):
        fp = sum(m and not v for m, v in zip(modele, verite))
        fn = sum(v and not m for m, v in zip(modele, verite))
        print(f"Modèle contre {nom} : {fp} faux positifs, {fn} faux négatifs")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("tirer", "comparer"):
        sys.exit(__doc__)
    {"tirer": tirer, "comparer": comparer}[sys.argv[1]]()
