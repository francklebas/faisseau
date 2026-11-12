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

Reste à faire, dans l'ordre : la grille de positionnement des médias adossée à des sources
externes.
