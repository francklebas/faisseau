"""Collecte des flux RSS : titres, extraits courts et liens. Jamais le texte des articles."""

from __future__ import annotations

import asyncio
import calendar
import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import httpx

from .config import Config, Media
from .modeles import Article

# Paramètres de suivi retirés des liens (on ne piste pas, et on dédoublonne mieux).
PARAMETRES_SUIVI = re.compile(r"^(utm_|xtor|at_|mc_|fbclid|gclid|ref$|source$|origine$)", re.I)


class _SansBalises(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.morceaux: list[str] = []
        self._ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._ignore += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._ignore:
            self._ignore -= 1

    def handle_data(self, data):
        if not self._ignore:
            self.morceaux.append(data)


def nettoyer_html(texte: str) -> str:
    """Retire les balises et normalise les espaces."""
    if not texte:
        return ""
    analyseur = _SansBalises()
    analyseur.feed(texte)
    analyseur.close()
    propre = html.unescape(" ".join(analyseur.morceaux))
    return re.sub(r"\s+", " ", propre.replace("\xa0", " ")).strip()


def tronquer(texte: str, maximum: int) -> str:
    """Coupe à la limite de mot la plus proche, sans dépasser `maximum` caractères."""
    if len(texte) <= maximum:
        return texte
    coupe = texte[: maximum - 1]
    espace = coupe.rfind(" ")
    if espace > maximum * 0.6:
        coupe = coupe[:espace]
    return coupe.rstrip(" ,;:.") + "…"


def normaliser_url(url: str) -> str:
    """Retire fragment et paramètres de suivi."""
    parties = urlsplit(url.strip())
    requete = [(k, v) for k, v in parse_qsl(parties.query, keep_blank_values=True) if not PARAMETRES_SUIVI.match(k)]
    return urlunsplit((parties.scheme, parties.netloc, parties.path, urlencode(requete), ""))


def identifiant(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _date(entree, defaut: datetime) -> datetime:
    for champ in ("published_parsed", "updated_parsed", "created_parsed"):
        valeur = entree.get(champ)
        if valeur:
            try:
                date = datetime.fromtimestamp(calendar.timegm(valeur), tz=timezone.utc)
            except (OverflowError, ValueError):
                continue
            # Une date dans le futur (flux mal réglé) est ramenée à l'heure de collecte.
            return min(date, defaut)
    return defaut


def analyser_flux(contenu: bytes, media_id: str, extrait_max: int, maintenant: datetime | None = None) -> list[Article]:
    """Transforme un flux RSS/Atom en articles.

    Seuls le titre, le lien, la date et le résumé (`description` / `summary`) sont lus. Le
    champ `content:encoded`, qui contient parfois l'article entier, n'est jamais utilisé, et
    le résumé est tronqué à `extrait_max` caractères.
    """
    maintenant = maintenant or datetime.now(timezone.utc)
    flux = feedparser.parse(contenu)
    articles: list[Article] = []
    vus: set[str] = set()
    for entree in flux.entries:
        titre = nettoyer_html(entree.get("title", ""))
        lien = entree.get("link", "")
        if not titre or not lien.startswith("http"):
            continue
        url = normaliser_url(lien)
        if url in vus:
            continue
        vus.add(url)
        # feedparser recopie le contenu intégral dans `summary` quand le flux n'a pas de
        # résumé (il n'y a alors pas de `summary_detail`) : dans ce cas on ne garde rien
        # plutôt que le début de l'article.
        resume = entree.get("summary", "") if "summary_detail" in entree else ""
        extrait = tronquer(nettoyer_html(resume), extrait_max)
        if extrait == titre:
            extrait = ""
        articles.append(
            Article(
                id=identifiant(url),
                media_id=media_id,
                titre=tronquer(titre, 300),
                extrait=extrait,
                url=url,
                publie_le=_date(entree, maintenant),
            )
        )
    return articles


@dataclass
class ResultatFlux:
    media_id: str
    url: str
    articles: list[Article]
    erreur: str = ""


async def _telecharger(client: httpx.AsyncClient, verrou: asyncio.Semaphore, media: Media, url: str, extrait_max: int) -> ResultatFlux:
    async with verrou:
        try:
            reponse = await client.get(url)
            reponse.raise_for_status()
        except httpx.HTTPStatusError as e:
            return ResultatFlux(media.id, url, [], f"HTTP {e.response.status_code}")
        except httpx.HTTPError as e:
            return ResultatFlux(media.id, url, [], type(e).__name__)
    articles = analyser_flux(reponse.content, media.id, extrait_max)
    return ResultatFlux(media.id, url, articles, "" if articles else "flux vide ou illisible")


async def _collecter(config: Config) -> list[ResultatFlux]:
    r = config.reglages["collecte"]
    verrou = asyncio.Semaphore(r["connexions_simultanees"])
    async with httpx.AsyncClient(
        timeout=r["delai_secondes"],
        follow_redirects=True,
        headers={"User-Agent": r["user_agent"], "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
    ) as client:
        taches = [
            _telecharger(client, verrou, media, url, r["extrait_max_caracteres"])
            for media in config.medias_actifs
            for url in media.flux
        ]
        return await asyncio.gather(*taches)


def collecter(config: Config) -> list[ResultatFlux]:
    """Télécharge tous les flux actifs. Un flux en panne n'interrompt pas la collecte."""
    return asyncio.run(_collecter(config))
