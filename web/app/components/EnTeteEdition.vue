<script setup lang="ts">
import type { ResumeEdition } from '#shared/types/revue'

defineProps<{ edition: ResumeEdition, titre: string }>()
</script>

<template>
  <header class="edition">
    <p class="etiquette">Édition du {{ dateLongue(edition.date) }}</p>
    <h1 class="titre-page">{{ titre }}</h1>
    <p class="chapo">
      {{ pluriel(edition.stats.nb_sujets, 'sujet') }} recoupés à partir de
      {{ pluriel(edition.stats.nb_articles, 'article') }} publiés par
      {{ pluriel(edition.stats.nb_medias_actifs, 'média') }} en {{ edition.stats.fenetre_heures }} heures.
      Pour chacun : ce que les sources ont en commun, ce qu'une seule avance, et qui en parle.
    </p>
    <p class="edition__maj">Mise à jour à {{ heure(edition.genere_le) }}</p>
  </header>
</template>

<style lang="scss" scoped>
.edition {
  margin-bottom: 2.5rem;

  .etiquette { margin-bottom: 0.4rem; }

  &__maj {
    margin-top: 0.75rem;
    font-family: var(--police-interface);
    font-size: 0.85rem;
    color: var(--encre-douce);
  }
}
</style>
