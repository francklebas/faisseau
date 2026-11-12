<script setup lang="ts">
const route = useRoute()
const { data: edition } = await useFetch(`/api/editions/${route.params.date}`)
if (!edition.value)
  throw createError({ statusCode: 404, statusMessage: 'Édition introuvable', fatal: true })

useSeoMeta({ title: () => `Édition du ${dateLongue(edition.value!.date)}` })
</script>

<template>
  <div v-if="edition">
    <EnTeteEdition :edition="edition" :titre="`Édition du ${dateLongue(edition.date)}`" />
    <section aria-labelledby="titre-sujets">
      <h2 id="titre-sujets" class="titre-section">Les sujets les plus couverts</h2>
      <ListeSujets :sujets="edition.sujets" :date="edition.date" numerote />
    </section>
  </div>
</template>
