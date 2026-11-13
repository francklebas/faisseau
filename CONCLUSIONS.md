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
- **Boulevard Voltaire** (classé extrême droite) : aucune des deux pages lues n'emploie ce terme.
  **L'Incorrect** (classé extrême droite) : Public Sénat le dit lancé par des personnalités
  « entre droite et extrême droite ».

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

---

# Suite du 12 novembre, tard — sources recoupées, sport et dépêches écartés, cinq blocs

Trois commits de plus, rien de poussé ni de déployé. Édition du 11 novembre rejouée, site
régénéré. Aucun positionnement modifié.

## Ce qui a été vérifié

- **Tests** : les 52 passent ; vérification de types du site sans erreur ; 38 pages générées ;
  page Angles morts contrôlée sur capture.
- **Sources ajoutées** : 22, chacune rechargée et sa citation retrouvée mot pour mot. Le
  fichier en compte 141.

## 1. Sources : aucune ne suffit seule

Règle inscrite en tête de `config/medias.yaml`, et dans le chargeur pour Wikipédia : une page
Wikipédia ne peut ni confirmer ni contredire un classement (7 verdicts ramenés à « ne tranche
pas »). Je suis remonté aux sources qu'elle cite pour les quatre médias concernés.

| Média | Classement | Ce que disent les sources d'origine lues |
|---|---|---|
| CNews | droite | Aucune ne la dit « d'extrême droite ». France 24 : « ancrée très à droite » ; RSF : invités « majoritairement de droite et d'extrême-droite » ; le Conseil d'État et l'Arcom ne la qualifient pas. |
| Valeurs actuelles | droite | franceinfo écrit « journal d'extrême-droite » le 27 avril 2021 et « hebdomadaire conservateur » le 10 mai 2021 ; Public Sénat : « ultraconservateur » ; Acrimed : « droite décomplexée ». |
| Causeur | droite | franceinfo : « magazine d'extrême droite » (2023, en incise) ; Politis : « mensuel réactionnaire » (2017) ; Acrimed : « droite décomplexée » (2017) ; eurotopics : « très vers la droite ». |
| L'Express | centre-droit | Rien de lu : la seule note de Wikipédia renvoie à La Montagne, qui refuse les robots. |

- **Slate.fr** : l'étiquette « libéral-conservateur » d'eurotopics reste isolée. Les fiches
  française et allemande disent la même chose (une seule source), sans justification, et la
  fiche se contredit sur l'actionnariat. Aucune autre source lue ne qualifie Slate.fr.
- **France Inter** : le rapport Thomas More est une source engagée (son auteur dit « nous ne
  sommes pas neutres ») et la note est attribuée par une IA « sans intervention humaine ». Les
  contrepoids lus : la commission d'enquête parlementaire, une mise en demeure de l'Arcom sur
  les horaires de parole du RN, Acrimed (2008, conclusion inverse, codage maison lui aussi), le
  baromètre de Radio France. Aucun ne mesure la ligne de façon indépendante.

**Il reste six sources marquées « contredit »**, aucune corroborée par une seconde source
indépendante : trois fiches eurotopics (L'Humanité, Le Nouvel Obs, Slate.fr), le rapport Thomas
More (France Inter) et deux articles de franceinfo (Valeurs actuelles, Causeur). Comme vous le
notez, cinq sur six portent sur le degré, pas sur le bord ; seule Slate.fr changerait de côté,
sur une étiquette douteuse.

**Une précision sur la grille** : elle a déjà les catégories « extrême gauche » et « extrême
droite ». Boulevard Voltaire et L'Incorrect sont classés extrême droite ; aucun média n'est
classé extrême gauche. La question n'est donc pas d'ajouter ces catégories mais de savoir à
qui les appliquer, ou s'il faut cesser de les afficher.

**Ce qui n'a pas pu être lu** : la plupart des articles du Monde, de Libération, du Figaro et
de L'Obs que Wikipédia cite, et deux études universitaires (Labarre 2024 sur CNews ; Marty,
Ouakrat et Pacouret 2022 sur Valeurs actuelles). Accès refusé aux robots, non contourné.

## 2. Effet de volume : sport et dépêches écartés

- **Sport** : un sujet dont au moins la moitié des articles est en rubrique sportive (segment
  de l'adresse : `/sport/`, `/football/`…) n'est pas classé. 7 sujets sur 80 le 11 novembre,
  dont 2 parmi les 30 publiés.
- **Dépêches** : un article dont le titre est repris presque mot pour mot par un autre média
  du sujet (75 % de mots communs) est traité comme une dépêche. Un média ne compte pour son
  bord que s'il publie au moins un article au titre propre. La page l'indique (« plus 1 par
  dépêche reprise »).

J'ai choisi le niveau de l'article plutôt que celui du sujet : un sujet majeur contient souvent
la dépêche et des articles originaux, et l'écarter en bloc aurait fait disparaître l'interdiction
de territoire russe (72 % de titres repris) sans attraper les 5 000 places en licence (44 %).

**Résultat : 3 sujets en asymétrie au lieu de 6.**

| Écart | Sujet | Gauche | Droite | Lecture |
|---|---|---|---|---|
| 29 points | Grève générale en Espagne | 2 sur 7 | 0 sur 12 | Inchangé. Libération et L'Humanité. |
| 25 points | Christophe Gleizes détenu en Algérie | 0 sur 7 | 3 sur 12 | Inchangé. Trois médias de centre gauche en parlent ; la barre le montre maintenant. |
| 25 points | Affaire Nvidia | 0 sur 7 | 3 sur 12 | Inchangé. CNews, Europe 1, Atlantico. |

Sortis : Mbappé (sport), les 5 000 places en licence (les trois médias de droite publiaient
le même titre), la menace iranienne (Le Figaro reprenait le titre de CNews ; il reste 2 médias
sur 12, sous le seuil).

## 3. Les deux « gauche » : cinq blocs

La barre de couverture a cinq segments : gauche, centre gauche, centre, centre droit, droite.
Les deux bords comparés sont les blocs gauche et droite, donc la barre et le détail comptent
les mêmes médias. Le réglage séparé `couverture.asymetrie.bords` a disparu. La page Médias et
la page d'un sujet suivent les cinq blocs.

## 4. Ifop

Téléchargement tenté une fois : le site ifop.com échoue à la vérification de son certificat.
Je n'ai pas forcé. En attente, comme convenu.

## Ce qui marche moins bien

- **La détection des dépêches est grossière.** Elle ne voit que les titres identiques : une
  dépêche retitrée passe pour un article propre (Europe 1 sur l'Iran). À l'inverse, deux
  médias qui choisissent le même titre factuel sont écartés à tort.
- **Le sport se reconnaît à l'adresse.** Un média sans rubrique dans ses adresses y échappe.
- **Trois sujets sur un seul jour** : trop peu pour dire si la mesure est juste.
- **Sources** : la presse nationale et les revues universitaires, qui portent l'essentiel des
  qualifications, restent fermées aux robots.

## Décisions prises sans validation préalable

- Dépêches écartées article par article, pas sujet par sujet (raison ci-dessus).
- Seuils : moitié des articles pour le sport, 75 % de mots communs pour un titre repris.
- Les verdicts Wikipédia « confirme » ont été ramenés à « ne tranche pas » comme les
  « contredit » : la règle vaut dans les deux sens.
- Couleurs des deux nouveaux segments : teintes intermédiaires, contraste AA vérifié en clair.
- Le contrôle par la couverture (`make affinites`) compare maintenant aux cinq blocs.

## Questions pour Franck

1. **Étiquettes extrêmes** : garder « extrême droite » pour Boulevard Voltaire et L'Incorrect,
   l'étendre, ou ne plus afficher que cinq blocs avec les descriptions sourcées à côté ? Le
   calcul ne change pas dans les trois cas : gauche et extrême gauche sont déjà dans le même
   bloc, droite et extrême droite aussi.
2. **Afficher les descriptions sourcées plutôt qu'une étiquette maison** : sur la page Médias
   seulement, ou partout où un média est nommé ? La page Médias liste déjà les sources ; elle
   n'affiche pas encore les citations.
3. **Sources fermées aux robots** : voulez-vous déposer vous-même les articles ou études clés
   (par exemple l'étude Quaderni 2022 sur Valeurs actuelles), comme pour l'Ifop ?

---

# Bilan du 13 novembre

## Ce qui a été vérifié

- La clé Mistral de `.env` était bien lue et valide ; le fournisseur restait `koboldcpp` parce que rien, hors `REVUE_LLM`, ne le changeait. Mistral est maintenant le défaut, KoboldCpp un repli à demander (`make quotidien LLM=koboldcpp`), sans repli automatique.
- Édition du 13 novembre, mêmes 31 sujets pour les deux modèles (fenêtre fixée à 11 h 56) : Gemma 3 4B, 149 faits en 27 min ; Mistral Small (`mistral-small-2603`), 217 faits en 2 min 40 pour 35 596 jetons en entrée et 11 300 en sortie, soit environ 0,012 $ au tarif lu (0,15 $ / 0,60 $ par million).
- 54 tests passent.

## Faits atomiques

Consigne : fait central minimal, chaque précision dans un fait séparé, noms et chiffres tels qu'écrits, pas de synthèse entre sources, faits lisibles seuls. La consigne entre dans la clé de cache.

| Étape (Mistral) | Communs | Recoupés | Isolés | Sujets sans fait commun |
|---|---|---|---|---|
| Ancienne consigne | 37 | 70 | 110 | 10 |
| Faits atomiques | 73 | 95 | 117 | 0 |
| Consigne resserrée | 75 | 93 | 126 | 0 |
| + contrôle du niveau commun (0,65) | 28 | 110 | 156 | 7 |

## Contrôle du niveau commun

Un fait n'est commun que par des sources dont une phrase en est proche par le sens (`seuil_commun`, Solon) ; sinon il ne garde que ces sources-là.

Calibrage sur 77 paires fait/source relues : pas de coupure nette, contrairement au 0,75 d'hier. Sources qui n'énoncent pas le fait : 4 sur 22 au-dessus de 0,65, 8 sur 22 entre 0,55 et 0,65, 19 sur 33 en dessous. Un fait court comparé à une phrase longue obtient un score bas même quand la phrase le contient.

À 0,65, 47 faits communs sur 75 tombent. Certains à raison (« Jensen Huang est le fondateur de Nvidia » était commun avec 19 médias sur 19 par simple présence des mots ; « Kevin Tessier a été arrêté », 10 sur 11). D'autres à tort (« L'équipe de France de football a été battue par l'Italie » devient une affirmation isolée ; « Marion Wagon a disparu » aussi). À 0,55 : 24 tombent, 51 restent.

Les 28 faits communs restants ont été relus, 14 avec leurs sources : aucun faux ; un surévalué (« des établissements ont été évacués », énoncé par 2 sources sur 6).

## Ce qui marche moins bien

- Le contrôle lexical rattache trop facilement un fait court : c'est la vraie cause des faux faits communs, et les faits atomiques l'aggravent.
- La proximité de phrase à phrase n'est pas la bonne mesure pour dire qu'une phrase longue contient un fait court.
- Un fait déclassé faute de sources proches s'affiche « isolé » alors que plusieurs médias le disent.

## Décisions prises sans validation préalable

- Seuil 0,65 retenu malgré l'absence de coupure nette.
- Un fait commun sans aucune source proche garde sa source la plus proche et devient isolé.

## Questions pour Franck

1. Garder 0,65, passer à 0,55, ou changer de mesure (découpage des phrases en propositions, ou modèle d'implication textuelle, nouvelle dépendance) ?
2. Un fait déclassé doit-il perdre ses autres sources, au risque de paraître isolé à tort ?

---

# Bilan du 13 novembre, suite : contrôle du niveau commun par implication

## Ce qui a été vérifié

- Les 77 paires relues sont dans `tests/donnees/paires_fait_source.json` avec leur verdict. Deux verdicts corrigés à la relecture (n° 51, lu d'abord sur un affichage tronqué ; n° 74, hôpital non nommé) : 46 paires où la phrase énonce le fait, 31 où elle ne l'énonce pas. Le jeu ne contient aucune paire de proximité Solon supérieure à 0,75.
- Comparaison rejouable : `scripts/comparer_controles.py`.
- 55 tests passent. Édition du 13 novembre rejouée sans appel à Mistral (cache).

## Comparaison sur les 77 paires

| Méthode | Faux positifs (sur 31) | Faux négatifs (sur 46) | Erreurs |
|---|---|---|---|
| Proximité, phrase entière ≥ 0,55 | 12 | 14 | 26 |
| Proximité, phrase entière ≥ 0,65 | 5 | 29 | 34 |
| Proximité par propositions ≥ 0,55 | 14 | 3 | 17 |
| Proximité par propositions ≥ 0,65 | 7 | 22 | 29 |
| Implication mDeBERTa-v3 multilingue ≥ 0,5 | 3 | 11 | 14 |
| Implication MiniLMv2 multilingue ≥ 0,5 | 4 | 14 | 18 |

Méthode retenue : implication, `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, seuil 0,5 (le seuil par défaut, non ajusté sur le jeu ; ajusté à 0,12 il donnerait 5 et 5, chiffre optimiste). Elle n'est appliquée qu'aux candidats au niveau commun, sur la phrase de chaque source la plus proche du fait.

## Édition du 13 novembre

| | Avant contrôle | Proximité 0,65 | Implication |
|---|---|---|---|
| Faits communs | 75 | 28 | 32 |
| Recoupés | 93 | 110 | 120 |
| Isolés | 126 | 156 | 136 |
| Sujets sans fait commun | 0 | 7 | 10 |

Des 75 candidats : 32 restent communs, 37 redescendent, 6 sont retirés faute de source qui les affirme.

Relecture des 32 faits communs avec la phrase de chacune de leurs 190 sources :

- aucun fait faux ;
- 9 sources retenues à tort (par exemple « Jensen Huang désormais sur un siège éjectable » pour la démission) ;
- trois faits ne tiennent leur niveau commun qu'à une de ces sources (saisine du CSM par Gérald Darmanin, candidature annoncée de Teddy Riner, « sanctions à la hauteur » en Île-de-France). Les trois sont vrais.

## Ce qui marche moins bien

- **Des faits vrais sont retirés.** Les six faits retirés étaient tous énoncés par au moins un média ; « Kevin Tessier est le suspect principal » l'est par 7. Le modèle ne voit qu'une phrase : « Il nie… » ne lui dit pas qui nie.
- **Le modèle est strict sur chaque détail.** « Jordan Bardella a porté plainte contre X pour faux et usage de faux » passe de 7 médias à 1, parce que la plupart des titres ne disent pas « contre X ». « L'équipe de France de football a été battue par l'Italie » passe de 9 à 3. Les faits de Mistral ne sont pas encore assez atomiques pour ce contrôle.
- **Durée** : environ 8 minutes de plus par édition sur 4 fils (492 s au total sans appel au LLM).
- 10 sujets sur 31 n'ont plus de fait commun.

## Décisions prises sans validation préalable

- Seuil 0,5 plutôt que le seuil ajusté 0,12.
- Le modèle juge la phrase la plus proche du fait dans chaque article, pas l'article entier : c'est la condition dans laquelle les 77 paires ont été relues.
- Un candidat commun qu'aucune source n'affirme est retiré (conséquence de « un fait n'affiche que les sources qui l'affirment »).
- Les sources d'un fait resté commun sont filtrées elles aussi.
- `transformers` ajouté aux dépendances déclarées (il était déjà installé par sentence-transformers).

## Questions pour Franck

1. Faut-il donner au modèle le titre et l'extrait entiers de l'article plutôt qu'une phrase ? Cela réglerait les pronoms, mais les 77 paires devraient être relues dans cette condition.
2. Un candidat commun sans aucune source qui l'affirme : le retirer (état actuel) ou le garder avec ses sources d'origine à un niveau inférieur ?
3. Huit minutes de plus par édition, est-ce acceptable ?

