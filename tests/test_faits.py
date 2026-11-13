"""Extraction des faits : ce que le code garantit quelle que soit la réponse du LLM."""

import json

from conftest import FauxEncodeur, FauxLLM, article

from revue.base import Base
from revue.faits import ancrage, extraire, lire_json, nombres, statut

NOMS = {"alpha": "Alpha", "beta": "Bêta", "gamma": "Gamma", "delta": "Delta"}


def sujet_piscine():
    return [
        article("alpha", "Villeneuve : le conseil municipal vote la fermeture de la piscine",
                "Le conseil municipal de Villeneuve a voté mardi la fermeture de la piscine Jean-Moulin, par 21 voix contre 12."),
        article("beta", "La piscine Jean-Moulin de Villeneuve va fermer",
                "Les élus de Villeneuve ont voté mardi soir la fermeture de la piscine Jean-Moulin. Le maire évoque un coût de rénovation de 4 millions d'euros."),
        article("gamma", "Fermeture de la piscine de Villeneuve votée par le conseil municipal",
                "Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin mardi."),
        article("alpha", "Piscine de Villeneuve : les nageurs du club manifestent",
                "Une centaine de membres du club de natation ont manifesté devant la mairie de Villeneuve."),
    ]  # fmt: skip


def reponse(faits, titre="Fermeture de la piscine de Villeneuve votée", hors_sujet=()):
    return json.dumps({"titre": titre, "faits": [{"fait": f, "sources": s} for f, s in faits], "hors_sujet": list(hors_sujet)})


def par_texte(extraction):
    return {f.texte: f for f in extraction.faits}


def test_fait_rapporte_par_une_seule_source_est_isole(reglage_faits):
    """Le coût de 4 millions n'est avancé que par Bêta : il doit sortir comme affirmation isolée."""
    articles = sujet_piscine()
    client = FauxLLM(reponse([
        ("Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin.", [1, 2, 3]),
        ("Le maire évoque un coût de rénovation de 4 millions d'euros.", [2]),
    ]))  # fmt: skip
    extraction = extraire(articles, client, NOMS, reglage_faits)
    faits = par_texte(extraction)

    isole = faits["Le maire évoque un coût de rénovation de 4 millions d'euros."]
    assert isole.statut == "isole"
    assert isole.medias == ["beta"]
    assert isole.article_ids == [articles[1].id]

    commun = faits["Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin."]
    assert commun.statut == "commun"
    assert set(commun.medias) == {"alpha", "beta", "gamma"}


def test_deux_articles_du_meme_media_ne_font_pas_un_recoupement(reglage_faits):
    """Un fait porté par deux articles du même média reste isolé : on compte les médias."""
    articles = sujet_piscine() + [
        article("alpha", "Villeneuve : une centaine de nageurs devant la mairie",
                "Une centaine de membres du club de natation ont manifesté devant la mairie, selon nos informations."),
    ]  # fmt: skip
    client = FauxLLM(reponse([("Une centaine de membres du club de natation ont manifesté devant la mairie.", [4, 5])]))
    fait = extraire(articles, client, NOMS, reglage_faits).faits[0]
    assert len(fait.article_ids) == 2
    assert fait.medias == ["alpha"]
    assert fait.statut == "isole"


def test_source_citee_a_tort_est_retiree(reglage_faits):
    """Le LLM attribue le coût à Gamma, dont le texte n'en dit rien : la source est retirée."""
    client = FauxLLM(reponse([("Le maire évoque un coût de rénovation de 4 millions d'euros.", [2, 3, 9])]))
    fait = extraire(sujet_piscine(), client, NOMS, reglage_faits).faits[0]
    assert fait.medias == ["beta"]
    assert fait.statut == "isole"


def test_fait_sans_aucune_source_valable_est_rejete(reglage_faits):
    """Un fait inventé (absent de tous les textes cités) n'est jamais publié."""
    client = FauxLLM(reponse([
        ("Le préfet a annulé la délibération du conseil municipal.", [1, 2]),
        ("Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin.", [1]),
    ]))  # fmt: skip
    extraction = extraire(sujet_piscine(), client, NOMS, reglage_faits)
    assert [f.texte for f in extraction.faits] == ["Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin."]
    assert any("préfet" in r for r in extraction.rejets)


def test_chiffre_different_ne_vaut_pas_confirmation(reglage_faits):
    """« 21 voix » dans le fait : un article qui parle du vote sans ce chiffre ne le confirme pas."""
    client = FauxLLM(reponse([("Le conseil municipal a voté la fermeture de la piscine par 21 voix contre 12.", [1, 3])]))
    fait = extraire(sujet_piscine(), client, NOMS, reglage_faits).faits[0]
    assert fait.medias == ["alpha"]
    assert fait.statut == "isole"


def test_source_oubliee_par_le_llm_est_ajoutee(reglage_faits):
    """Le LLM ne cite qu'Alpha alors que Bêta et Gamma disent la même chose : pas de faux isolé."""
    client = FauxLLM(reponse([("Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin.", [1])]))
    fait = extraire(sujet_piscine(), client, NOMS, reglage_faits).faits[0]
    assert set(fait.medias) == {"alpha", "beta", "gamma"}
    assert fait.statut != "isole"


def sujet_universites():
    return [
        article("alpha", "Universités : Sébastien Lecornu annonce 5 000 places de plus en licence",
                "Le chef du gouvernement veut ouvrir 5 000 places à la rentrée. Les syndicats étudiants jugent l'effort insuffisant."),
        article("beta", "Le Premier ministre promet 5 000 places supplémentaires en licence",
                "Matignon a confirmé la création de 5 000 places supplémentaires en licence dès la rentrée prochaine."),
        article("gamma", "Licence : 3 000 places de plus, loin des besoins selon les présidents d'université",
                "Les présidents d'université réclamaient 3 000 places de plus dès cette année."),
    ]  # fmt: skip


FAIT_PLACES = "Le Premier ministre a formalisé la création de 5 000 places supplémentaires en licence."
SENS_PLACES = {"5 000 places": "places", "3 000 places de plus, loin": "places", "formalisé la création": "places"}


def test_reformulation_rattachee_par_le_sens(reglage_faits):
    """Alpha dit la même chose avec d'autres mots : sans le sens, le fait passe pour isolé."""
    articles = sujet_universites()
    brut = reponse([(FAIT_PLACES, [2])], titre="5 000 places supplémentaires en licence")
    lexical = extraire(articles, FauxLLM(brut), NOMS, reglage_faits)
    assert lexical.faits[0].medias == ["beta"] and lexical.faits[0].statut == "isole"

    encodeur = FauxEncodeur(SENS_PLACES)
    avec_sens = extraire(articles, FauxLLM(brut), NOMS, reglage_faits, encodeur=encodeur, seuil_semantique=0.75)
    assert avec_sens.faits[0].medias == ["beta", "alpha"]
    assert avec_sens.faits[0].statut == "commun"
    assert avec_sens.rapproches == 1
    assert encodeur.appels == 1  # un seul lot d'embeddings par sujet


def test_le_sens_ne_passe_pas_outre_un_chiffre_different(reglage_faits):
    """Gamma ressemble au fait mais parle de 3 000 places : la proximité ne vaut pas confirmation."""
    articles = sujet_universites()
    client = FauxLLM(reponse([(FAIT_PLACES, [2, 3])], titre="5 000 places supplémentaires en licence"))
    extraction = extraire(articles, client, NOMS, reglage_faits, encodeur=FauxEncodeur(SENS_PLACES), seuil_semantique=0.75)
    assert "gamma" not in extraction.faits[0].medias


def test_sans_seuil_le_sens_n_est_pas_utilise(reglage_faits):
    articles = sujet_universites()
    encodeur = FauxEncodeur(SENS_PLACES)
    client = FauxLLM(reponse([(FAIT_PLACES, [2])], titre="5 000 places supplémentaires en licence"))
    extraction = extraire(articles, client, NOMS, reglage_faits, encodeur=encodeur, seuil_semantique=None)
    assert extraction.faits[0].medias == ["beta"] and encodeur.appels == 0


def test_chaque_fait_renvoie_a_des_articles_du_sujet(reglage_faits):
    articles = sujet_piscine()
    client = FauxLLM(reponse([
        ("Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin.", [1, 2, 3]),
        ("Le maire évoque un coût de rénovation de 4 millions d'euros.", [2]),
        ("Une centaine de membres du club de natation ont manifesté devant la mairie.", ["4"]),
    ]))  # fmt: skip
    extraction = extraire(articles, client, NOMS, reglage_faits)
    connus = {a.id for a in articles}
    assert len(extraction.faits) == 3
    for fait in extraction.faits:
        assert fait.article_ids and set(fait.article_ids) <= connus


def test_doublons_fusionnes(reglage_faits):
    client = FauxLLM(reponse([
        ("Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin.", [1]),
        ("Le conseil municipal de Villeneuve a voté mardi la fermeture de la piscine Jean-Moulin.", [3]),
    ]))  # fmt: skip
    assert len(extraire(sujet_piscine(), client, NOMS, reglage_faits).faits) == 1


def test_article_hors_sujet_ecarte_sauf_s_il_porte_un_fait(reglage_faits):
    articles = sujet_piscine() + [article("delta", "Le club de football de Villeneuve monte en division supérieure")]
    fait = ("Le conseil municipal de Villeneuve a voté la fermeture de la piscine Jean-Moulin.", [1, 2, 3])
    # Numérotation de l'invite : un article par média d'abord → [4] est l'article de Delta.
    extraction = extraire(articles, FauxLLM(reponse([fait], hors_sujet=[4, 1])), NOMS, reglage_faits)
    assert extraction.hors_sujet == [articles[4].id]  # l'article 1 porte un fait : il reste


def test_reponse_illisible_puis_correcte(reglage_faits):
    bonne = "Voici le résultat :\n```json\n" + reponse([("Le maire évoque un coût de rénovation de 4 millions d'euros.", [2])]) + "\n```"
    client = FauxLLM("Désolé, je ne peux pas répondre.", bonne)
    extraction = extraire(sujet_piscine(), client, NOMS, reglage_faits)
    assert client.appels == 2
    assert extraction.etat == "ok" and len(extraction.faits) == 1


def test_reponse_toujours_illisible_donne_un_echec_sans_fait(reglage_faits):
    extraction = extraire(sujet_piscine(), FauxLLM("pas du JSON"), NOMS, reglage_faits)
    assert extraction.etat == "echec" and extraction.faits == []
    assert extraction.titre == sujet_piscine()[0].titre


def test_sans_llm_le_sujet_reste_publiable(reglage_faits):
    extraction = extraire(sujet_piscine(), None, NOMS, reglage_faits)
    assert extraction.etat == "indisponible" and extraction.faits == []


def test_un_seul_appel_au_llm_par_sujet(reglage_faits):
    """Le traitement IA se fait une fois par sujet : le second passage relit le cache."""
    base = Base(":memory:")
    client = FauxLLM(reponse([("Le maire évoque un coût de rénovation de 4 millions d'euros.", [2])]))
    for _ in range(3):
        extraction = extraire(sujet_piscine(), client, NOMS, reglage_faits, cache=base, signature="abc123")
    assert client.appels == 1
    assert len(extraction.faits) == 1


def test_titre_invente_remplace_par_un_titre_d_article(reglage_faits):
    fait = ("Le maire évoque un coût de rénovation de 4 millions d'euros.", [2])
    extraction = extraire(sujet_piscine(), FauxLLM(reponse([fait], titre="Scandale financier à la mairie de Bordeaux")), NOMS, reglage_faits)
    assert extraction.titre == sujet_piscine()[0].titre


def test_statut_selon_le_nombre_de_medias():
    assert statut(1, 10, 0.5) == "isole"
    assert statut(2, 10, 0.5) == "recoupe"
    assert statut(5, 10, 0.5) == "commun"
    assert statut(2, 3, 0.5) == "commun"
    assert statut(1, 1, 0.5) == "isole"


def test_nombres_normalises():
    assert nombres("6 000 écoles") == nombres("6.000 écoles") == nombres("6000 écoles") == {"6000"}
    assert nombres("deux députés et 2 journalistes") == {"2"}
    assert nombres("en 2027, 22 % des électeurs") == {"2027", "22"}


def test_ancrage():
    source = "Le conseil municipal de Villeneuve a voté mardi la fermeture de la piscine, par 21 voix contre 12."
    assert ancrage("Le conseil municipal a voté la fermeture de la piscine.", source) == 1.0
    assert ancrage("La fermeture a été votée par 25 voix.", source) == 0.0  # chiffre absent de la source
    assert ancrage("Le préfet a saisi le tribunal administratif.", source) == 0.0


def test_lire_json_tolere_l_habillage():
    assert lire_json('```json\n{"titre": "t", "faits": []}\n```')["titre"] == "t"
    assert lire_json('[{"titre": "t", "faits": []}]')["faits"] == []


def test_un_fait_commun_redescend_sans_sources_proches_par_le_sens(reglage_faits):
    from revue.faits import verifier

    textes = [
        ("a", "Le maire de Lyon a démissionné ce matin"),
        ("b", "Lyon : le maire annonce qu'il a démissionné"),
        ("c", "À Lyon, le maire dément avoir démissionné"),
        ("d", "Lyon : la rumeur disant que le maire a démissionné enfle"),
        ("e", "Le maire de Lyon a démissionné ? Ses adjoints n'y croient pas"),
    ]
    articles = [article(m, t) for m, t in textes]
    brut = {"titre": "Démission du maire de Lyon", "faits": [{"fait": "Le maire de Lyon a démissionné.", "sources": [1, 2, 3, 4, 5]}]}
    sans = verifier(brut, articles, articles, reglage_faits, "secours")
    assert sans.faits[0].statut == "commun"
    encodeur = FauxEncodeur({"démissionné ce matin": "demission", "annonce qu'il a démissionné": "demission", "Le maire de Lyon a démissionné.": "demission"})
    avec = verifier(brut, articles, articles, reglage_faits, "secours", encodeur, None, 0.65)
    assert avec.declasses == 1
    assert avec.faits[0].statut == "recoupe"
    assert sorted(avec.faits[0].medias) == ["a", "b"]
