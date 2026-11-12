import type { PageSujet } from '#shared/types/revue'

export default defineEventHandler(async (event): Promise<PageSujet> => {
  const edition = await lireEdition(getRouterParam(event, 'date') ?? '')
  const sujet = edition.sujets.find(s => s.slug === getRouterParam(event, 'slug'))
  if (!sujet)
    throw createError({ statusCode: 404, statusMessage: 'Sujet introuvable' })
  const cites = new Set(sujet.articles.map(a => a.media))
  const medias: PageSujet['medias'] = {}
  for (const m of edition.medias) {
    if (cites.has(m.id))
      medias[m.id] = { nom: m.nom, bloc: m.bloc, orientation: m.orientation, statut: m.statut }
  }
  return { date: edition.date, sujet, medias }
})
