<script setup lang="ts">
import type { Bloc } from '#shared/types/revue'

// Répartition des médias ayant couvert un sujet. La barre est décorative : les chiffres
// sont toujours donnés en toutes lettres dans la légende, lisible sans les couleurs.
const props = defineProps<{ couverture: Record<Bloc, number>, compact?: boolean }>()

const total = computed(() => BLOCS.reduce((somme, b) => somme + props.couverture[b], 0))
const segments = computed(() => BLOCS.filter(b => props.couverture[b] > 0))
</script>

<template>
  <div class="couverture" :class="{ 'couverture--compact': compact }">
    <div class="couverture__barre" aria-hidden="true">
      <span
        v-for="bloc in segments"
        :key="bloc"
        class="couverture__segment"
        :class="`couverture__segment--${bloc}`"
        :style="{ flexGrow: couverture[bloc] }"
      >{{ couverture[bloc] }}</span>
    </div>
    <ul class="couverture__legende">
      <li v-for="bloc in BLOCS" :key="bloc">
        <span class="pastille" :class="`pastille--${bloc}`" aria-hidden="true" />{{ NOM_BLOC[bloc] }}&nbsp;:
        <strong>{{ couverture[bloc] }}</strong><span class="masque"> {{ couverture[bloc] > 1 ? 'médias' : 'média' }} sur {{ total }}</span>
      </li>
    </ul>
  </div>
</template>

<style lang="scss" scoped>
.couverture {
  font-family: var(--police-interface);

  &__barre {
    display: flex;
    gap: 2px;
    height: 1.6rem;
    border-radius: 3px;
    overflow: hidden;
  }

  &__segment {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 1.6rem;
    flex-basis: 0;
    color: var(--sur-bloc);
    font-size: 0.8rem;
    font-weight: 700;

    &--gauche { background: var(--gauche); }
    &--centre { background: var(--centre); }
    &--droite { background: var(--droite); }
  }

  &__legende {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 1.1rem;
    margin-top: 0.4rem;
    font-size: 0.85rem;
    color: var(--encre-douce);

    strong { color: var(--encre); }
  }

  &--compact &__barre { height: 1.25rem; }
}
</style>
