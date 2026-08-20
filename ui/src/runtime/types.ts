export type RuntimeResource = Readonly<{
  id: string
  kind: string
  etag: string
  size: number
  operation_id?: string
}>

export type RuntimeResourceContent = Readonly<{
  id: string
  kind: string
  etag: string
  size?: number
  operation_id?: string
  content: unknown
}>

export type ResourceResponse = Readonly<{
  ok: boolean
  resource: RuntimeResourceContent
}>

export type RuntimeFile = Readonly<{
  id: string
  name: string
  size: number
  sha256?: string
  media_type?: string
  url?: string
}>

export type RuntimeSnapshot = Readonly<{
  snapshot_etag?: string
  read_only: boolean
  errors: readonly string[]
  view: Readonly<{
    schema_version?: number
    project_id?: string
    project_name?: string
    project_revision?: number
    active_sequence?: string
    source_media_id?: string
    sequence_geometry?: Readonly<{ width: number; height: number }>
    source_media?: Readonly<{
      name: string
      duration_s: number
      width: number
      height: number
      has_video: boolean
      has_audio: boolean
    }>
    operation_count?: number
    review_count?: number
    operations?: readonly RuntimeOperation[]
    reviews?: readonly RuntimeReview[]
    timeline?: RuntimeTimeline
    content_cards_edit?: Readonly<{
      fields: Readonly<Record<string, unknown>>
      review_template: ContentCardsReview
      cues?: readonly RuntimeCardCue[]
    }>
    captions_edit?: Readonly<{
      style: Readonly<Record<string, unknown>>
      cues: readonly RuntimeCaptionCue[]
    }>
    graphic_motion_edit?: Readonly<{
      cues: readonly RuntimeGraphicMotionCue[]
    }>
    layers?: readonly RuntimeLayer[]
  }>
  resources: readonly RuntimeResource[]
  media: readonly RuntimeFile[]
  artifacts: readonly RuntimeFile[]
}>

export type RuntimeLayerTransform = Readonly<
  { x: number; y: number; scale: number; scale_x?: never; scale_y?: never }
  | { x: number; y: number; scale?: never; scale_x: number; scale_y: number }
>

export type RuntimeLayer = Readonly<{
  id: string
  operation_id: string
  cue_id: string
  kind: 'caption' | 'card' | 'graphic-motion'
  media_type: 'dom' | 'image-sequence'
  z_index: number
  program_range: Readonly<{ start_s: number; end_s: number }>
  transform: RuntimeLayerTransform
  content: Readonly<Record<string, unknown>>
  image_sequence?: Readonly<{
    pattern: string
    start_number: number
    fps: Readonly<{ num: number; den: number }>
    frame_count: number
    frame_url_template?: string
    content_bounds?: Readonly<{ x: number; y: number; width: number; height: number }>
  }>
}>

export type RuntimeTimeline = Readonly<{
  duration_s: number
  source_duration_s?: number
  fps: Readonly<{ num: number; den: number }>
  clips: readonly Readonly<{
    id: string
    source_range: Readonly<{ start_s: number; end_s: number }>
    program_range: Readonly<{ start_s: number; end_s: number }>
    speed?: number
    audio_mode?: 'embedded' | 'detached' | 'muted'
    decision_ref?: string
    source_asset_id?: string
  }>[]
  audio_clips?: readonly Readonly<{
    id: string
    source_range: Readonly<{ start_s: number; end_s: number }>
    program_range: Readonly<{ start_s: number; end_s: number }>
    speed?: number
    source_video_clip_id: string
    linked: boolean
    muted: boolean
    source_asset_id?: string
  }>[]
}>

export type RuntimeTimelineReadSet = Readonly<{
  project: string
  operation: string
  timeline: string
  plans: Readonly<Record<string, string>>
}>

export type RuntimeCaptionCue = Readonly<{
  id: string
  index?: number
  text: string
  program_range: Readonly<{ start_s: number; end_s: number }>
  source_ranges?: readonly Readonly<{ start_s: number; end_s: number }>[]
  source_text?: string
  decision_rationale?: string
  review_status?: string
  review_evidence?: readonly string[]
  transform?: RuntimeLayerTransform
}>

export type RuntimeCardCue = Readonly<{
  id: string
  card_type?: string
  copy: string
  layout: string
  placement: string
  enabled: boolean
  program_range: Readonly<{ start_s: number; end_s: number }>
  source_range?: Readonly<{ start_s: number; end_s: number }>
  source_text?: string
  decision_rationale?: string
  evidence_refs?: readonly string[]
  review_status?: string
  review_mode?: string
  review_evidence?: readonly string[]
  data?: Readonly<Record<string, unknown>>
  transform?: RuntimeLayerTransform
}>

export type RuntimeGraphicMotionCue = Readonly<{
  id: string
  status?: string
  enabled: boolean
  content: string
  recipe_id?: string
  review_status?: string
  review_mode?: string
  source_status?: string
  license_status?: string
  source_ranges?: readonly Readonly<{ start_s: number; end_s: number }>[]
  source_text?: string
  decision_rationale?: string
  review_evidence?: readonly string[]
  program_range: Readonly<{ start_s: number; end_s: number }>
  transform?: RuntimeLayerTransform
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

export type RuntimeExportJob = Readonly<{
  id?: string
  status: 'idle' | 'running' | 'succeeded' | 'failed'
  stage?: 'preparing' | 'rendering' | 'finalizing' | 'complete'
  startedAt?: string
  finishedAt?: string
  output?: string
  size?: number
  error?: string
}>

export type RuntimeExportResponse = Readonly<{
  ok: boolean
  job: RuntimeExportJob
  error?: string
}>

export type SnapshotResponse = Readonly<{
  ok: boolean
  snapshot: RuntimeSnapshot
}>

export type RuntimeDraft = Readonly<{
  baseRevision: number
  changes: readonly Readonly<Record<string, unknown>>[]
  conflict: boolean
  updatedAt?: string
}>
