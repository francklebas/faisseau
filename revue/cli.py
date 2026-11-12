"""Ligne de commande : `revue executer`, `revue flux`, `revue sujets`."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

from . import config as configuration
from .base import Base
from .collecte import collecter
from .couverture import angle_mort
from .edition import ecrire_edition
from .modeles import Sujet


def _dire(message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


def _collecter(cfg, base: Base) -> list[str]:
    resultats = collecter(cfg)
    nouveaux = sum(base.ajouter_articles(r.articles) for r in resultats)
    erreurs = [f"{r.media_id} ({r.erreur})" for r in resultats if r.erreur]
    _dire(f"Collecte : {len(resultats)} flux, {nouveaux} nouveaux articles, {len(erreurs)} flux en erreur")
    for erreur in erreurs:
        _dire(f"  ⚠ {erreur}")
    return erreurs


def _sujets(cfg, base: Base, max_sujets: int | None = None) -> tuple[list[Sujet], int]:
    from .plongements import encodeur_depuis, vecteurs_articles
    from .regroupement import construire_sujets

    r = cfg.reglages
    debut = datetime.now(timezone.utc) - timedelta(hours=r["collecte"]["fenetre_heures"])
    articles = base.articles_depuis(debut, medias={m.id for m in cfg.medias_actifs})
    if not articles:
        return [], 0
    modele = cfg.modele_embeddings
    _dire(f"Embeddings ({modele['cle']}) : {len(articles)} articles sur {r['collecte']['fenetre_heures']} h")
    vecteurs = vecteurs_articles(base, encodeur_depuis(cfg), articles)
    g = r["regroupement"]
    tous = construire_sujets(
        articles,
        vecteurs,
        seuil=modele["seuil"],
        liaison=g["liaison"],
        min_medias=g["min_medias"],
        max_articles_par_media=g["max_articles_par_media"],
    )
    # Édition = les sujets les plus couverts, plus les angles morts trouvés au-delà : par
    # nature, un sujet porté par un seul bord est rarement parmi les plus couverts.
    limite = max_sujets or g["max_sujets"]
    sujets = tous[:limite]
    angles = [s for s in tous[limite:] if angle_mort(s.medias, cfg)]
    sujets += angles[: g["max_angles_morts"]]
    _dire(
        f"Regroupement : {len(tous)} sujets d'au moins {g['min_medias']} médias ; "
        f"{len(sujets)} retenus dont {len(sujets) - min(limite, len(tous))} angles morts hors classement"
    )
    return sujets, len(articles)


def executer(options) -> int:
    from .faits import extraire
    from .llm import creer_client

    cfg = configuration.charger()
    base = Base(cfg.base)
    debut = time.time()
    erreurs = [] if options.sans_collecte else _collecter(cfg, base)
    base.purger(cfg.reglages["collecte"]["conservation_jours"])

    sujets, nb_articles = _sujets(cfg, base, options.max_sujets)
    if not sujets:
        _dire("Aucun sujet : pas assez d'articles récents (lancer sans --sans-collecte ?).")
        return 1

    if options.sans_llm:
        client, message = None, "extraction des faits désactivée (--sans-llm)"
    else:
        client, message = creer_client(cfg)
    _dire(f"LLM : {message}")
    if client is None:
        if options.exiger_llm and not options.sans_llm and cfg.fournisseur_llm != "aucun":
            _dire("  ✖ --exiger-llm : abandon, aucune édition n'est écrite.")
            return 2
        _dire("  ⚠ La revue sera produite sans faits extraits (regroupement et couverture seulement).")

    noms = {m.id: m.nom for m in cfg.medias.values()}
    for rang, sujet in enumerate(sujets, 1):
        t0 = time.time()
        sujet.extraction = extraire(sujet.articles, client, noms, cfg.reglages["faits"], cache=base, signature=sujet.signature)
        if client is not None:
            e = sujet.extraction
            _dire(
                f"  {rang}/{len(sujets)} « {e.titre[:60]} » : {len(e.faits)} faits, "
                f"{len(e.rejets)} rejetés, {len(e.hors_sujet)} hors sujet ({time.time() - t0:.0f} s)"
            )

    stats = {
        "nb_articles": nb_articles,
        "nb_medias_actifs": len(cfg.medias_actifs),
        "fenetre_heures": cfg.reglages["collecte"]["fenetre_heures"],
        "modele_embeddings": cfg.modele_embeddings["nom"],
        "llm": message,
        "flux_en_erreur": erreurs,
    }
    chemin = ecrire_edition(sujets, cfg, stats)
    _dire(f"Édition écrite : {chemin} ({time.time() - debut:.0f} s)")
    base.fermer()
    return 0


def flux(_options) -> int:
    """État de chaque flux : utile pour repérer un flux mort ou déplacé."""
    cfg = configuration.charger()
    resultats = collecter(cfg)
    en_panne = 0
    for r in sorted(resultats, key=lambda r: r.media_id):
        etat = f"⚠ {r.erreur}" if r.erreur else "ok"
        en_panne += bool(r.erreur)
        print(f"{r.media_id:26} {len(r.articles):4} articles  {etat:28} {r.url}")
    print(f"\n{len(resultats)} flux, {en_panne} en erreur")
    return 1 if en_panne else 0


def sujets(options) -> int:
    """Affiche les sujets regroupés, sans LLM ni écriture : pour régler le seuil."""
    cfg = configuration.charger()
    base = Base(cfg.base)
    trouves, _ = _sujets(cfg, base, options.max_sujets)
    for rang, sujet in enumerate(trouves, 1):
        print(f"\n## {rang}. {len(sujet.articles)} articles, {len(sujet.medias)} médias")
        for a in sujet.articles:
            print(f"   [{a.media_id}] {a.titre[:110]}")
    return 0


def main() -> None:
    analyse = argparse.ArgumentParser(prog="revue", description="Revue du matin : pipeline quotidien")
    commandes = analyse.add_subparsers(dest="commande", required=True)

    c = commandes.add_parser("executer", help="collecte, regroupement, extraction des faits, écriture de l'édition")
    c.add_argument("--sans-collecte", action="store_true", help="réutilise les articles déjà en base")
    c.add_argument("--sans-llm", action="store_true", help="pas d'extraction des faits")
    c.add_argument("--exiger-llm", action="store_true", help="échoue si le LLM configuré est injoignable (passage planifié)")
    c.add_argument("--max-sujets", type=int, help="surcharge regroupement.max_sujets")
    c.set_defaults(fonction=executer)

    c = commandes.add_parser("flux", help="vérifie l'état de chaque flux RSS")
    c.set_defaults(fonction=flux)

    c = commandes.add_parser("sujets", help="affiche les sujets regroupés (réglage du seuil)")
    c.add_argument("--max-sujets", type=int)
    c.set_defaults(fonction=sujets)

    options = analyse.parse_args()
    sys.exit(options.fonction(options))


if __name__ == "__main__":
    main()
