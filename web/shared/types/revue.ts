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
  /** Sources externes sur la ligne éditoriale (absent des éditions antérieures au 12 novembre 2026). */
  sources?: SourceMedia[]
}

export interface SourceMedia {
  url: string
  type: 'ligne_revendiquee' | 'propriete' | 'etude' | 'presse' | 'audience'
  titre: string
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

export type Bord = 'gauche' | 'droite'

export interface CouvertureBord {
  /** Médias de ce bord qui couvrent le sujet avec au moins un article au titre propre. */
  medias: string[]
  /** Médias de ce bord qui n'ont publié qu'une dépêche reprise : non comptés. */
  depeche: string[]
  /** Médias de ce bord ayant publié ce jour-là. */
  total: number
  /** medias.length / total, entre 0 et 1. */
  part: number
}

/** Écart de couverture entre les médias de gauche et de droite (centre-gauche et centre-droit exclus). */
export interface Asymetrie {
  gauche: CouvertureBord
  droite: CouvertureBord
  /** Part à gauche − part à droite, entre −1 et 1. */
  ecart: number
  bord_dominant: Bord | null
  /** Motif pour lequel le sujet n'est pas classé (rubrique sportive). */
  ecarte: 'sport' | null
  /** L'écart dépasse le seuil d'affichage. */
  notable: boolean
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
  asymetrie: Asymetrie
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
  nb_asymetries: number
  effectif_bords: Record<Bord, number>
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
  asymetrie: Asymetrie
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
