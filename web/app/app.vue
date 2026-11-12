<script setup lang="ts">
const liens = [
  { vers: '/', nom: 'À la une' },
  { vers: '/angles-morts', nom: 'Angles morts' },
  { vers: '/medias', nom: 'Médias' },
  { vers: '/methode', nom: 'Méthode' },
  { vers: '/archives', nom: 'Archives' },
]
useHead({
  titleTemplate: titre => (titre ? `${titre} — Revue du matin` : 'Revue du matin — l\'actualité française, recoupée'),
})

const route = useRoute()
const actif = (vers: string) => (vers === '/' ? route.path === '/' : route.path.startsWith(vers))
</script>

<template>
  <a class="lien-evitement" href="#contenu">Aller au contenu</a>

  <header class="entete">
    <div class="page entete__ligne">
      <NuxtLink to="/" class="entete__marque">
        <span class="entete__barres" aria-hidden="true"><i /><i /><i /></span>
        Revue du matin
      </NuxtLink>
      <nav aria-label="Navigation principale">
        <ul class="entete__nav">
          <li v-for="lien in liens" :key="lien.vers">
            <NuxtLink :to="lien.vers" :aria-current="actif(lien.vers) ? 'page' : undefined">{{ lien.nom }}</NuxtLink>
          </li>
        </ul>
      </nav>
    </div>
  </header>

  <main id="contenu" class="page contenu" tabindex="-1">
    <NuxtPage />
  </main>

  <footer class="pied">
    <div class="page pied__ligne">
      <p>
        Revue du matin recoupe les titres et extraits publiés par les médias dans leurs flux RSS.
        Elle ne reproduit aucun article : chaque lien mène au texte original.
      </p>
      <p>
        Pas de compte, pas de publicité, pas de cookie, pas de mesure d'audience.
        <NuxtLink to="/methode">Comment c'est fait, et avec quelles limites</NuxtLink>.
      </p>
    </div>
  </footer>
</template>

<style lang="scss" scoped>
@use '~/assets/scss/outils' as *;

.entete {
  border-bottom: 1px solid var(--filet);
  background: var(--papier);

  &__ligne {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem 2rem;
    padding-block: 0.9rem;
  }

  &__marque {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    font-family: var(--police-titre);
    font-size: 1.45rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    text-decoration: none;
  }

  &__barres {
    display: inline-flex;
    gap: 2px;

    i {
      width: 5px;
      height: 1.1rem;
      background: var(--centre);

      &:first-child { background: var(--gauche); }
      &:last-child { background: var(--droite); }
    }
  }

  &__nav {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 1.25rem;
    font-family: var(--police-interface);
    font-size: 0.95rem;

    a {
      display: inline-block;
      padding-block: 0.35rem;
      text-decoration: none;
      border-bottom: 2px solid transparent;

      &:hover { border-bottom-color: var(--filet); }

      &[aria-current='page'] {
        font-weight: 600;
        border-bottom-color: var(--filet-fort);
      }
    }
  }
}

.contenu {
  padding-block: 2.5rem 4rem;

  &:focus { outline: none; }
}

.pied {
  border-top: 1px solid var(--filet);
  font-family: var(--police-interface);
  font-size: 0.9rem;
  color: var(--encre-douce);

  &__ligne {
    display: grid;
    gap: 0.75rem 3rem;
    padding-block: 1.75rem 2.5rem;

    @include a-partir-de($moyen) {
      grid-template-columns: 1fr 1fr;
    }
  }
}
</style>
