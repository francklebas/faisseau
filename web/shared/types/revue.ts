// Forme des fichiers data/editions/*.json écrits par le pipeline (revue/edition.py).

export type Bloc = 'gauche' | 'centre' | 'droite'

export interface Media {
  id: string
  nom: string
  site: string
  orientation: string
  bloc: Bloc
  justification: string
  note: string
  statut: 'a_valider' | 'valide'
  actif: boolean
}

export interface Fait {
  texte: string
  /** Identifiants des médias distincts qui énoncent le fait. */
  medias: string[]
  /** Numéros (`n`) des articles sources, dans la liste du sujet. */
  sources: number[]
}

export interface ArticleSource {
  n: number
  media: string
  titre: string
  url: string
  publie_le: string
}

export interface AngleMort {
  bord_dominant: 'gauche' | 'droite'
  bord_absent: 'gauche' | 'droite'
  part: number
}

export interface Sujet {
  id: string
  slug: string
  titre: string
  titre_origine: 'synthese' | 'article'
  extraction: 'ok' | 'indisponible' | 'echec'
  nb_articles: number
  nb_medias: number
  couverture: Record<Bloc, string[]>
  angle_mort: AngleMort | null
  faits_communs: Fait[]
  faits_recoupes: Fait[]
  affirmations_isolees: Fait[]
  premiere_publication: string
  derniere_publication: string
  articles: ArticleSource[]
}

export interface Stats {
  nb_articles: number
  nb_medias_actifs: number
  nb_sujets: number
  nb_angles_morts: number
  fenetre_heures: number
  modele_embeddings: string
  llm: string
  flux_en_erreur: string[]
}

export interface Edition {
  date: string
  genere_le: string
  stats: Stats
  sujets: Sujet[]
  medias: Media[]
}

/** Ce que les pages de liste reçoivent : le sujet sans ses articles ni ses faits. */
export interface ResumeSujet {
  id: string
  slug: string
  titre: string
  nb_articles: number
  nb_medias: number
  couverture: Record<Bloc, number>
  angle_mort: AngleMort | null
  nb_faits_communs: number
  nb_faits_recoupes: number
  nb_affirmations_isolees: number
  premier_fait: string | null
}

export interface ResumeEdition {
  date: string
  genere_le: string
  stats: Stats
  sujets: ResumeSujet[]
}

export interface EntreeIndex {
  date: string
  genere_le: string
  nb_sujets: number
}

export interface PageSujet {
  date: string
  sujet: Sujet
  /** Médias cités par ce sujet, par identifiant. */
  medias: Record<string, Pick<Media, 'nom' | 'bloc' | 'orientation' | 'statut'>>
}
