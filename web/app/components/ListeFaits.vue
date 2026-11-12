<script setup lang="ts">
import type { ArticleSource, Fait, PageSujet } from '#shared/types/revue'

// Un fait n'est jamais affiché sans ses sources : chaque média cité est un lien vers
// l'article qui l'énonce.
const props = defineProps<{
  faits: Fait[]
  articles: ArticleSource[]
  medias: PageSujet['medias']
  nbMedias: number
  isole?: boolean
}>()

const parNumero = computed(() => new Map(props.articles.map(a => [a.n, a])))
const sources = (fait: Fait) => fait.sources.map(n => parNumero.value.get(n)).filter((a): a is ArticleSource => !!a)
const nom = (id: string) => props.medias[id]?.nom ?? id
</script>

<template>
  <ol class="faits">
    <li v-for="(fait, i) in faits" :key="i" class="fait">
      <p class="fait__texte">{{ fait.texte }}</p>
      <p class="fait__sources">
        <span class="fait__compte">
          <template v-if="isole">Avancé par un seul média :</template>
          <template v-else>{{ fait.medias.length }} médias sur {{ nbMedias }} :</template>
        </span>
        <template v-for="(article, j) in sources(fait)" :key="article.n">
          <a :href="article.url" rel="external noopener" :aria-label="`${nom(article.media)} : ${article.titre}`">
            <span class="pastille" :class="`pastille--${medias[article.media]?.bloc}`" aria-hidden="true" />{{ nom(article.media) }}</a><template v-if="j < sources(fait).length - 1">, </template>
        </template>
      </p>
    </li>
  </ol>
</template>

<style lang="scss" scoped>
.faits {
  display: grid;
  gap: 1.1rem;
  max-width: 46rem;
}

.fait {
  padding-left: 1rem;
  border-left: 3px solid var(--filet);

  &__texte { font-size: 1.1rem; }

  &__sources {
    margin-top: 0.25rem;
    font-family: var(--police-interface);
    font-size: 0.85rem;
    color: var(--encre-douce);

    a { white-space: nowrap; }
  }

  &__compte { margin-right: 0.3rem; }
}
</style>
