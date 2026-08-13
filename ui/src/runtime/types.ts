export type RuntimeResource = Readonly<{
  id: string
  kind: string
  etag: string
  size: number
  operation_id?: string
}>

export type RuntimeFile = Readonly<{
  id: string
  name: string
  size: number
}>

export type RuntimeSnapshot = Readonly<{
  read_only: boolean
  errors: readonly string[]
  view: Readonly<{
    schema_version?: number
    active_sequence?: string
    operation_count?: number
    review_count?: number
    operations?: readonly RuntimeOperation[]
    reviews?: readonly RuntimeReview[]
    content_cards_edit?: Readonly<{
      fields: Readonly<Record<string, unknown>>
      review_template: ContentCardsReview
    }>
  }>
  resources: readonly RuntimeResource[]
  media: readonly RuntimeFile[]
  artifacts: readonly RuntimeFile[]
}>

export type RuntimeOperation = Readonly<{
  id: string
  revision: number
  status: string
  etag: string
  plan_resource_id?: string
}>

export type RuntimeReview = Readonly<{
  id: string
  revision: number
  status: string
  based_on?: Readonly<Record<string, number>>
  snapshot_etag?: string
  evidence_hashes?: readonly string[]
  decision_mode?: string
  rationale?: string
}>

export type RuntimeReadSet = Readonly<{
  project: string
  operation: string
  plan: string
}>

export type ContentCardsReview = Readonly<{
  schema_version: 1
  cards: readonly Readonly<{
    id: string
    selected: boolean
    copy: string
    placement: string
    visual_treatment: string
    data?: Readonly<Record<string, unknown>>
  }>[]
}>

export type RuntimeMutationResponse = Readonly<{
  ok: boolean
  result?: 'committed' | 'no_change'
  error?: string
  snapshot?: RuntimeSnapshot
}>

export type SnapshotResponse = Readonly<{
  ok: boolean
  snapshot: RuntimeSnapshot
}>
