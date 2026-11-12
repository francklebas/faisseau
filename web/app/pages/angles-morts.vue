<script setup lang="ts">
const { data: edition } = await useFetch('/api/editions/derniere')

useSeoMeta({
  title: 'Angles morts',
  description: 'Les sujets du jour que les médias de gauche et de droite couvrent le plus inégalement.',
})

// Du plus asymétrique au moins asymétrique ; le seuil d'affichage est appliqué par le pipeline.
const sujets = computed(() => (edition.value?.sujets.filter(s => s.asymetrie.notable) ?? [])
  .toSorted((a, b) => Math.abs(b.asymetrie.ecart) - Math.abs(a.asymetrie.ecart)))
const BORDS = ['gauche', 'droite'] as const
const nbSport = computed(() => edition.value?.sujets.filter(s => s.asymetrie.ecarte === 'sport').length ?? 0)
</script>

<template>
  <header>
    <p v-if="edition" class="etiquette">Édition du {{ dateLongue(edition.date) }}</p>
    <h1 class="titre-page">Angles morts</h1>
    <p class="chapo">
      Les sujets du jour que les médias de gauche et de droite couvrent le plus inégalement, du plus grand
      écart au plus petit. Cela ne dit rien de l'importance du sujet : seulement de qui le traite.
    </p>
  </header>

  <template v-if="edition">
    <p class="ecarts__aide">
      Ce jour-là, {{ pluriel(edition.stats.effectif_bords.gauche, 'média') }} de gauche et
      {{ pluriel(edition.stats.effectif_bords.droite, 'média') }} de droite ont publié. Pour chaque sujet, on
      compare la part de chaque bord qui en parle.
    </p>

    <ol v-if="sujets.length" class="ecarts">
      <li v-for="(sujet, i) in sujets" :key="sujet.id" class="ecarts__sujet">
        <CarteSujet :sujet="sujet" :date="edition.date" :rang="i + 1" />
        <dl class="ecarts__detail">
          <div v-for="bord in BORDS" :key="bord">
            <dt><span class="pastille" :class="`pastille--${bord}`" aria-hidden="true" />Médias de {{ bord }}</dt>
            <dd>
              {{ sujet.asymetrie[bord].medias.length }} sur {{ sujet.asymetrie[bord].total }}
              ({{ pourcent(sujet.asymetrie[bord].part) }})<template v-if="sujet.asymetrie[bord].depeche.length">,
                plus {{ sujet.asymetrie[bord].depeche.length }} par dépêche reprise</template>
            </dd>
          </div>
          <div>
            <dt>Écart</dt>
            <dd>{{ points(sujet.asymetrie.ecart) }}</dd>
          </div>
        </dl>
      </li>
    </ol>
    <p v-else class="ecarts__vide">Aucun sujet ne dépasse le seuil d'affichage aujourd'hui.</p>

    <p class="note ecarts__note">
      Un écart n'est affiché qu'à partir de 25 points et de deux médias du bord qui domine. Les médias de
      centre gauche et de centre droit ne sont pas comptés. Les sujets de sport ne sont pas classés
      <template v-if="nbSport">({{ nbSport }} dans cette édition)</template>, et un média qui ne fait que
      reprendre une dépêche d'agence n'est pas compté : dans les deux cas, l'écart refléterait les
      rubriques et le débit des médias, pas un choix de traitement. Le calcul dépend entièrement du classement des
      médias, qui est provisoire et consultable sur la page <NuxtLink to="/medias">Médias</NuxtLink>. Un
      flux RSS ne reflète pas toujours tout ce qu'un média publie, et les médias des deux bords n'ont ni la
      même taille ni les mêmes rubriques : voir la <NuxtLink to="/methode">méthode</NuxtLink>.
    </p>
  </template>
</template>

<style lang="scss" scoped>
.ecarts {
  margin-top: 2rem;

  &__sujet:first-child :deep(.carte) { border-top: 0; }

  &__aide,
  &__vide {
    max-width: var(--mesure);
    margin-top: 1.5rem;
    font-family: var(--police-interface);
    font-size: 0.9rem;
    color: var(--encre-douce);
  }

  &__detail {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 2rem;
    margin-bottom: 1.4rem;
    font-family: var(--police-interface);
    font-size: 0.9rem;

    div { display: flex; gap: 0.5rem; }
    dt { color: var(--encre-douce); }
    dd { font-weight: 600; }
  }

  &__note {
    max-width: var(--mesure);
    margin-top: 3rem;
  }
}
</style>
