// Site statique : toutes les pages sont générées à partir de data/editions/*.json,
// puis servies telles quelles (Cloudflare, ou n'importe quel hébergement de fichiers).
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  telemetry: false,

  css: ['~/assets/scss/main.scss'],

  app: {
    head: {
      htmlAttrs: { lang: 'fr' },
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'color-scheme', content: 'light dark' },
        { name: 'referrer', content: 'no-referrer' },
      ],
      link: [{ rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    },
  },

  // Aucun JavaScript côté lecteur : des pages HTML et une feuille de style, rien d'autre.
  // (Retirer cette ligne suffit pour retrouver une application Vue hydratée.)
  features: { noScripts: true },
  experimental: { payloadExtraction: false },

  nitro: {
    prerender: {
      crawlLinks: true,
      routes: ['/', '/angles-morts', '/medias', '/methode', '/archives'],
      failOnError: true,
    },
  },

  typescript: { strict: true },
})
