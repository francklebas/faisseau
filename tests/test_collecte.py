"""Collecte : on ne garde que titre, extrait court et lien — jamais le texte de l'article."""

from datetime import datetime, timezone

from revue.base import Base
from revue.collecte import analyser_flux, nettoyer_html, normaliser_url, tronquer

LONG = "Paragraphe de l'article complet. " * 200

FLUX = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><title>Journal de test</title>
<item>
  <title>Budget : le S&#233;nat adopte le texte</title>
  <link>https://journal.example/budget?utm_source=rss&amp;id=7#xtor=RSS-1</link>
  <description><![CDATA[<p>Le <b>Sénat</b> a adopté le budget&nbsp;mardi.</p><img src="x.jpg"/>]]></description>
  <content:encoded><![CDATA[<p>{LONG}</p>]]></content:encoded>
  <pubDate>Wed, 11 Nov 2026 07:30:00 +0100</pubDate>
</item>
<item>
  <title>Article livré en entier dans le flux</title>
  <link>https://journal.example/integral</link>
  <content:encoded><![CDATA[<p>{LONG}</p>]]></content:encoded>
</item>
<item>
  <title>Résumé interminable</title>
  <link>https://journal.example/long</link>
  <description>{LONG}</description>
</item>
<item><title>Sans lien</title></item>
<item><title>Budget : le Sénat adopte le texte (doublon)</title><link>https://journal.example/budget?id=7</link></item>
</channel></rss>""".encode()


def test_flux_reduit_au_titre_a_l_extrait_et_au_lien():
    maintenant = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
    articles = analyser_flux(FLUX, "journal", extrait_max=400, maintenant=maintenant)
    assert [a.titre for a in articles] == ["Budget : le Sénat adopte le texte", "Article livré en entier dans le flux", "Résumé interminable"]

    budget, integral, long = articles
    assert budget.extrait == "Le Sénat a adopté le budget mardi."
    assert budget.url == "https://journal.example/budget?id=7"  # suivi publicitaire retiré
    assert budget.publie_le == datetime(2026, 11, 11, 6, 30, tzinfo=timezone.utc)
    assert budget.media_id == "journal"

    # Le texte intégral (content:encoded) n'est jamais repris, même à défaut de résumé.
    assert integral.extrait == ""
    assert integral.publie_le == maintenant
    # Un résumé trop long est coupé.
    assert len(long.extrait) <= 400 and long.extrait.endswith("…")
    assert all("Paragraphe" not in a.extrait or len(a.extrait) <= 400 for a in articles)


def test_rien_d_autre_n_est_stocke():
    base = Base(":memory:")
    articles = analyser_flux(FLUX, "journal", extrait_max=400)
    assert base.ajouter_articles(articles) == 3
    assert base.ajouter_articles(articles) == 0  # pas de doublon au second passage
    colonnes = [c[1] for c in base.cx.execute("PRAGMA table_info(articles)")]
    assert colonnes == ["id", "media_id", "titre", "extrait", "url", "publie_le", "collecte_le"]
    assert max(len(e) for (e,) in base.cx.execute("SELECT extrait FROM articles")) <= 400


def test_outils_de_nettoyage():
    assert nettoyer_html("<p>Un&nbsp;<em>texte</em></p>\n<script>alert(1)</script> propre") == "Un texte propre"
    assert tronquer("mot " * 50, 30).endswith("…") and len(tronquer("mot " * 50, 30)) <= 30
    assert tronquer("court", 30) == "court"
    assert normaliser_url("https://a.example/x?utm_medium=rss&p=2&fbclid=abc#ancre") == "https://a.example/x?p=2"
