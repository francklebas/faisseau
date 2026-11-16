"""Ligne de commande : `revue executer`, `revue flux`, `revue sujets`."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

from . import config as configuration
from .base import Base
from .collecte import collecter
from .couverture import asymetrie, effectifs
from .affinites import analyser, ecrire_couvertures, en_markdown, lire_couvertures
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


def _sujets(
    cfg, base: Base, max_sujets: int | None = None, encodeur=None, reference: datetime | None = None
) -> tuple[list[Sujet], int, dict[str, int], list[Sujet]]:
    from .plongements import encodeur_depuis, vecteurs_articles
    from .regroupement import construire_sujets

    r = cfg.reglages
    fin = reference or datetime.now(timezone.utc)
    debut = fin - timedelta(hours=r["collecte"]["fenetre_heures"])
    articles = base.articles_depuis(debut, fin, medias={m.id for m in cfg.medias_actifs})
    if not articles:
        return [], 0, {}, []
    modele = cfg.modele_embeddings
    _dire(f"Embeddings ({modele['cle']}) : {len(articles)} articles sur {r['collecte']['fenetre_heures']} h")
    vecteurs = vecteurs_articles(base, encodeur or encodeur_depuis(cfg), articles)
    g = r["regroupement"]
    tous = construire_sujets(
        articles,
        vecteurs,
        seuil=modele["seuil"],
        liaison=g["liaison"],
        min_medias=g["min_medias"],
        max_articles_par_media=g["max_articles_par_media"],
    )
    # Édition = les sujets les plus couverts, plus les plus asymétriques trouvés au-delà :
    # par nature, un sujet porté par un seul bord est rarement parmi les plus couverts.
    limite = max_sujets or g["max_sujets"]
    sujets = tous[:limite]
    effectif = effectifs((a.media_id for a in articles), cfg)
    ecarts = [(asymetrie(s.articles, effectif, cfg), s) for s in tous[limite:]]
    penches = sorted((e for e in ecarts if e[0]["notable"]), key=lambda e: -abs(e[0]["ecart"]))
    sujets += [s for _, s in penches[: g["max_asymetries"]]]
    _dire(
        f"Regroupement : {len(tous)} sujets d'au moins {g['min_medias']} médias ; {len(sujets)} retenus "
        f"dont {len(sujets) - min(limite, len(tous))} asymétriques hors classement "
        f"(médias présents : {effectif['gauche']} à gauche, {effectif['droite']} à droite)"
    )
    return sujets, len(articles), effectif, tous


def executer(options) -> int:
    from .faits import extraire
    from .implication import juge_depuis
    from .llm import creer_client
    from .plongements import encodeur_depuis

    cfg = configuration.charger()
    base = Base(cfg.base)
    debut = time.time()
    reference = datetime.fromisoformat(options.reference).astimezone(timezone.utc) if options.reference else None
    erreurs = [] if options.sans_collecte or reference else _collecter(cfg, base)
    base.purger(cfg.reglages["collecte"]["conservation_jours"])

    encodeur = encodeur_depuis(cfg)
    sujets, nb_articles, effectif, tous = _sujets(cfg, base, options.max_sujets, encodeur, reference)
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
    seuil_faits = cfg.modele_embeddings.get("seuil_faits")
    juge = juge_depuis(cfg) if client is not None else None
    if juge is not None:
        _dire(f"Niveau commun contrôlé par implication : {juge.nom} (seuil {juge.seuil})")
    if client is not None:
        _dire(f"Recoupement par le sens : {f'seuil {seuil_faits}' if seuil_faits else 'désactivé (pas de seuil_faits pour ce modèle)'}")
    for rang, sujet in enumerate(sujets, 1):
        t0 = time.time()
        sujet.extraction = extraire(
            sujet.articles, client, noms, cfg.reglages["faits"], cache=base, signature=sujet.signature,
            encodeur=encodeur, seuil_semantique=seuil_faits, juge=juge,
        )  # fmt: skip
        if client is not None:
            e = sujet.extraction
            _dire(
                f"  {rang}/{len(sujets)} « {e.titre[:60]} » : {len(e.faits)} faits, "
                f"{e.rapproches} sources rapprochées par le sens, {e.declasses} communs déclassés, {len(e.rejets)} rejetés, "
                f"{len(e.hors_sujet)} hors sujet ({time.time() - t0:.0f} s)"
            )

    if client is not None:
        _dire(
            f"Consommation LLM : {client.appels} appels, {client.jetons_entree} jetons en entrée, "
            f"{client.jetons_sortie} en sortie (sujets déjà en cache non recomptés)"
        )

    stats = {
        "nb_articles": nb_articles,
        "nb_medias_actifs": len(cfg.medias_actifs),
        "fenetre_heures": cfg.reglages["collecte"]["fenetre_heures"],
        "modele_embeddings": cfg.modele_embeddings["nom"],
        "llm": message,
        "flux_en_erreur": erreurs,
    }
    chemin = ecrire_edition(sujets, cfg, stats, effectif, reference)
    # Tous les sujets du jour, publiés ou non : matière du contrôle par la couverture.
    ecrire_couvertures(tous, cfg, chemin.stem)
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
    trouves, _, _, _ = _sujets(cfg, base, options.max_sujets)
    for rang, sujet in enumerate(trouves, 1):
        print(f"\n## {rang}. {len(sujet.articles)} articles, {len(sujet.medias)} médias")
        for a in sujet.articles:
            print(f"   [{a.media_id}] {a.titre[:110]}")
    return 0


def affinites(_options) -> int:
    """Compare la couverture des médias sur l'historique et signale ceux qui s'écartent de leur bloc."""
    cfg = configuration.charger()
    rapport = analyser(*lire_couvertures(cfg.dossier_donnees / "couvertures"), cfg)
    texte = en_markdown(rapport, cfg)
    print(texte)
    sortie = cfg.dossier_donnees / "affinites.md"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(texte, encoding="utf-8")
    print(f"Rapport écrit dans {sortie}")
    return 0


def main() -> None:
    analyse = argparse.ArgumentParser(prog="revue", description="Revue quotidienne : pipeline quotidien")
    commandes = analyse.add_subparsers(dest="commande", required=True)

    c = commandes.add_parser("executer", help="collecte, regroupement, extraction des faits, écriture de l'édition")
    c.add_argument("--sans-collecte", action="store_true", help="réutilise les articles déjà en base")
    c.add_argument("--sans-llm", action="store_true", help="pas d'extraction des faits")
    c.add_argument("--exiger-llm", action="store_true", help="échoue si le LLM configuré est injoignable (passage planifié)")
    c.add_argument("--max-sujets", type=int, help="surcharge regroupement.max_sujets")
    c.add_argument(
        "--reference",
        metavar="DATE_ISO",
        help="rejoue l'édition telle qu'à cette date (ex. 2026-11-11T21:55:00+01:00), sans collecte, à partir de la base",
    )
    c.set_defaults(fonction=executer)

    c = commandes.add_parser("flux", help="vérifie l'état de chaque flux RSS")
    c.set_defaults(fonction=flux)

    c = commandes.add_parser("sujets", help="affiche les sujets regroupés (réglage du seuil)")
    c.add_argument("--max-sujets", type=int)
    c.set_defaults(fonction=sujets)

    c = commandes.add_parser("affinites", help="compare la couverture des médias sur l'historique des éditions")
    c.set_defaults(fonction=affinites)

    options = analyse.parse_args()
    sys.exit(options.fonction(options))


if __name__ == "__main__":
    main()
