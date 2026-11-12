<script setup lang="ts">
const { data: edition } = await useFetch('/api/editions/derniere')

useSeoMeta({
  title: 'Angles morts',
  description: 'Les sujets du jour couverts surtout par des médias d\'un seul bord politique.',
})

const parBord = computed(() => ({
  droite: edition.value?.sujets.filter(s => s.angle_mort?.bord_absent === 'droite') ?? [],
  gauche: edition.value?.sujets.filter(s => s.angle_mort?.bord_absent === 'gauche') ?? [],
}))
const libelles = {
  droite: { titre: 'Peu couverts à droite', aide: 'Sujets portés surtout par des médias classés à gauche.' },
  gauche: { titre: 'Peu couverts à gauche', aide: 'Sujets portés surtout par des médias classés à droite.' },
} as const
</script>

<template>
  <header>
    <p v-if="edition" class="etiquette">Édition du {{ dateLongue(edition.date) }}</p>
    <h1 class="titre-page">Angles morts</h1>
    <p class="chapo">
      Un angle mort est un sujet dont la couverture vient très majoritairement d'un seul bord, tandis que
      l'autre n'en parle presque pas. Cela ne dit rien de l'importance du sujet : seulement de qui le traite.
    </p>
  </header>

  <template v-if="edition">
    <section v-for="bord in (['droite', 'gauche'] as const)" :key="bord" class="bord" :aria-labelledby="`titre-${bord}`">
      <h2 :id="`titre-${bord}`" class="titre-section">{{ libelles[bord].titre }}</h2>
      <p class="bord__aide">{{ libelles[bord].aide }}</p>
      <ListeSujets v-if="parBord[bord].length" :sujets="parBord[bord]" :date="edition.date" />
      <p v-else class="bord__vide">Aucun sujet dans ce cas aujourd'hui.</p>
    </section>

    <p class="note bord__note">
      Le calcul dépend entièrement du classement des médias, qui est provisoire et consultable sur la page
      <NuxtLink to="/medias">Médias</NuxtLink>. Un flux RSS ne reflète pas toujours tout ce qu'un média publie.
    </p>
  </template>
</template>

<style lang="scss" scoped>
.bord {
  margin-top: 3rem;

  &__aide,
  &__vide {
    margin-top: 0.3rem;
    font-family: var(--police-interface);
    font-size: 0.9rem;
    color: var(--encre-douce);
  }

  &__vide { margin-top: 1.25rem; }

  &__note {
    max-width: var(--mesure);
    margin-top: 3rem;
  }
}
</style>
