<script setup lang="ts">
import type { ArticleSource, Bloc } from '#shared/types/revue'

const route = useRoute()
const { data } = await useFetch(`/api/sujets/${route.params.date}/${route.params.slug}`)
if (!data.value)
  throw createError({ statusCode: 404, statusMessage: 'Sujet introuvable', fatal: true })

const sujet = computed(() => data.value!.sujet)
const medias = computed(() => data.value!.medias)

useSeoMeta({
  title: () => sujet.value.titre,
  description: () => `${sujet.value.nb_medias} médias, ${sujet.value.nb_articles} articles : faits communs, affirmations isolées et répartition de la couverture.`,
})

const compte = computed(() => ({
  gauche: sujet.value.couverture.gauche.length,
  centre: sujet.value.couverture.centre.length,
  droite: sujet.value.couverture.droite.length,
}))
const nom = (id: string) => medias.value[id]?.nom ?? id
const articlesDu = (bloc: Bloc): ArticleSource[] => sujet.value.articles.filter(a => medias.value[a.media]?.bloc === bloc)
const classementProvisoire = computed(() => Object.values(medias.value).some(m => m.statut === 'a_valider'))
const aDesFaits = computed(() => sujet.value.faits_communs.length + sujet.value.faits_recoupes.length + sujet.value.affirmations_isolees.length > 0)
</script>

<template>
  <article v-if="data" class="sujet">
    <header class="sujet__entete">
      <p class="etiquette">
        <NuxtLink :to="`/editions/${data.date}`">Édition du {{ dateLongue(data.date) }}</NuxtLink>
      </p>
      <h1 class="titre-page">{{ sujet.titre }}</h1>
      <p class="sujet__meta">
        {{ pluriel(sujet.nb_medias, 'média') }} · {{ pluriel(sujet.nb_articles, 'article') }} ·
        du {{ dateHeure(sujet.premiere_publication) }} au {{ dateHeure(sujet.derniere_publication) }}
      </p>
      <p class="sujet__origine">
        <template v-if="sujet.titre_origine === 'synthese'">Titre de synthèse rédigé automatiquement à partir des titres des médias.</template>
        <template v-else>Titre repris de l'article le plus représentatif du sujet ({{ nom(sujet.articles[0]!.media) }}).</template>
      </p>
    </header>

    <section class="sujet__section" aria-labelledby="t-couverture">
      <h2 id="t-couverture" class="titre-section">Qui en parle</h2>
      <BarreCouverture class="sujet__barre" :couverture="compte" />
      <p v-if="sujet.angle_mort" class="note sujet__angle">
        <strong>Angle mort à {{ sujet.angle_mort.bord_absent }}.</strong>
        {{ Math.round(sujet.angle_mort.part * 100) }} % des médias qui couvrent ce sujet sont classés à
        {{ sujet.angle_mort.bord_dominant }} ; presque aucun à {{ sujet.angle_mort.bord_absent }}.
      </p>
      <div class="sujet__blocs">
        <div v-for="bloc in BLOCS" :key="bloc">
          <h3 class="sujet__bloc-titre">
            <span class="pastille" :class="`pastille--${bloc}`" aria-hidden="true" />{{ NOM_BLOC[bloc] }}
          </h3>
          <p v-if="sujet.couverture[bloc].length">{{ sujet.couverture[bloc].map(nom).join(', ') }}</p>
          <p v-else class="sujet__vide">Aucun média</p>
        </div>
      </div>
      <p v-if="classementProvisoire" class="sujet__avertissement">
        Classement des médias provisoire, en attente de validation. <NuxtLink to="/medias">Voir le classement et ses justifications</NuxtLink>.
      </p>
    </section>

    <template v-if="aDesFaits">
      <section v-if="sujet.faits_communs.length" class="sujet__section" aria-labelledby="t-communs">
        <h2 id="t-communs" class="titre-section">Faits communs</h2>
        <p class="sujet__aide">Rapportés par au moins la moitié des médias qui couvrent le sujet.</p>
        <ListeFaits :faits="sujet.faits_communs" :articles="sujet.articles" :medias="medias" :nb-medias="sujet.nb_medias" />
      </section>

      <section v-if="sujet.faits_recoupes.length" class="sujet__section" aria-labelledby="t-recoupes">
        <h2 id="t-recoupes" class="titre-section">Faits recoupés</h2>
        <p class="sujet__aide">Rapportés par plusieurs médias, sans être repris par la majorité.</p>
        <ListeFaits :faits="sujet.faits_recoupes" :articles="sujet.articles" :medias="medias" :nb-medias="sujet.nb_medias" />
      </section>

      <section v-if="sujet.affirmations_isolees.length" class="sujet__section sujet__section--isole" aria-labelledby="t-isoles">
        <h2 id="t-isoles" class="titre-section">Affirmations isolées</h2>
        <p class="sujet__aide">
          Relevées chez un seul média. Cela ne veut pas dire qu'elles sont fausses, ni que les autres ne les
          mentionnent pas dans le corps de leurs articles : seuls les titres et extraits sont comparés.
        </p>
        <ListeFaits :faits="sujet.affirmations_isolees" :articles="sujet.articles" :medias="medias" :nb-medias="sujet.nb_medias" isole />
      </section>
    </template>
    <p v-else class="note sujet__section">
      Les faits n'ont pas été extraits pour ce sujet
      ({{ sujet.extraction === 'indisponible' ? 'extraction désactivée lors de ce passage' : 'réponse du modèle inexploitable' }}).
      Le regroupement des articles et la répartition de la couverture restent valables.
    </p>

    <section class="sujet__section" aria-labelledby="t-articles">
      <h2 id="t-articles" class="titre-section">Les articles</h2>
      <p class="sujet__aide">Chaque lien mène à l'article sur le site du média.</p>
      <div class="sujet__articles">
        <div v-for="bloc in BLOCS" :key="bloc">
          <h3 class="sujet__bloc-titre">
            <span class="pastille" :class="`pastille--${bloc}`" aria-hidden="true" />{{ NOM_BLOC[bloc] }}
          </h3>
          <ul v-if="articlesDu(bloc).length" class="articles">
            <li v-for="article in articlesDu(bloc)" :key="article.n">
              <span class="articles__media">{{ nom(article.media) }}</span>
              <a :href="article.url" rel="external noopener">{{ article.titre }}</a>
              <time class="articles__date" :datetime="article.publie_le">{{ dateHeure(article.publie_le) }}</time>
            </li>
          </ul>
          <p v-else class="sujet__vide">Aucun article</p>
        </div>
      </div>
    </section>
  </article>
</template>

<style lang="scss" scoped>
@use '~/assets/scss/outils' as *;

.sujet {
  &__entete .etiquette { margin-bottom: 0.4rem; }

  &__meta,
  &__origine,
  &__aide,
  &__avertissement {
    font-family: var(--police-interface);
    font-size: 0.9rem;
    color: var(--encre-douce);
  }

  &__meta { margin-top: 0.9rem; }
  &__origine { margin-top: 0.2rem; font-style: italic; }
  &__aide { max-width: var(--mesure); margin-block: 0.3rem 1.25rem; }
  &__avertissement { margin-top: 1rem; }

  &__section { margin-top: 3rem; }

  &__barre {
    max-width: 40rem;
    margin-top: 1.1rem;
  }

  &__angle {
    max-width: 40rem;
    margin-top: 1rem;
  }

  &__blocs,
  &__articles {
    display: grid;
    gap: 1.25rem 2rem;
    margin-top: 1.25rem;
  }

  &__blocs {
    font-family: var(--police-interface);
    font-size: 0.95rem;

    @include a-partir-de($moyen) { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  }

  &__articles {
    @include a-partir-de($large) { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  }

  &__bloc-titre {
    @include etiquette;
    margin-bottom: 0.4rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--filet);
  }

  &__vide {
    font-family: var(--police-interface);
    font-size: 0.9rem;
    color: var(--encre-douce);
  }
}

.articles {
  display: grid;
  gap: 0.9rem;
  font-size: 0.98rem;
  line-height: 1.4;

  li { display: grid; }

  &__media,
  &__date {
    font-family: var(--police-interface);
    font-size: 0.8rem;
    color: var(--encre-douce);
  }

  &__media { font-weight: 600; }
}
</style>
