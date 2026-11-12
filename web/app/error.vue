<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()
useSeoMeta({ title: props.error.statusCode === 404 ? 'Page introuvable' : 'Erreur' })
</script>

<template>
  <main class="page erreur">
    <p class="etiquette">Erreur {{ error.statusCode }}</p>
    <h1 class="titre-page">{{ error.statusCode === 404 ? 'Cette page n\'existe pas' : 'Une erreur est survenue' }}</h1>
    <p class="chapo"><a href="/">Revenir à l'édition du jour</a></p>
  </main>
</template>

<style lang="scss" scoped>
.erreur {
  padding-block: 4rem;
}
</style>
