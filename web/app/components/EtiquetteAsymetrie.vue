<script setup lang="ts">
import type { Asymetrie } from '#shared/types/revue'

defineProps<{ asymetrie: Asymetrie }>()
</script>

<template>
  <span class="asymetrie badge">
    Surtout couvert à {{ asymetrie.bord_dominant }}
  </span>
</template>

<style lang="scss" scoped>
.asymetrie {
  color: var(--accent);
}
</style>
