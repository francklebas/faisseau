<script setup lang="ts">
import type { ResumeSujet } from '#shared/types/revue'

// `ecarts` : affiche sous chaque carte le détail de l'asymétrie (part de chaque bord, écart).
defineProps<{ sujets: ResumeSujet[], date: string, numerote?: boolean, ecarts?: boolean }>()
</script>

<template>
  <ol class="sujets">
    <li v-for="(sujet, i) in sujets" :key="sujet.id">
      <CarteSujet :sujet="sujet" :date="date" :rang="numerote ? i + 1 : undefined" />
      <DetailAsymetrie v-if="ecarts" :asymetrie="sujet.asymetrie" />
    </li>
  </ol>
</template>

<style lang="scss" scoped>
.sujets > li:first-child :deep(.carte) {
  border-top: 0;
}
</style>
