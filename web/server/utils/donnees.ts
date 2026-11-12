import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import type { Edition, EntreeIndex, ResumeEdition } from '#shared/types/revue'

// Les éditions sont lues au moment de la génération statique ; rien n'est servi à chaud.
const dossier = () => resolve(process.env.REVUE_DONNEES ?? resolve(process.cwd(), '..', 'data'), 'editions')

const DATE = /^\d{4}-\d{2}-\d{2}$/

export async function lireIndex(): Promise<EntreeIndex[]> {
  try {
    return JSON.parse(await readFile(resolve(dossier(), 'index.json'), 'utf8'))
  }
  catch {
    return []
  }
}

export async function lireEdition(date: string): Promise<Edition> {
  if (!DATE.test(date))
    throw createError({ statusCode: 404, statusMessage: 'Édition introuvable' })
  try {
    return JSON.parse(await readFile(resolve(dossier(), `${date}.json`), 'utf8'))
  }
  catch {
    throw createError({ statusCode: 404, statusMessage: 'Édition introuvable' })
  }
}

export function resumer(edition: Edition): ResumeEdition {
  return {
    date: edition.date,
    genere_le: edition.genere_le,
    stats: edition.stats,
    sujets: edition.sujets.map(s => ({
      id: s.id,
      slug: s.slug,
      titre: s.titre,
      nb_articles: s.nb_articles,
      nb_medias: s.nb_medias,
      couverture: {
        gauche: s.couverture.gauche.length,
        centre: s.couverture.centre.length,
        droite: s.couverture.droite.length,
      },
      asymetrie: s.asymetrie,
      nb_faits_communs: s.faits_communs.length,
      nb_faits_recoupes: s.faits_recoupes.length,
      nb_affirmations_isolees: s.affirmations_isolees.length,
      premier_fait: s.faits_communs[0]?.texte ?? s.faits_recoupes[0]?.texte ?? null,
    })),
  }
}
