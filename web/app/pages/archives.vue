<script setup lang="ts">
const { data: editions } = await useFetch('/api/editions')

useSeoMeta({ title: 'Archives', description: 'Les éditions précédentes de la Revue quotidienne.' })
</script>

<template>
  <h1 class="titre-page">Archives</h1>
  <p class="chapo">Une édition par jour. Les éditions passées restent consultables telles qu'elles ont été publiées.</p>
  <ul v-if="editions?.length" class="editions">
    <li v-for="e in editions" :key="e.date">
      <NuxtLink :to="`/editions/${e.date}`">{{ dateLongue(e.date) }}</NuxtLink>
      <span>{{ pluriel(e.nb_sujets, 'sujet') }}</span>
    </li>
  </ul>
  <p v-else class="chapo">Aucune édition pour l'instant.</p>
</template>

<style lang="scss" scoped>
.editions {
  max-width: var(--mesure);
  margin-top: 2rem;

  li {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding-block: 0.8rem;
    border-top: 1px solid var(--filet);

    &::first-letter { text-transform: uppercase; }
  }

  span {
    font-family: var(--police-interface);
    font-size: 0.9rem;
    color: var(--encre-douce);
  }
}
</style>
