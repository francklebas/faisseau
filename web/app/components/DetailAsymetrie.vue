<script setup lang="ts">
import type { Asymetrie } from '#shared/types/revue'

defineProps<{ asymetrie: Asymetrie }>()

const BORDS = ['gauche', 'droite'] as const
</script>

<template>
  <dl class="detail">
    <div v-for="bord in BORDS" :key="bord">
      <dt><span class="pastille" :class="`pastille--${bord}`" aria-hidden="true" />Médias de {{ bord }}</dt>
      <dd>
        {{ asymetrie[bord].medias.length }} sur {{ asymetrie[bord].total }}
        ({{ pourcent(asymetrie[bord].part) }})<template v-if="asymetrie[bord].depeche.length">,
          plus {{ asymetrie[bord].depeche.length }} par dépêche reprise</template>
      </dd>
    </div>
    <div>
      <dt>Écart</dt>
      <dd>{{ points(asymetrie.ecart) }}</dd>
    </div>
  </dl>
</template>

<style lang="scss" scoped>
.detail {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 2rem;
  margin-bottom: 1.4rem;
  font-family: var(--police-interface);
  font-size: 0.9rem;

  div { display: flex; gap: 0.5rem; }
  dt { color: var(--encre-douce); }
  dd { font-weight: 600; }
}
</style>
