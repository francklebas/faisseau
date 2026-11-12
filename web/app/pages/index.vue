<script setup lang="ts">
const { data: edition } = await useFetch('/api/editions/derniere')

useSeoMeta({
  description: 'L\'actualité française recoupée entre une quarantaine de médias : faits communs, affirmations isolées, répartition de la couverture et angles morts.',
})

const anglesMorts = computed(() => edition.value?.sujets.filter(s => s.angle_mort) ?? [])
</script>

<template>
  <div v-if="edition">
    <EnTeteEdition :edition="edition" titre="L'actualité, recoupée" />

    <section v-if="anglesMorts.length" class="bloc" aria-labelledby="titre-angles">
      <h2 id="titre-angles" class="titre-section">
        Angles morts du jour
        <NuxtLink to="/angles-morts" class="bloc__suite">{{ pluriel(anglesMorts.length, 'sujet') }}</NuxtLink>
      </h2>
      <p class="bloc__aide">Des sujets couverts surtout par un bord, et presque pas par l'autre.</p>
      <ListeSujets :sujets="anglesMorts.slice(0, 3)" :date="edition.date" />
    </section>

    <section class="bloc" aria-labelledby="titre-une">
      <h2 id="titre-une" class="titre-section">Les sujets les plus couverts</h2>
      <p class="bloc__aide">Classés par nombre de médias qui en parlent, sans tri éditorial.</p>
      <ListeSujets :sujets="edition.sujets" :date="edition.date" numerote />
    </section>
  </div>

  <div v-else class="prose">
    <h1 class="titre-page">Aucune édition pour l'instant</h1>
    <p>Le pipeline n'a pas encore produit de revue. Lancez <code>make revue</code> à la racine du dépôt.</p>
  </div>
</template>

<style lang="scss" scoped>
.bloc {
  margin-top: 3rem;

  &__aide {
    margin-top: 0.3rem;
    font-family: var(--police-interface);
    font-size: 0.9rem;
    color: var(--encre-douce);
  }

  &__suite {
    margin-left: auto;
    font-family: var(--police-interface);
    font-size: 0.9rem;
    font-weight: 400;
  }
}
</style>
