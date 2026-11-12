import type { ResumeEdition } from '#shared/types/revue'

// Dernière édition publiée, ou null tant que le pipeline n'a jamais tourné.
export default defineEventHandler(async (): Promise<ResumeEdition | null> => {
  const [derniere] = await lireIndex()
  return derniere ? resumer(await lireEdition(derniere.date)) : null
})
