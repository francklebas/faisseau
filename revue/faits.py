"""Extraction des faits d'un sujet par LLM, puis vérification et classement par le code.

Le LLM propose des faits et les articles qui les énoncent. Le code ne lui fait pas
confiance : chaque rattachement fait → article est contrôlé sur le texte (mots et chiffres),
les rattachements oubliés sont ajoutés, et le statut d'un fait (commun, recoupé, isolé)
est calculé à partir du nombre de médias distincts, jamais déclaré par le LLM.

Le contrôle lexical manque les reformulations (« le Premier ministre » pour « Sébastien
Lecornu »). Si un modèle d'embeddings est fourni, un article est aussi rattaché quand une de
ses phrases est très proche du fait par le sens, à condition que les chiffres concordent :
deux phrases qui ne diffèrent que par un chiffre se ressemblent beaucoup.
"""

from __future__ import annotations

import hashlib
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
- Un fait est une affirmation vérifiable et courte, en une phrase complète et neutre, qui se \
comprend seule.
- Un fait ne dit qu'une chose. Énonce d'abord le fait central du sujet sous sa forme la plus \
simple (qui a fait quoi), sans date, lieu, chiffre ni circonstance. Chaque précision (date, lieu, \
chiffre, durée, cause) fait ensuite l'objet d'un fait séparé, avec ses propres sources. \
Exemple : « Le maire de Lyon a démissionné. » puis « La démission du maire de Lyon date du 3 mars. », \
et non « Le maire de Lyon a démissionné le 3 mars après douze ans de mandat. ».
- Seulement ce qui s'est passé, ce qui a été décidé ou ce qui a été dit. Pas de fait d'identité \
(« X est journaliste »), pas d'opinion ni de jugement. Une déclaration s'écrit comme un fait \
attribué : « X affirme que… ».
- Reprends les noms propres et les chiffres exactement comme ils sont écrits dans les textes : \
« Jensen Huang » et non « le patron de Nvidia », « 3-1 » et non « 3 buts à 1 ». Nomme les \
personnes et les organisations dans chaque fait, sans les remplacer par une périphrase.
- Pas de synthèse entre plusieurs articles : chaque fait doit être énoncé tel quel par chacune de \
ses sources. N'écris pas « plusieurs sondages », « selon certains médias », « en tête ou proche \
de la tête » : rapporte ce qu'un texte dit, précisément.
- Chaque fait doit garder son sens lu seul, hors de cette liste : pas de « Un sondage est publié \
le 11 novembre. » ni de « La plainte a été déposée contre X. » sans dire de quoi il s'agit.
- Ne donne jamais deux fois la même information.
- "sources" : tous les numéros d'articles qui énoncent ce fait explicitement, et seulement ceux-là.
- Donne de 5 à 12 faits. D'abord ceux présents dans plusieurs articles. Termine par 2 ou 3 faits \
qu'un seul article avance : un détail, un chiffre ou une déclaration absent des autres.
- "titre" : titre neutre et factuel du sujet, 12 mots au plus, sans recopier le titre d'un article.
- "hors_sujet" : numéros des articles qui traitent d'un autre sujet (liste vide sinon).

Réponds uniquement par un objet JSON de cette forme :
{"titre": "…", "faits": [{"fait": "…", "sources": [1, 3]}, {"fait": "…", "sources": [2]}], "hors_sujet": []}"""

# La consigne fait partie de la clé de cache : la modifier fait retraiter les sujets.
EMPREINTE_CONSIGNE = hashlib.sha1(SYSTEME.encode()).hexdigest()[:8]

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
    if not chiffres_concordent(fait, source):
        return 0.0
    return len(mots_fait & mots(source)) / len(mots_fait)


def chiffres_concordent(fait: str, source: str) -> bool:
    """Vrai si tous les chiffres du fait figurent dans la source."""
    # L'année en cours est tolérée : le LLM complète volontiers « le 12 novembre » en
    # « le 12 novembre 2026 », ce qui ne change pas le fait.
    return nombres(fait) - {str(date.today().year)} <= nombres(source)


MOTIF_PHRASE = re.compile(r"(?<=[.!?…»])\s+(?=[A-ZÀ-Ý«\"“])")


def phrases(article: Article) -> list[str]:
    """Le titre et les phrases de l'extrait : un fait se compare à une phrase, pas à un bloc."""
    return [article.titre] + [p.strip() for p in MOTIF_PHRASE.split(article.extrait or "") if len(p.strip()) >= 25]


MOTIF_PROPOSITION = re.compile(r"\s*[,;:()«»\"“”…–—]\s*|\s+-\s+")


def propositions(phrase: str) -> list[str]:
    """La phrase et ses propositions (coupées à la ponctuation, trois mots au moins).

    Un fait court ressemble peu à une longue phrase qui le contient, davantage à la
    proposition qui le porte.
    """
    morceaux = [m.strip() for m in MOTIF_PROPOSITION.split(phrase) if len(m.split()) >= 3]
    return list(dict.fromkeys([phrase] + morceaux))


def proximites(faits: list[str], articles: list[Article], encodeur) -> list[dict[str, tuple[float, str]]]:
    """Pour chaque fait et chaque article : (proximité de sens, phrase la plus proche).

    `encodeur.encoder(textes)` renvoie des vecteurs normalisés.
    """
    if encodeur is None or not faits or not articles:
        return [{} for _ in faits]
    morceaux = [(a, p) for a in articles for p in phrases(a)]
    vecteurs = encodeur.encoder(faits + [p for _, p in morceaux])
    similarites = vecteurs[: len(faits)] @ vecteurs[len(faits) :].T
    resultat: list[dict[str, tuple[float, str]]] = []
    for ligne in similarites:
        meilleures: dict[str, tuple[float, str]] = {}
        for (a, p), s in zip(morceaux, ligne):
            if a.id not in meilleures or s > meilleures[a.id][0]:
                meilleures[a.id] = (float(s), p)
        resultat.append(meilleures)
    return resultat


def rapprochements(faits: list[str], articles: list[Article], encodeur, seuil: float) -> list[set[str]]:
    """Pour chaque fait, identifiants des articles dont une phrase dit la même chose.

    La proximité ne suffit pas : « plus de 3 millions de personnes » et « plus de 2 millions de
    personnes » sont presque identiques pour le modèle, d'où le contrôle des chiffres sur tout
    le texte de l'article.
    """
    parid = {a.id: a for a in articles}
    return [
        {i for i, (s, _) in proches.items() if s >= seuil and chiffres_concordent(fait, parid[i].texte)}
        for fait, proches in zip(faits, proximites(faits, articles, encodeur))
    ]


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


def verifier(
    brut: dict,
    envoyes: list[Article],
    tous: list[Article],
    reglage: dict,
    titre_secours: str,
    encodeur=None,
    seuil_semantique: float | None = None,
    juge=None,
) -> Extraction:
    """Contrôle la réponse du LLM et construit l'extraction publiable.

    `envoyes` : articles numérotés dans l'invite. `tous` : tous les articles du sujet (ceux
    que le LLM n'a pas vus servent aussi au recoupement). `encodeur` et `seuil_semantique` :
    rapprochement par le sens, en plus du contrôle lexical (voir `rapprochements`).
    `juge` : implication textuelle (voir implication.Juge). Un fait candidat au niveau
    « commun » ne garde que les sources dont le texte (titre et extrait entiers) l'affirme,
    puis son niveau est recalculé ; sans aucune source qui l'affirme, il n'est pas publié.
    """
    extraction = Extraction()
    retenus: list[tuple[str, list[Article]]] = []
    corpus_complet = " ".join(a.texte for a in tous)

    proposes: list[tuple[str, list[Article]]] = []
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
        proposes.append((texte, cites))
    semantique = encodeur if seuil_semantique else None
    parid = {a.id: a for a in tous}
    sens = dict(zip((t for t, _ in proposes), proximites([t for t, _ in proposes], tous, semantique)))
    proches = [
        {i for i, (s, _) in sens[t].items() if seuil_semantique and s >= seuil_semantique and chiffres_concordent(t, parid[i].texte)}
        for t, _ in proposes
    ]

    for (texte, cites), memes in zip(proposes, proches):
        # 1. Une source citée n'est gardée que si son texte porte bien le fait.
        propres = noms_propres(texte, corpus_complet)
        sources = [a for a in dict.fromkeys(cites) if a.id in memes or porte(texte, a.texte, propres, reglage["ancrage_min"])]
        if not sources:
            extraction.rejets.append(f"aucune source ne porte ce fait : {texte!r}")
            continue
        # 2. Un article non cité qui énonce clairement le fait est ajouté : sans cela, un
        #    oubli du LLM ferait passer un fait partagé pour une affirmation isolée.
        if len(mots(texte)) >= 4:
            lexicales = [a for a in tous if a not in sources and porte(texte, a.texte, propres, reglage["ancrage_ajout"], 1.0)]
            ajouts = [a for a in tous if a not in sources and a not in lexicales and a.id in memes]
            extraction.rapproches += len(ajouts)
            sources += lexicales + ajouts
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
        # Le niveau « commun » se mérite : les mots d'un fait court se retrouvent facilement
        # dans des articles qui ne l'énoncent pas. Un candidat ne garde donc que les sources
        # dont le texte l'affirme, au jugement d'un modèle d'implication. Le modèle lit le
        # titre et l'extrait entiers : une phrase seule perd le sujet d'un « Il nie… ».
        if juge is not None and statut(len(medias), nb_medias, reglage["part_majorite"]) == "commun":
            verdicts = juge.affirme([(a.texte, texte) for a in sources])
            sources = [a for a, oui in zip(sources, verdicts) if oui]
            if not sources:
                extraction.rejets.append(f"candidat commun qu'aucune source n'affirme : {texte!r}")
                continue
            medias = list(dict.fromkeys(a.media_id for a in sources))
            if statut(len(medias), nb_medias, reglage["part_majorite"]) != "commun":
                extraction.declasses += 1
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


def extraire(
    articles: list[Article],
    client,
    noms_medias: dict[str, str],
    reglage: dict,
    cache=None,
    signature: str = "",
    encodeur=None,
    seuil_semantique: float | None = None,
    juge=None,
) -> Extraction:
    """Analyse un sujet. Un seul appel au LLM par sujet (deux si la première réponse est illisible).

    `cache` : objet avec `extraction(cle)` / `enregistrer_extraction(cle, dict)` ; la réponse
    du LLM y est conservée pour qu'un sujet inchangé ne soit jamais retraité.
    """
    titre_secours = articles[0].titre
    if client is None:
        return Extraction(titre=titre_secours, etat="indisponible")
    envoyes = choisir_articles(articles, reglage["max_articles_par_sujet"])
    cle = f"{signature}:{client.nom}:{EMPREINTE_CONSIGNE}" if signature else ""
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
    return verifier(brut, envoyes, articles, reglage, titre_secours, encodeur, seuil_semantique, juge)
