# Revue du matin

Un équivalent français de Ground News. Chaque jour, le pipeline lit les flux RSS d'une
quarantaine de médias français, regroupe les articles par sujet et produit un site statique
qui montre, pour chaque sujet :

- les **faits communs** (rapportés par la majorité des médias) et les **faits recoupés** (au moins deux) ;
- les **affirmations isolées** (un seul média), signalées comme telles ;
- la **répartition de la couverture** entre gauche, centre et droite ;
- les **angles morts** : les sujets que les médias de gauche et de droite couvrent le plus inégalement.

Chaque fait affiché renvoie aux articles qui l'énoncent. Le site ne contient ni compte, ni
cookie, ni script, ni ressource tierce.

## Lancer

Prérequis : [uv](https://docs.astral.sh/uv/), Node ≥ 20 avec pnpm, make. Python 3.12 est
installé par uv si besoin.

```sh
make
```

Cette commande installe les dépendances, collecte les flux, regroupe, extrait les faits,
génère le site et le sert sur <http://localhost:4173>. Le premier passage télécharge le
modèle d'embeddings (1,1 Go) et encode tous les articles (3 à 4 minutes sur un portable) ;
les suivants n'encodent que les nouveaux.

Sans LLM joignable, la revue est quand même produite (sujets, couverture, angles morts),
avec un avertissement et sans faits. Pour les faits, voir « Extraction des faits ».

| Commande | Effet |
|---|---|
| `make` | tout, puis serveur local |
| `make quotidien` | pipeline + génération du site, sans serveur (à planifier) |
| `make test` | tests (le test sur vrai modèle est sauté si le modèle n'est pas en cache) |
| `make flux` | état de chaque flux RSS |
| `make sujets` | affiche les sujets regroupés, sans LLM (pour régler un seuil) |
| `uv run revue executer --reference 2026-11-11T21:55:00+01:00` | rejoue une édition passée à partir de la base, sans collecte |
| `make affinites` | compare la couverture des médias sur l'historique et signale ceux qui s'écartent de leur bloc (ne classe rien) |
| `make comparer-embeddings` | compare Solon et E5 sur l'échantillon étiqueté |
| `make deployer` | publie sur Cloudflare (jamais lancé automatiquement) |

## Configuration

- **`config/medias.yaml`** : les médias, leurs flux, leur positionnement et sa justification.
  Aucun classement n'existe ailleurs. **Tous les positionnements sont marqués `a_valider`** :
  ce sont des propositions rédigées de mémoire, à relire une par une. Tant qu'un média est
  `a_valider`, le site l'affiche comme provisoire. Passer `statut: valide` après relecture.
  Chaque média porte aussi des `sources` externes sur sa ligne éditoriale (lien, citation,
  verdict) et parfois un bloc `audience`, donné pour information : le format est décrit en tête
  du fichier.
- **`config/reglages.yaml`** : fenêtre de collecte, modèle d'embeddings et seuils, définition
  des trois blocs (quelle nuance va dans quel bloc), seuils d'asymétrie, fournisseur LLM.
- **`.env`** (voir `.env.example`) : clé Mistral et surcharges ponctuelles.

### Extraction des faits

Deux fournisseurs, même protocole (API compatible OpenAI) :

```sh
# Mistral
echo 'REVUE_LLM=mistral' >> .env && echo 'MISTRAL_API_KEY=…' >> .env

# Modèle local : lancer KoboldCpp, puis (défaut : http://localhost:5001/v1)
./koboldcpp --model gemma-3-4b-it-Q4_K_M.gguf --contextsize 8192
```

`REVUE_LLM=aucun` désactive l'extraction. La réponse du LLM est mise en cache par sujet : un
sujet dont les articles n'ont pas changé n'est jamais retraité, et rien n'est calculé à la
lecture.

### Passage quotidien

```sh
# systemd (utilisateur) — tous les jours à 6 h
cp deploy/revue-du-matin.* ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now revue-du-matin.timer

# ou cron
0 6 * * * cd ~/workspace/faisseau && make quotidien >> data/quotidien.log 2>&1
```

`make quotidien` échoue (et ne remplace pas l'édition précédente) si le LLM configuré est
injoignable. Le site généré est dans `web/.output/public`, déployable tel quel :
`make deployer` (Cloudflare Workers Static Assets, `web/wrangler.jsonc`) ou glisser le dossier
dans Cloudflare Pages. Les en-têtes de sécurité sont dans `web/public/_headers`.

## Comment ça marche

```
flux RSS ──► collecte ──► embeddings ──► regroupement ──► LLM ──► vérification ──► JSON ──► Nuxt generate
            (titre,       (CPU, cache)   (CAH, liaison    (1 appel   (code)         data/      pages statiques
             extrait,                     moyenne)         par sujet)                editions/
             lien)
```

| Étape | Fichier | Choix |
|---|---|---|
| Collecte | `revue/collecte.py` | `feedparser` + `httpx`. On garde titre, lien, date et résumé tronqué à 400 caractères. `content:encoded` (parfois l'article entier) n'est jamais lu. |
| Stockage | `revue/base.py` | SQLite (`data/revue.db`), purge à 14 jours. |
| Embeddings | `revue/plongements.py` | `sentence-transformers` sur CPU, 4 fils, vecteurs en cache. |
| Regroupement | `revue/regroupement.py` | Classification ascendante hiérarchique, distance cosinus, **liaison moyenne** : deux groupes ne fusionnent que si leurs articles se ressemblent en moyenne, ce qui empêche un article « pont » de souder deux sujets voisins. Sujet = au moins 3 médias distincts. |
| Faits | `revue/faits.py` | Le LLM propose faits et sources ; le code contrôle chaque rattachement (mots, noms propres, chiffres), retire les sources non fondées, ajoute les sources oubliées — y compris celles qui disent la même chose autrement, repérées par Solon — et calcule seul le statut à partir du nombre de **médias** distincts. |
| Couverture | `revue/couverture.py` | Comptage par bloc, un média = une voix. Asymétrie : part des médias de gauche qui couvrent le sujet moins part des médias de droite, parmi ceux qui ont publié ce jour-là ; centre-gauche et centre-droit ne comptent pour aucun bord. Affichée à partir de 25 points d'écart et de 2 médias du bord dominant. Les sujets de sport (rubrique dans l'adresse des articles) ne sont pas classés, et un média qui ne publie qu'un titre repris d'un autre (dépêche) n'est pas compté. Une édition = les 30 sujets les plus couverts, plus jusqu'à 8 sujets asymétriques trouvés au-delà. |
| Site | `web/` | Nuxt 4, `nuxt generate`, **zéro JavaScript** côté lecteur (`features.noScripts`). |

### Solon ou E5 ?

`make comparer-embeddings` mesure les deux modèles sur `tests/donnees/titres_etiquetes.json`
(275 titres réels du 11 novembre 2026, rangés à la main en 25 sujets, mêlés à 1 500 autres
articles du jour). Résultat sur un ThinkPad T14s (4 fils) :

| | Solon-embeddings-base | multilingual-e5-small |
|---|---|---|
| AUC paires même sujet / sujets différents | 0,9996 | 0,9957 |
| Meilleur F1 du regroupement | 0,996 (seuil 0,47) | 0,983 (seuil 0,87) |
| Au seuil configuré : précision / rappel | 1,00 / 0,89 (0,58) | 1,00 / 0,94 (0,88) |
| Plage de seuils sans fausse fusion | large (0,47 → 0,70) | étroite (0,87 → 0,92) |
| Vitesse d'encodage | 8 textes/s | 28 textes/s |

Solon reste le défaut : il sépare mieux et son seuil est bien moins sensible (les similarités
d'E5 sont tassées entre 0,80 et 0,95, un centième de trop suffit à fusionner). E5 est une
alternative honnête sur une machine lente : `REVUE_EMBEDDINGS=e5-small`. Les seuils configurés
sont volontairement plus stricts que l'optimum mesuré : mieux vaut un sujet scindé en deux
qu'une fausse fusion.

### Contrôle du classement par la couverture

Chaque passage archive dans `data/couvertures/` tous les sujets du jour et les médias qui les
couvrent. `make affinites` mesure, sur cet historique, quels médias couvrent les mêmes sujets
que quels autres, et signale ceux qui sont plus proches d'un autre bloc que du leur
(`affinites` dans `reglages.yaml`). Ce n'est pas un classement : couvrir les mêmes sujets ne
dit rien de ce qu'on en écrit. Le rapport se déclare non concluant en dessous de 14 éditions.

## Limites

- **Recoupement approximatif.** La vérification compare des mots, des noms propres et des
  chiffres, puis rattrape les reformulations par le sens : un article est rattaché à un fait si
  une de ses phrases en est proche pour Solon (`seuil_faits`, 0,75) et que les chiffres
  concordent. Le seuil est prudent : sur les 30 sujets du 11 novembre, 9 sources ajoutées et
  4 faits « isolés » sur 66 reclassés, sans rattachement faux parmi ceux relus. À 0,72 on en
  reclasse 8, mais un rattachement sur 33 était faux (« en Irlande » rapproché d'« en Italie ») :
  le modèle voit mal un nom de lieu qui change. Une reformulation libre échappe donc encore au
  recoupement (faux « isolé »), une négation peut passer (faux « commun »), et les nombres en
  lettres au-delà de vingt (« cinq cents ») ne sont pas rapprochés des chiffres. Non calibré
  pour E5 : avec `e5-small`, le contrôle reste lexical.
- **Titres et extraits seulement.** Une « affirmation isolée » l'est dans les extraits RSS ;
  un autre média peut donner la même information dans le corps de son article. Le site le dit
  au lecteur. Certains flux (Le Parisien, L'Express) ne donnent que le titre.
- **Qualité du LLM.** Un modèle local de 4 Go (Gemma 3 4B) formule parfois mal un fait ou en
  propose de peu utiles ; le contrôle écarte les rattachements infondés mais ne réécrit pas.
  Mistral donne de meilleurs énoncés. Comptez ~1 min 30 par sujet en local sur CPU, soit
  45 minutes pour 30 sujets ; quelques secondes par sujet avec l'API.
- **Classement des médias non validé**, et en trois blocs seulement : les angles morts en
  dépendent directement. Le service public et la presse régionale sont rangés au centre faute
  de ligne revendiquée, ce qui se discute.
- **Flux absents.** Le Point, Les Échos, Marianne et RTL refusent les robots ou n'ont plus de
  flux public : ils sont listés `actif: false`, on ne contourne pas. Le Parisien ne date pas
  ses articles : ils prennent l'heure de première collecte.
- **Seuils calibrés sur une seule journée.** À revérifier avec `make comparer-embeddings`
  quand l'échantillon étiqueté aura grossi.
- **Pas de suivi d'un sujet d'un jour à l'autre** : chaque édition repart de la fenêtre des
  36 dernières heures.

## Décisions prises sans vous demander

- **Trois niveaux de faits** au lieu de deux (commun / recoupé / isolé) : « au moins deux
  médias » et « la majorité » ne disent pas la même chose, autant le montrer.
- **Pas de résumé rédigé par le LLM** : seul le titre du sujet est synthétisé (et remplacé par
  un titre d'article s'il s'écarte des textes). Tout le reste est un fait sourcé.
- **Les extraits RSS ne sont pas republiés** : le site affiche les titres et les liens ; les
  extraits ne servent qu'à l'analyse (droit voisin).
- **Pas d'API FastAPI** : le site est statique et lit des fichiers JSON à la génération ; une
  API n'aurait servi à rien et aurait ajouté un service à faire tourner.
- **Zéro JavaScript** dans les pages publiées. Une ligne à retirer dans `web/nuxt.config.ts`
  pour retrouver une application Vue hydratée le jour où il faudra de l'interactivité.
- **« France uniquement »** est compris comme : médias français, en français. L'actualité
  internationale qu'ils couvrent est incluse.
- **Centre-gauche compte à gauche, centre-droit à droite** dans la répartition affichée (comme
  Ground News), mais **pas pour les angles morts** : seuls gauche, droite et extrêmes y font un
  bord (`couverture.asymetrie.bords`).
- Le dossier s'appelle `faisseau/` comme demandé ; le dépôt git est initialisé, rien n'est commité.

## Accessibilité

Visée RGAA : HTML sémantique (landmarks, titres hiérarchisés, tableaux avec en-têtes), lien
d'évitement, focus visible, contrastes AA en clair et en sombre, aucune information portée par
la seule couleur (les blocs sont toujours nommés et chiffrés), texte en `rem`, pas d'animation.
Non fait : audit RGAA complet et test avec lecteur d'écran.

## Arborescence

```
config/      medias.yaml, reglages.yaml
revue/       le pipeline (collecte, base, plongements, regroupement, faits, couverture, edition, cli)
scripts/     comparer_embeddings.py
tests/       pytest + titres réels étiquetés
web/         site Nuxt 4 (app/, server/api/ pour lire les éditions à la génération)
deploy/      unités systemd pour le passage quotidien
data/        base SQLite et éditions générées (non versionné)
```
