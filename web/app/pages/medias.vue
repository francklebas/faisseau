<script setup lang="ts">
import type { Bloc, Media } from '#shared/types/revue'

const { data: medias } = await useFetch('/api/medias')

useSeoMeta({
  title: 'Médias et classement',
  description: 'La liste des médias suivis, leur positionnement politique et la justification de chaque classement.',
})

const actifs = computed(() => (medias.value ?? []).filter(m => m.actif))
const inactifs = computed(() => (medias.value ?? []).filter(m => !m.actif))
const duBloc = (bloc: Bloc): Media[] => actifs.value.filter(m => m.bloc === bloc)
const aValider = computed(() => actifs.value.filter(m => m.statut === 'a_valider').length)
</script>

<template>
  <header>
    <h1 class="titre-page">Médias et classement</h1>
    <p class="chapo">
      {{ pluriel(actifs.length, 'média suivi', 'médias suivis') }}, répartis en trois blocs pour mesurer qui couvre quoi.
      Le positionnement décrit la ligne éditoriale d'ensemble d'un titre, pas chacun de ses articles.
    </p>
    <p v-if="aValider" class="note intro-note">
      <strong>Classement provisoire.</strong>
      {{ aValider === actifs.length ? 'Tous les positionnements' : `${aValider} positionnements sur ${actifs.length}` }}
      sont des propositions en attente de relecture. Ils sont discutables par nature ; la justification de chacun est donnée ci-dessous.
    </p>
  </header>

  <section v-for="bloc in BLOCS" :key="bloc" class="bloc" :aria-labelledby="`bloc-${bloc}`">
    <h2 :id="`bloc-${bloc}`" class="titre-section">
      <span><span class="pastille" :class="`pastille--${bloc}`" aria-hidden="true" />{{ NOM_BLOC[bloc] }}</span>
      <span class="bloc__compte">{{ pluriel(duBloc(bloc).length, 'média') }}</span>
    </h2>
    <div class="defilant" role="region" :aria-labelledby="`bloc-${bloc}`" tabindex="0">
      <table class="tableau">
        <thead>
          <tr>
            <th scope="col">Média</th>
            <th scope="col">Positionnement</th>
            <th scope="col">Justification</th>
            <th scope="col">Statut</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="media in duBloc(bloc)" :key="media.id">
            <th scope="row"><a :href="media.site" rel="external noopener">{{ media.nom }}</a></th>
            <td class="tableau__court">{{ NOM_ORIENTATION[media.orientation] ?? media.orientation }}</td>
            <td>
              {{ media.justification }}
              <span v-if="media.note" class="tableau__note">{{ media.note }}</span>
              <span v-if="media.sources?.length" class="tableau__note">
                Sources :
                <template v-for="(source, i) in media.sources" :key="source.url">
                  <a :href="source.url" rel="external noopener">{{ source.titre }}</a>{{ i < media.sources.length - 1 ? ' ; ' : '' }}
                </template>
              </span>
            </td>
            <td class="tableau__court">
              <span class="badge" :class="{ 'badge--attente': media.statut === 'a_valider' }">{{ media.statut === 'a_valider' ? 'À valider' : 'Validé' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <section v-if="inactifs.length" class="bloc prose" aria-labelledby="t-inactifs">
    <h2 id="t-inactifs" class="titre-section">Médias non suivis pour l'instant</h2>
    <p>Leur flux RSS n'est pas accessible aux robots ; ils ne sont donc pas pris en compte.</p>
    <ul>
      <li v-for="media in inactifs" :key="media.id"><strong>{{ media.nom }}</strong> — {{ media.note }}</li>
    </ul>
  </section>
</template>

<style lang="scss" scoped>
.intro-note {
  max-width: var(--mesure);
  margin-top: 1.25rem;
}

.bloc {
  margin-top: 3rem;

  &__compte {
    margin-left: auto;
    font-family: var(--police-interface);
    font-size: 0.9rem;
    font-weight: 400;
    color: var(--encre-douce);
  }
}

.defilant {
  overflow-x: auto;
}

.tableau {
  width: 100%;
  min-width: 38rem;
  border-collapse: collapse;
  font-family: var(--police-interface);
  font-size: 0.92rem;
  line-height: 1.45;

  th,
  td {
    padding: 0.7rem 1rem 0.7rem 0;
    border-bottom: 1px solid var(--filet);
    text-align: left;
    vertical-align: top;
  }

  thead th {
    font-size: 0.75rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--encre-douce);
  }

  tbody th {
    width: 11rem;
    font-weight: 600;
  }

  &__court { white-space: nowrap; }

  &__note {
    display: block;
    margin-top: 0.2rem;
    font-style: italic;
    color: var(--encre-douce);
  }
}

.badge--attente {
  color: var(--accent);
}
</style>
