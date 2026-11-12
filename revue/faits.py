"""Extraction des faits d'un sujet par LLM, puis vérification et classement par le code.

Le LLM propose des faits et les articles qui les énoncent. Le code ne lui fait pas
confiance : chaque rattachement fait → article est contrôlé sur le texte (mots et chiffres),
les rattachements oubliés sont ajoutés, et le statut d'un fait (commun, recoupé, isolé)
est calculé à partir du nombre de médias distincts, jamais déclaré par le LLM.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from datetime import date

import httpx

from .modeles import Article, Extraction, Fait

SYSTEME = """Tu es documentaliste dans une agence de presse. On te donne des titres et extraits \
d'articles de médias français, numérotés, qui portent en principe sur le même sujet d'actualité. \
Tu dégages les faits rapportés et tu indiques précisément quels articles les énoncent.

Règles :
- Utilise uniquement les textes fournis. N'ajoute aucune connaissance extérieure, ne déduis rien.
- Un fait est une affirmation vérifiable et courte : une seule information par fait (qui, quoi, \
où, quand, combien), en une phrase complète et neutre, qui se comprend seule.
- Seulement ce qui s'est passé, ce qui a été décidé ou ce qui a été dit. Pas de fait d'identité \
(« X est journaliste »), pas d'opinion ni de jugement. Une déclaration s'écrit comme un fait \
attribué : « X affirme que… ».
- Reprends les noms propres et les chiffres exactement comme dans les textes.
- Ne donne jamais deux fois la même information.
- "sources" : tous les numéros d'articles qui énoncent ce fait explicitement, et seulement ceux-là.
- Donne de 4 à 9 faits. D'abord ceux présents dans plusieurs articles. Termine par 2 ou 3 faits \
qu'un seul article avance : un détail, un chiffre ou une déclaration absent des autres.
- "titre" : titre neutre et factuel du sujet, 12 mots au plus, sans recopier le titre d'un article.
- "hors_sujet" : numéros des articles qui traitent d'un autre sujet (liste vide sinon).

Réponds uniquement par un objet JSON de cette forme :
{"titre": "…", "faits": [{"fait": "…", "sources": [1, 3]}, {"fait": "…", "sources": [2]}], "hors_sujet": []}"""

MOTS_VIDES = frozenset(
    """a afin ai ainsi alors apres au aucun aussi autre autres aux avait avant avec avoir bien car ce
    cela celle celles celui ces cet cette ceux chez comme comment contre dans de depuis des deux donc dont du
    elle elles en encore entre est et etait ete etre eux fait faire fois font ici il ils je la le les leur
    leurs lors lui mais meme mes moins mon ne ni non nos notre nous on ont ou par parce pas pendant peu peut
    plus pour pourquoi qu quand que quel quelle quelles quels qui quoi sa sans se selon sera ses si son sont
    sous sur ta tandis tant te tes toujours tous tout toute toutes tres trop tu un une vers via vos votre
    vous ete ont deja apres ainsi dit affirme declare annonce indique selon""".split()
)
NOMBRES_EN_LETTRES = {
    "deux": "2", "trois": "3", "quatre": "4", "cinq": "5", "six": "6", "sept": "7", "huit": "8",
    "neuf": "9", "dix": "10", "onze": "11", "douze": "12", "treize": "13", "quatorze": "14",
    "quinze": "15", "seize": "16", "vingt": "20", "trente": "30", "quarante": "40",
    "cinquante": "50", "soixante": "60", "cent": "100", "mille": "1000",
}  # fmt: skip
MOTIF_NOMBRE = re.compile(r"\d{1,3}(?:[\s. \xa0]\d{3})+|\d+(?:,\d+)?")


def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texte.lower()) if not unicodedata.combining(c))


def nombres(texte: str) -> set[str]:
    """Nombres cités, normalisés : « 6 000 », « 6.000 » et « 6000 » sont identiques."""
    plat = _sans_accents(texte)
    trouves = {re.sub(r"\D", "", n) for n in MOTIF_NOMBRE.findall(plat)}
    trouves |= {NOMBRES_EN_LETTRES[m] for m in re.findall(r"[a-z]+", plat) if m in NOMBRES_EN_LETTRES}
    return trouves


def mots(texte: str) -> set[str]:
    """Mots porteurs de sens, sans accents, réduits à leurs 6 premières lettres."""
    plat = MOTIF_NOMBRE.sub(" ", _sans_accents(texte))
    return {
        m[:6]
        for m in re.findall(r"[a-z]+", plat)
        if len(m) >= 3 and m not in MOTS_VIDES and m not in NOMBRES_EN_LETTRES
    }


MOTIF_PROPRE = re.compile(r"(?<![\w-])[A-ZÀ-Ý][\w’'-]{2,}")


def noms_propres(fait: str, corpus: str) -> set[str]:
    """Noms propres du fait (mots à majuscule), sans accents.

    Le premier mot d'une phrase porte toujours une majuscule : il n'est compté que s'il
    apparaît aussi avec une majuscule en milieu de phrase dans les textes du sujet.
    """
    trouves = MOTIF_PROPRE.findall(fait)
    premier = re.match(r"[\W\d]*([A-ZÀ-Ý][\w’'-]{2,})", fait)
    if premier and trouves and trouves[0] == premier.group(1):
        if not re.search(r"[a-zà-ÿ,;:]\s+" + re.escape(trouves[0]) + r"(?![\w-])", corpus):
            trouves = trouves[1:]
    return {_sans_accents(n) for n in trouves}


def porte(fait: str, source: str, propres: set[str], seuil: float, part_propres: float = 0.75) -> bool:
    """Vrai si le texte de la source énonce le fait : assez de mots, de noms propres, tous les chiffres."""
    if propres:
        plat = _sans_accents(source)
        if sum(1 for n in propres if n in plat) / len(propres) < part_propres:
            return False
    return ancrage(fait, source) >= seuil


def ancrage(fait: str, source: str) -> float:
    """Part des mots du fait retrouvés dans la source (0 si un chiffre du fait en est absent)."""
    mots_fait = mots(fait)
    if not mots_fait:
        return 0.0
    # L'année en cours est tolérée : le LLM complète volontiers « le 12 novembre » en
    # « le 12 novembre 2026 », ce qui ne change pas le fait.
    if not nombres(fait) - {str(date.today().year)} <= nombres(source):
        return 0.0
    return len(mots_fait & mots(source)) / len(mots_fait)


def construire_invite(articles: list[Article], noms_medias: dict[str, str], extrait_max: int = 400) -> str:
    lignes = []
    for numero, a in enumerate(articles, 1):
        lignes.append(f"[{numero}] {noms_medias.get(a.media_id, a.media_id)} — {a.titre}")
        if a.extrait:
            extrait = a.extrait if len(a.extrait) <= extrait_max else a.extrait[:extrait_max].rsplit(" ", 1)[0] + "…"
            lignes.append(f"    {extrait}")
    return "Articles :\n" + "\n".join(lignes) + "\n\nJSON :"


def lire_json(texte: str) -> dict:
    """Extrait l'objet JSON d'une réponse de LLM (balises de code, texte autour…)."""
    texte = re.sub(r"^```(?:json)?|```$", "", texte.strip(), flags=re.M).strip()
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut < 0 or fin <= debut:
        raise ValueError("pas d'objet JSON dans la réponse")
    objet = json.loads(texte[debut : fin + 1])
    if not isinstance(objet, dict) or not isinstance(objet.get("faits"), list):
        raise ValueError("JSON sans liste « faits »")
    return objet


def choisir_articles(articles: list[Article], maximum: int) -> list[Article]:
    """Sélection transmise au LLM : un article par média d'abord, puis les suivants."""
    par_media: dict[str, list[Article]] = {}
    for a in articles:
        par_media.setdefault(a.media_id, []).append(a)
    choisis: list[Article] = []
    rang = 0
    while len(choisis) < min(maximum, len(articles)):
        for groupe in par_media.values():
            if rang < len(groupe) and len(choisis) < maximum:
                choisis.append(groupe[rang])
        rang += 1
    return choisis


def statut(nb_medias_fait: int, nb_medias_sujet: int, part_majorite: float) -> str:
    """isole : un seul média. commun : la majorité des médias du sujet. recoupe : entre les deux."""
    if nb_medias_fait <= 1:
        return "isole"
    if nb_medias_fait >= max(2, math.ceil(part_majorite * nb_medias_sujet)):
        return "commun"
    return "recoupe"


def verifier(brut: dict, envoyes: list[Article], tous: list[Article], reglage: dict, titre_secours: str) -> Extraction:
    """Contrôle la réponse du LLM et construit l'extraction publiable.

    `envoyes` : articles numérotés dans l'invite. `tous` : tous les articles du sujet (ceux
    que le LLM n'a pas vus servent aussi au recoupement).
    """
    extraction = Extraction()
    retenus: list[tuple[str, list[Article]]] = []
    corpus_complet = " ".join(a.texte for a in tous)

    for element in brut.get("faits", []):
        if not isinstance(element, dict):
            continue
        texte = re.sub(r"\s+", " ", str(element.get("fait") or element.get("texte") or "")).strip()
        if not 15 <= len(texte) <= 320:
            extraction.rejets.append(f"longueur invalide : {texte[:60]!r}")
            continue
        cites = []
        for numero in element.get("sources") or []:
            if isinstance(numero, (int, str)) and str(numero).isdigit() and 1 <= int(numero) <= len(envoyes):
                cites.append(envoyes[int(numero) - 1])
        # 1. Une source citée n'est gardée que si son texte porte bien le fait.
        propres = noms_propres(texte, corpus_complet)
        sources = [a for a in dict.fromkeys(cites) if porte(texte, a.texte, propres, reglage["ancrage_min"])]
        if not sources:
            extraction.rejets.append(f"aucune source ne porte ce fait : {texte!r}")
            continue
        # 2. Un article non cité qui énonce clairement le fait est ajouté : sans cela, un
        #    oubli du LLM ferait passer un fait partagé pour une affirmation isolée.
        if len(mots(texte)) >= 4:
            sources += [a for a in tous if a not in sources and porte(texte, a.texte, propres, reglage["ancrage_ajout"], 1.0)]
        # 3. Fusion des doublons (même fait reformulé).
        for i, (autre, autres_sources) in enumerate(retenus):
            a, b = mots(texte), mots(autre)
            if len(a & b) / max(len(a | b), 1) >= 0.7 and nombres(texte) == nombres(autre):
                retenus[i] = (autre, list(dict.fromkeys(autres_sources + sources)))
                break
        else:
            retenus.append((texte, sources))

    # Articles signalés hors sujet : écartés seulement s'ils ne soutiennent aucun fait retenu
    # et s'ils restent minoritaires (sinon c'est le LLM qui se trompe de sujet).
    soutiens = {a.id for _, sources in retenus for a in sources}
    signales = []
    for numero in brut.get("hors_sujet") or []:
        if isinstance(numero, (int, str)) and str(numero).isdigit() and 1 <= int(numero) <= len(envoyes):
            article = envoyes[int(numero) - 1]
            if article.id not in soutiens:
                signales.append(article.id)
    if len(signales) <= len(envoyes) / 3:
        extraction.hors_sujet = signales

    restants = [a for a in tous if a.id not in extraction.hors_sujet]
    nb_medias = len({a.media_id for a in restants})
    for texte, sources in retenus:
        medias = list(dict.fromkeys(a.media_id for a in sources))
        extraction.faits.append(
            Fait(
                texte=texte if texte[-1] in ".!?»" else texte + ".",
                article_ids=[a.id for a in sources],
                medias=medias,
                statut=statut(len(medias), nb_medias, reglage["part_majorite"]),
            )
        )
    ordre = {"commun": 0, "recoupe": 1, "isole": 2}
    extraction.faits.sort(key=lambda f: (ordre[f.statut], -len(f.medias)))

    # Le titre proposé doit lui aussi sortir des textes ; sinon on garde celui de secours.
    titre = re.sub(r"\s+", " ", str(brut.get("titre") or "")).strip().rstrip(".")
    corpus = " ".join(a.texte for a in restants)
    if 8 <= len(titre) <= 140 and ancrage(titre, corpus) >= 0.6:
        extraction.titre = titre
    else:
        extraction.titre = titre_secours
    if not extraction.faits:
        extraction.etat = "echec"
    return extraction


def extraire(articles: list[Article], client, noms_medias: dict[str, str], reglage: dict, cache=None, signature: str = "") -> Extraction:
    """Analyse un sujet. Un seul appel au LLM par sujet (deux si la première réponse est illisible).

    `cache` : objet avec `extraction(cle)` / `enregistrer_extraction(cle, dict)` ; la réponse
    du LLM y est conservée pour qu'un sujet inchangé ne soit jamais retraité.
    """
    titre_secours = articles[0].titre
    if client is None:
        return Extraction(titre=titre_secours, etat="indisponible")
    envoyes = choisir_articles(articles, reglage["max_articles_par_sujet"])
    cle = f"{signature}:{client.nom}" if signature else ""
    brut = cache.extraction(cle) if cache is not None and cle else None
    if brut is None:
        invite = construire_invite(envoyes, noms_medias, reglage.get("extrait_max_llm", 400))
        erreur = ""
        for _ in range(2):
            try:
                brut = lire_json(client.completer(SYSTEME, invite))
                break
            except (ValueError, KeyError) as e:  # réponse illisible : on réessaie une fois
                erreur = str(e)
            except httpx.HTTPError as e:  # serveur tombé ou délai dépassé : inutile d'insister
                erreur = type(e).__name__
                break
        if brut is None:
            return Extraction(titre=titre_secours, etat="echec", rejets=[f"pas de réponse exploitable : {erreur}"])
        if cache is not None and cle:
            cache.enregistrer_extraction(cle, brut)
    return verifier(brut, envoyes, articles, reglage, titre_secours)
