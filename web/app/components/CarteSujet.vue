<script setup lang="ts">
import type { ResumeSujet } from '#shared/types/revue'

defineProps<{ sujet: ResumeSujet, date: string, rang?: number }>()
</script>

<template>
  <article class="carte">
    <p v-if="rang" class="carte__rang" aria-hidden="true">{{ rang }}</p>
    <div class="carte__corps">
      <h3 class="carte__titre">
        <NuxtLink :to="`/sujets/${date}/${sujet.slug}`">{{ sujet.titre }}</NuxtLink>
      </h3>
      <p v-if="sujet.premier_fait" class="carte__fait">{{ sujet.premier_fait }}</p>
      <p class="carte__meta">
        {{ pluriel(sujet.nb_medias, 'média') }} · {{ pluriel(sujet.nb_articles, 'article') }}
        <template v-if="sujet.nb_faits_communs + sujet.nb_faits_recoupes">
          · {{ pluriel(sujet.nb_faits_communs + sujet.nb_faits_recoupes, 'fait recoupé', 'faits recoupés') }}
        </template>
        <template v-if="sujet.nb_affirmations_isolees">
          · {{ pluriel(sujet.nb_affirmations_isolees, 'affirmation isolée', 'affirmations isolées') }}
        </template>
        <EtiquetteAngleMort v-if="sujet.angle_mort" :angle="sujet.angle_mort" class="carte__angle" />
      </p>
    </div>
    <BarreCouverture class="carte__couverture" :couverture="sujet.couverture" compact />
  </article>
</template>

<style lang="scss" scoped>
@use '~/assets/scss/outils' as *;

.carte {
  display: grid;
  gap: 0.75rem 1.5rem;
  padding-block: 1.4rem;
  border-top: 1px solid var(--filet);

  @include a-partir-de($large) {
    grid-template-columns: 2.5rem minmax(0, 1fr) 17rem;
    align-items: start;
  }

  &__rang {
    display: none;
    font-family: var(--police-titre);
    font-size: 1.6rem;
    line-height: 1.15;
    color: var(--encre-douce);

    @include a-partir-de($large) { display: block; }
  }

  &__titre {
    font-size: 1.4rem;

    a {
      text-decoration: none;

      &:hover { text-decoration: underline; }
    }
  }

  &__fait {
    max-width: var(--mesure);
    margin-top: 0.4rem;
    color: var(--encre-douce);
  }

  &__meta {
    margin-top: 0.5rem;
    font-family: var(--police-interface);
    font-size: 0.85rem;
    color: var(--encre-douce);
  }

  &__angle { margin-left: 0.5rem; }

  &__couverture {
    @include a-partir-de($large) { grid-column: 3; }
  }
}
</style>
