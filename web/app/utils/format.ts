import type { Bloc } from '#shared/types/revue'

const PARIS = 'Europe/Paris'

export const NOM_BLOC: Record<Bloc, string> = { gauche: 'Gauche', centre: 'Centre', droite: 'Droite' }
export const BLOCS: Bloc[] = ['gauche', 'centre', 'droite']

export const NOM_ORIENTATION: Record<string, string> = {
  'extreme-gauche': 'Extrême gauche',
  'gauche': 'Gauche',
  'centre-gauche': 'Centre gauche',
  'centre': 'Centre',
  'centre-droit': 'Centre droit',
  'droite': 'Droite',
  'extreme-droite': 'Extrême droite',
}

/** « mercredi 11 novembre 2026 » à partir de « 2026-11-11 » ou d'une date ISO complète. */
export function dateLongue(iso: string): string {
  const date = new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso)
  return new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: PARIS }).format(date)
}

/** « 11 nov., 08:30 » */
export function dateHeure(iso: string): string {
  return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: PARIS }).format(new Date(iso))
}

export function heure(iso: string): string {
  return new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit', timeZone: PARIS }).format(new Date(iso))
}

/** pluriel(3, 'média') → « 3 médias » ; pluriel(1, 'fait commun', 'faits communs') → « 1 fait commun » */
export function pluriel(n: number, singulier: string, plurielExplicite?: string): string {
  return `${n} ${n > 1 ? (plurielExplicite ?? `${singulier}s`) : singulier}`
}
