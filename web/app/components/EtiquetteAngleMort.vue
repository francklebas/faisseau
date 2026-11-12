<script setup lang="ts">
import type { AngleMort } from '#shared/types/revue'

defineProps<{ angle: AngleMort }>()
</script>

<template>
  <span class="angle badge">
    Angle mort à {{ angle.bord_absent }}
  </span>
</template>

<style lang="scss" scoped>
.angle {
  color: var(--accent);
}
</style>
