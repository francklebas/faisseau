<script setup lang="ts">
const { data: edition } = await useFetch('/api/editions/derniere')

useSeoMeta({
  title: 'Méthode et limites',
  description: 'Comment la Revue du matin regroupe les articles, extrait les faits et mesure la couverture, et ce qu\'elle ne sait pas faire.',
})
</script>

<template>
  <div class="prose">
    <h1 class="titre-page">Méthode et limites</h1>
    <p class="chapo">
      La Revue du matin ne choisit pas « les bons médias ». Elle en lit beaucoup, de tous bords, et montre
      ce qui se recoupe et ce qui ne se recoupe pas. Voici exactement comment, et où cela peut se tromper.
    </p>

    <h2>Ce qui est lu</h2>
    <p>
      Uniquement les flux RSS que les médias publient eux-mêmes : le titre de chaque article, un extrait
      de quelques lignes et le lien. Le texte des articles n'est jamais récupéré ni conservé, et les
      contenus payants ne sont pas contournés. Pour lire un article, il faut aller sur le site du média.
    </p>

    <h2>Comment les sujets sont formés</h2>
    <p>
      Chaque titre accompagné de son extrait est transformé en vecteur par un modèle de langue qui tourne
      sur notre machine. Les articles dont les vecteurs sont proches sont regroupés. Un groupe devient un
      sujet lorsqu'au moins trois médias différents y contribuent. Les sujets sont classés par nombre de
      médias, sans intervention humaine.
    </p>

    <h2>Comment les faits sont extraits</h2>
    <p>
      Pour chaque sujet, un modèle de langue lit les titres et extraits et propose une liste de faits, en
      indiquant quels articles les énoncent. Ce traitement a lieu une seule fois par sujet. Un programme
      vérifie ensuite chaque proposition :
    </p>
    <ul>
      <li>
        une source n'est conservée que si son texte contient bien les mots, les noms propres et les chiffres du
        fait, ou si l'une de ses phrases dit la même chose autrement, chiffres identiques ;
      </li>
      <li>un fait dont aucune source ne résiste à ce contrôle n'est pas publié ;</li>
      <li>un article qui énonce clairement un fait est ajouté à ses sources même si le modèle l'avait oublié ;</li>
      <li>le classement d'un fait dépend du nombre de médias distincts, jamais de l'avis du modèle.</li>
      <li>
        un fait n'est dit « commun » que si, chez assez de médias, une phrase le dit de façon proche par le
        sens ; sinon il redescend, et seuls ces médias-là restent cités.
      </li>
    </ul>
    <p>Trois niveaux en résultent :</p>
    <ul>
      <li><strong>Fait commun</strong> : rapporté par au moins la moitié des médias qui couvrent le sujet.</li>
      <li><strong>Fait recoupé</strong> : rapporté par au moins deux médias.</li>
      <li><strong>Affirmation isolée</strong> : relevée chez un seul média.</li>
    </ul>

    <h2>Couverture et angles morts</h2>
    <p>
      Chaque média est rangé dans un bloc — gauche, centre gauche, centre, centre droit ou droite — selon un
      <NuxtLink to="/medias">classement public et justifié</NuxtLink>. Pour chaque sujet, on compte les
      médias de chaque bloc, un média ne comptant qu'une fois quel que soit son nombre d'articles.
    </p>
    <p>
      La page <NuxtLink to="/angles-morts">Angles morts</NuxtLink> compare ensuite les deux bords. Pour
      chaque sujet, on calcule la part des médias de gauche qui en parlent et la part des médias de droite
      qui en parlent, parmi ceux qui ont publié ce jour-là. On compare des parts et non des nombres, parce
      que les deux bords ne comptent pas autant de médias. Les sujets sont classés par écart décroissant.
      Un écart n'est affiché qu'à partir de 25 points et de deux médias du bord qui domine : en dessous, le
      choix d'un seul média suffirait à le créer.
    </p>
    <p>
      Deux cas sont écartés parce qu'ils mesurent autre chose qu'un choix de traitement. Les sujets de
      sport ne sont pas classés : on les reconnaît à la rubrique des articles, et tous les médias suivis
      n'ont pas de rubrique sportive. Un article dont le titre est repris presque mot pour mot par un autre
      média est traité comme une dépêche d'agence : un média ne compte pour son bord que s'il publie au
      moins un article au titre propre.
    </p>
    <p>
      Pour cette comparaison, seuls les blocs gauche et droite comptent. Les médias classés centre-gauche,
      centre ou centre-droit ont leur propre segment dans la barre de couverture et n'appartiennent à
      aucun bord : deux généralistes modérés ne suffisent pas à faire pencher un sujet. Un écart ne dit rien de l'importance du sujet ni d'une
      intention : les médias des deux bords n'ont ni la même taille ni les mêmes rubriques.
    </p>

    <h2>Ce que cela ne sait pas faire</h2>
    <ul>
      <li>
        <strong>« Commun » ne veut pas dire « vrai ».</strong> Plusieurs médias peuvent reprendre la même
        dépêche ou la même erreur. La revue mesure l'accord entre sources, pas l'exactitude.
      </li>
      <li>
        <strong>« Isolé » ne veut pas dire « faux » ni « exclusif ».</strong> Seuls les titres et extraits
        sont comparés : un autre média peut donner la même information plus bas dans son article.
      </li>
      <li>
        <strong>La vérification reste approximative.</strong> Elle compare des mots et une mesure de
        proximité de sens, réglée prudemment : une reformulation très libre peut encore échapper au
        recoupement, et une négation peut passer inaperçue.
      </li>
      <li>
        <strong>Le modèle de langue se trompe.</strong> Il peut mal formuler un fait ou manquer une nuance.
        Les liens vers les sources sont là pour vérifier.
      </li>
      <li>
        <strong>Le classement des médias est une simplification</strong> et, pour l'instant, une proposition
        non validée. Il pèse directement sur les angles morts.
      </li>
      <li>
        <strong>Un flux RSS n'est pas tout un média.</strong> Certains titres n'en proposent pas ou le
        ferment aux robots ; ils sont absents de la revue.
      </li>
    </ul>

    <h2>Vie privée</h2>
    <p>
      Le site est fait de pages statiques. Il n'exécute aucun script, ne dépose aucun cookie, ne charge
      rien depuis un autre domaine et ne mesure pas son audience. Il n'y a ni compte ni publicité.
    </p>

    <template v-if="edition">
      <h2>Cette édition</h2>
      <ul>
        <li>Générée le {{ dateLongue(edition.genere_le) }} à {{ heure(edition.genere_le) }}.</li>
        <li>{{ pluriel(edition.stats.nb_articles, 'article') }} de {{ pluriel(edition.stats.nb_medias_actifs, 'média') }} sur {{ edition.stats.fenetre_heures }} heures.</li>
        <li>Modèle de regroupement : {{ edition.stats.modele_embeddings }}.</li>
        <li>Extraction des faits : {{ edition.stats.llm }}.</li>
        <li v-if="edition.stats.flux_en_erreur.length">Flux en erreur lors de ce passage : {{ edition.stats.flux_en_erreur.join(', ') }}.</li>
        <li v-else>Tous les flux ont répondu lors de ce passage.</li>
      </ul>
    </template>
  </div>
</template>
