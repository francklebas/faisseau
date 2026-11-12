import type { Media } from '#shared/types/revue'

// Le classement affiché est celui de la dernière édition (copie de config/medias.yaml).
export default defineEventHandler(async (): Promise<Media[]> => {
  const [derniere] = await lireIndex()
  return derniere ? (await lireEdition(derniere.date)).medias : []
})
