# Revue du matin — conclusions de la livraison du MVP

Bilan du 11 novembre 2026, après un passage complet du pipeline sur les vrais flux RSS et la
génération du site statique à partir de cette édition. Le mode d'emploi est dans le
[README](README.md) ; ce fichier consigne ce qui a été vérifié, ce qui marche moins bien et
ce qui reste à faire.

## Ce qui a été vérifié sur les vrais flux

- **Collecte** : 46 médias actifs, 56 flux, aucun en erreur, environ 1 560 articles sur 36 heures.
- **Regroupement** : 80 sujets d'au moins 3 médias. Les premiers ont été relus un par un, ils
  sont cohérents. Les sujets voisins restent séparés (trois annonces « Présidentielle 2027 »,
  deux affaires iraniennes le même jour).
- **Faits** : 32 sujets publiés, 163 faits (36 communs, 56 recoupés, 71 isolés). Chaque fait
  renvoie à au moins un article du sujet ; un sujet sur 32 n'a aucun fait.
- **Angles morts** : 2 trouvés, un à gauche, un à droite. Ils étaient hors des 30 sujets les
  plus couverts, donc l'édition les ajoute en plus du classement.
- **Tests** : les 33 passent, dont un test sur le vrai modèle avec 275 titres réels rangés à
  la main en 25 sujets.
- **Site** : 40 pages générées, 1,2 Mo, vérifié par captures en largeur ordinateur et mobile.
  La vérification de types passe.

Pour voir la revue : `make servir`, puis <http://localhost:4173>. `make` refait tout depuis
zéro, `make quotidien` est la commande à planifier.

## Ce qui marche moins bien

- **Faux « isolés »** : le contrôle des sources compare des mots, des noms propres et des
  chiffres, pas le sens. Quand deux médias disent la même chose avec des mots différents, le
  fait peut sortir comme affirmation isolée. Exemple du 11 novembre : les six faits du sujet
  sur la cyberattaque iranienne sont classés isolés. Le site prévient le lecteur, mais c'est
  la principale faiblesse.
- **Qualité du modèle local** : les essais ont été faits avec Gemma 3 4B via KoboldCpp, faute
  de clé Mistral sur la machine. Il formule parfois mal un fait et en propose de peu utiles.
  Compter environ 75 secondes par sujet sur le ThinkPad T14s, soit 20 à 25 minutes par édition
  (4 fils, Tctl autour de 70 °C). Le chemin Mistral est codé mais n'a pas été testé avec une
  vraie clé.
- **Seuils calibrés sur une seule journée** de titres.
- **Quatre médias absents** : Le Point, Les Échos, Marianne et RTL refusent les robots ou
  n'ont plus de flux public. Ils sont listés comme inactifs, sans contournement.

## Solon ou E5

Solon reste le défaut. Il sépare mieux les sujets (F1 0,996 contre 0,983) et son seuil est
bien moins sensible. E5 est environ 3,5 fois plus rapide (28 textes/s contre 8).
`make comparer-embeddings` refait la mesure ; le tableau complet est dans le README.

## Décisions prises sans validation préalable

- Trois niveaux de faits au lieu de deux : commun (majorité des médias), recoupé (au moins
  deux), isolé.
- Pas de résumé rédigé par le LLM ; seul le titre du sujet est synthétisé.
- Les extraits RSS servent à l'analyse mais ne sont pas republiés : le site affiche titres et
  liens.
- Pas d'API FastAPI, le site lit des fichiers JSON à la génération.
- Zéro JavaScript dans les pages publiées (une ligne à retirer dans `web/nuxt.config.ts` pour
  revenir à du Vue hydraté).
- Centre-gauche compte à gauche, centre-droit à droite ; réglable dans `config/reglages.yaml`.

## Ce qui reste à faire

- **Relire `config/medias.yaml`** : les 46 positionnements sont des propositions rédigées de
  mémoire, toutes marquées `a_valider` et affichées comme provisoires sur le site. Les plus
  discutables portent une note (France Inter, CNews, Le JDD, Valeurs actuelles, Front
  Populaire).
- **Choisir le LLM** : mettre `MISTRAL_API_KEY` dans `.env`, ou lancer KoboldCpp sur le port
  5001 avant un passage. Sans LLM joignable, `make` produit la revue sans faits et
  `make quotidien` échoue plutôt que de publier une édition dégradée.
- **Commit, déploiement, planification** : rien n'est commité (dépôt git initialisé
  seulement), rien n'est déployé sur Cloudflare, et le timer systemd de `deploy/` n'est pas
  installé.

## Suites du 12 novembre

Deux changements faits après relecture de ce bilan, mesurés sur les données du 11 novembre.
L'édition déjà générée n'a pas été refaite : ils s'appliqueront au prochain passage.

- **Angles morts : bords plus étroits.** Centre-gauche et centre-droit restent à gauche et à
  droite dans la répartition affichée, mais ne comptent plus comme un bord pour le signalement
  (`couverture.angle_mort.bords`). Les deux angles morts du 11 novembre tenaient à des médias
  modérés (une critique de film à 3 médias « de gauche » dont 2 centre-gauche ; un sujet à
  4 médias dont 1 centre-droit) : avec la nouvelle définition, aucun des 80 sujets n'en est un.
  Avec 9 médias de gauche et 12 de droite actifs, le seuil de 60 % sera rarement atteint ; il
  est à revoir après quelques jours de données.
- **Recoupement des faits par le sens.** En plus du contrôle lexical, un article est rattaché
  à un fait si une de ses phrases en est proche pour Solon (seuil 0,75) et que les chiffres
  concordent. Sur 30 sujets : 9 sources ajoutées, 1 fait sauvé du rejet, 4 faits isolés sur 66
  reclassés (dont « Paris accuse l'Iran » pour la cyberattaque). Le gain est réel mais limité :
  la plupart des affirmations isolées le sont vraiment dans les titres et extraits. Un seuil
  plus bas (0,72) en reclasse 8, au prix d'un rattachement faux observé sur 33.

Le seuil de 60 % a été remplacé le soir même par une mesure par pôle : voir le bilan ci-dessous.

---

# Bilan du 12 novembre au soir — grille de sources, asymétrie par pôle, contrôle par la couverture

Trois changements, un commit chacun, rien de poussé ni de déployé. L'édition du 11 novembre a
été rejouée avec ces changements (`uv run revue executer --reference 2026-11-11T21:55:00+01:00`)
et le site régénéré. Aucun positionnement n'a été modifié : les 50 restent `a_valider`.

## Ce qui a été vérifié

- **Tests** : les 51 passent ; la vérification de types du site aussi ; 38 pages générées.
- **Édition rejouée** : mêmes 1 569 articles et mêmes 80 sujets que la veille. 30 sujets
  publiés au lieu de 32 : les deux anciens « angles morts » (une critique de film, le mouvement
  lycéen) étaient hors des 30 premiers et ne passent plus le seuil.
- **Faits** : 36 communs, 61 recoupés, 64 isolés (contre 36, 56 et 71). L'écart vient du
  recoupement par le sens, des deux sujets sortis, et du sujet « Commémorations du 11 novembre »
  dont l'extraction avait échoué la veille et a réussi cette fois (4 faits). Plus aucun sujet
  sans fait. KoboldCpp a été lancé à la main sur le port 5002 pour ce seul sujet, puis arrêté.
- **Sources des médias** : 119 sources pour les 50 médias. Chaque page a été rechargée par un
  script et la citation y a été retrouvée mot pour mot (119 sur 119, avec un témoin négatif).
  Les étiquettes invoquées par les 8 sources contradictoires ont été recontrôlées une à une.
- **Audience** : la figure D.21 de l'étude Cagé, Hengel, Hervé, Urvoy (p. 75) a été lue sur le
  PDF. Elle ne couvre que trois de nos médias.

## 1. Grille de positionnement

Chaque média de `config/medias.yaml` porte maintenant une liste `sources` (lien, type, date,
citation, verdict) et, pour trois chaînes, un bloc `audience`. Le chargeur refuse une source
sans lien, sans citation, ou qui « contredit » sans dire en quoi. Les sources sont aussi
listées sur la page Médias du site.

**Ce que valent ces sources.** Sur 119 : 49 descriptions par un tiers, 45 sur la propriété,
19 où le média parle de lui-même, 6 études ou décisions. 85 ne tranchent pas, 26 confirment,
8 contredisent. Deux sources reviennent beaucoup : Wikipédia (22) et les fiches eurotopics
(14). 32 médias n'ont ni ligne revendiquée ni étude de contenu. Les verdicts « confirme » et
« ne tranche pas » sont une première lecture ; seuls les « contredit » ont été recontrôlés.

**Médias pour lesquels une source contredit le classement actuel** (rien n'a été changé) :

| Média | Classement actuel | Ce que dit la source | Source |
|---|---|---|---|
| L'Humanité | gauche | « Political orientation: Far left » | fiche eurotopics |
| Le Nouvel Obs | centre-gauche | « Political orientation: Left-wing » | fiche eurotopics |
| Slate.fr | centre-gauche | « Political orientation: Liberal-conservative » | fiche eurotopics |
| France Inter | centre | 56 chroniques sur 64 notées « à gauche » | rapport Institut Thomas More, février 2026 |
| L'Express | centre-droit | « orienté politiquement au centre » | Wikipédia |
| CNews | droite | « chaîne […] privée d'extrême droite » | Wikipédia |
| Valeurs actuelles | droite | « classé à l'extrême droite » depuis 2012 | Wikipédia |
| Causeur | droite | « le plus souvent classé à l'extrême droite » depuis 2019 | Wikipédia |

Tous les écarts sont d'un cran, sauf Slate.fr. Le rapport Thomas More vient d'un think tank,
pas d'une université. Pour Valeurs actuelles et Causeur, une autre source confirme « droite »
(CB News, eurotopics).

**Changements récents à relire**, sans contradiction formelle :

- **Le Point** (inactif) : départ du directeur le 10 novembre 2026, sur fond de « volonté de
  changement de ligne éditoriale par rapport au Rassemblement national » (Ozap).
- **Capital** : contrôlé par Bolloré via Prisma ; clause de conscience ouverte fin 2025 parce
  que « la direction s'éloigne de la ligne éditoriale historique du titre » (Ozap).
- **Front Populaire** : racheté à 90 % par Lagardère Media News en août 2026 (Ozap).
- **Boulevard Voltaire, L'Incorrect** : aucune source lue n'emploie « extrême droite ».

**Audience (information, pas un critère).** Moyenne du public sur une échelle de 1 (très à
gauche) à 7 (très à droite), en 2020 : population 3,96 ; CNews 4,33 ; BFM TV 4,34 ; TF1 4,44.
Pour TF1, c'est le public de la chaîne, pas du site TF1 Info.

**Ce qui n'a pas pu être lu :**

- **Sondage Ifop pour Marianne (2022)** : non utilisé. Le site ifop.com échoue à la
  vérification du certificat TLS et marianne.net refuse les robots ; je n'ai rien contourné.
- **Cartes d'audience du Reuters Institute** : image seule, sans valeurs, en 2017 comme en 2019.
- **Pages « qui sommes-nous »** de L'Humanité, Mediapart, Libération, Le Nouvel Obs,
  Alternatives Économiques, L'Express, L'Opinion, Valeurs actuelles, Slate : accès refusé
  aux robots.

## 2. Angles morts : asymétrie par pôle

Pour chaque sujet : part des médias de gauche qui le couvrent, moins part des médias de
droite. Le dénominateur est le nombre de médias du bord qui ont publié dans la fenêtre (7 à
gauche et 12 à droite le 11 novembre ; Basta et StreetPress n'avaient que 2 articles, deux
médias de gauche aucun). Centre-gauche et centre-droit restent hors des bords. La page classe
les sujets par écart décroissant et donne le détail par pôle.

**Seuil retenu : 25 points d'écart, et au moins 2 médias du bord dominant.** Un seul média de
gauche fait bouger la part de 14 points (1 sur 7), un seul média de droite de 8 points. À
25 points, il faut l'équivalent de deux médias de gauche ou de trois de droite : le choix d'un
seul média ne suffit pas à créer un écart. La condition « 2 médias » protège du cas où un bord
n'aurait que trois ou quatre médias présents. Les deux valeurs sont dans
`couverture.asymetrie` de `config/reglages.yaml`.

**Comparaison** : 2 angles morts avec l'ancien seuil (aucun après le resserrement des bords),
6 sujets en asymétrie avec la nouvelle mesure, tous parmi les 30 premiers. Relus un par un :

| Écart | Sujet | Gauche | Droite | Lecture |
|---|---|---|---|---|
| 33 points | Mbappé forfait contre l'Italie | 0 sur 7 | 4 sur 12 | Sport : les médias de gauche suivis n'en publient presque pas. Effet de rubrique. |
| 29 points | Grève générale en Espagne | 2 sur 7 | 0 sur 12 | Libération et L'Humanité. Écart qui a un sens éditorial. |
| 25 points | Christophe Gleizes détenu en Algérie | 0 sur 7 | 3 sur 12 | CNews, Europe 1, Sud Radio. Plausible, mais trois médias de centre-gauche en parlent aussi. |
| 25 points | 5 000 places en licence | 0 sur 7 | 3 sur 12 | Même dépêche reprise par Europe 1, Sud Radio et Le Figaro. Effet de volume. |
| 25 points | Affaire Nvidia | 0 sur 7 | 3 sur 12 | CNews, Europe 1, Atlantico, sous l'angle de l'espionnage chinois. Écart qui a un sens. |
| 25 points | Menace iranienne sur les bases américaines | 0 sur 7 | 3 sur 12 | Dépêche reprise. Effet de volume. |

Juste sous le seuil : la pétition contre CNews (24 points, 4 médias de chaque bord) et la
candidature d'Éric Zemmour (19 points).

## 3. Contrôle du positionnement par la couverture

Chaque passage archive dans `data/couvertures/` tous les sujets du jour (80 le 11 novembre,
pas seulement les 30 publiés) avec les médias qui les couvrent. `make affinites` calcule la
proximité de couverture entre médias (cosinus sur les ensembles de sujets), la moyenne avec
chaque bloc, et signale un média plus proche d'un autre bloc que du sien. Le rapport va dans
`data/affinites.md`.

Le calcul est testé sur des historiques fabriqués (7 tests). Sur la seule édition disponible
il tourne et se déclare lui-même « historique insuffisant » : je n'en tire aucune conclusion
et n'en rapporte aucun chiffre ici. Il lui faut 14 éditions (`affinites.min_editions`).

## Ce qui marche moins bien

- **L'asymétrie mesure aussi le volume et les rubriques.** La mesure par pôle corrige le
  déséquilibre d'effectif, pas celui de taille : CNews publie 102 articles dans la fenêtre,
  Europe 1 51, quand cinq des sept médias de gauche en publient 12 ou moins et ne couvrent ni
  le sport ni les dépêches. Sur les 6 sujets, 3 s'expliquent ainsi et 2 ont un sens éditorial.
- **Deux « gauche » sur la même page.** La barre de couverture compte le centre-gauche à
  gauche ; le détail par pôle ne le compte pas. Pour Christophe Gleizes, la page affiche
  « Gauche : 3 médias » et « Médias de gauche : 0 sur 7 ». C'est expliqué en note, mais prête
  à confusion.
- **Sources de qualité inégale.** Beaucoup de Wikipédia et de fiches eurotopics, peu d'études.
  Quatre des huit contradictions reposent sur Wikipédia seule.
- **Contrôle par la couverture** : rien à en dire avant deux semaines d'éditions.

## Décisions prises sans validation préalable

- Dénominateur de l'asymétrie : les médias du bord ayant publié dans la fenêtre, pas les
  médias actifs du fichier (un média qui n'a rien publié ne peut pas couvrir le sujet).
- Une édition garde les 30 sujets les plus couverts, plus jusqu'à 8 sujets asymétriques
  trouvés au-delà (aucun le 11 novembre).
- Les sources sont affichées sur la page Médias, sans leur verdict.
- Contrôle par la couverture : proximité en cosinus, comparaison aux trois blocs affichés,
  seuils de 14 éditions, 20 sujets par média et 0,05 d'avance.
- Option `--reference` pour rejouer une édition passée sans collecte.

## Questions pour Franck

1. **Wikipédia, eurotopics et le rapport Thomas More sont-ils des sources recevables** pour
   contredire un classement ? Si non, il reste zéro contradiction solide.
2. **Asymétrie et volume** : faut-il corriger l'effet de rubrique (par exemple écarter le
   sport, ou ne compter dans chaque bord que les médias généralistes) ? Je n'ai rien fait.
3. **Deux définitions de « gauche »** sur la page Angles morts : garder les deux avec la note,
   ou aligner la barre de couverture sur les bords stricts pour cette page ?
4. **Sondage Ifop** : si vous déposez le PDF du rapport dans le dépôt, je peux le lire et
   remplir la colonne audience pour la presse et les radios.

## Ce qui reste à faire

- Relire `config/medias.yaml`, en commençant par les huit médias du tableau.
- Laisser tourner `make quotidien` deux semaines avant de lancer `make affinites`.
- Choisir le LLM, déployer, installer le timer : inchangé depuis le premier bilan.
