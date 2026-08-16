export type LibraryTab = 'assets' | 'captions' | 'cards' | 'graphic-motion'

export type MenuId = 'viewer-more' | 'aspect-ratio' | null

export type EditorSelection =
  | {
      kind: 'asset' | 'video' | 'audio' | 'caption' | 'card' | 'graphic-motion'
      id: string
    }
  | null

export type AssetView = Readonly<{
  id: string
  name: string
  kind: 'video' | 'audio'
  mediaType?: string
  url?: string
  durationS?: number
  width?: number
  height?: number
}>

export type RuntimeResourceView = Readonly<{
  id: string
  kind: string
  etag: string
  size: number
  operationId?: string
}>

export type ReviewArtifactView = Readonly<{
  id: string
  name: string
  size: number
  sha256: string
  mediaType: string
  url: string
}>

export type LayerTransform = Readonly<{
  x: number
  y: number
  scale: number
}>

export type EditorLayerView = Readonly<{
  id: string
  operationId: string
  cueId: string
  kind: 'caption' | 'card' | 'graphic-motion'
  mediaType: 'dom' | 'image-sequence'
  zIndex: number
  programRange: Readonly<{ startS: number; endS: number }>
  transform: LayerTransform
  content: Readonly<Record<string, unknown>>
  imageSequence?: Readonly<{
    pattern: string
    startNumber: number
    fps: Readonly<{ numerator: number; denominator: number }>
    frameCount: number
    frameUrlTemplate?: string
  }>
}>

export type TrackView = Readonly<{
  id: string
  name: string
  kind: 'video' | 'audio' | 'caption' | 'card' | 'graphic-motion'
  clips?: readonly ClipView[]
}>

export type ClipView = Readonly<{
  id: string
  trackId?: string
  sourceAssetId?: string
  displayName?: string
  summary?: string
  speed?: number
  enabled?: boolean
  sourceRange: Readonly<{ startS: number; endS: number }>
  programRange: Readonly<{ startS: number; endS: number }>
}>

export type ContentCardEditableField = 'copy' | 'layout' | 'placement' | 'enabled'

export type ContentCardLayout = 'lower-third' | 'quote' | 'statistic' | 'default' | 'metric-spotlight' | 'bar-chart' | 'pie-chart' | 'line-chart' | 'side-by-side' | 'parallel-columns'

export type ContentCardPlacement = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'top' | 'bottom' | 'left' | 'right' | 'center'

export type OperationPreview = Readonly<{
  status: 'current' | 'stale'
  revision: number
  reviewId: string
  snapshotEtag: string
  evidenceHashes: readonly string[]
  artifacts?: readonly ReviewArtifactView[]
}>

export type OperationApproval = Readonly<{
  status: 'none' | 'approved' | 'rejected' | 'invalidated'
  revision?: number
  rationale?: string
  reviewId?: string
  snapshotEtag?: string
  evidenceHashes?: readonly string[]
}>

export type EditorOperationView = Readonly<{
  id: string
  kind: string
  revision: number
  editable: boolean
  fields: Readonly<Record<string, unknown>>
  preview?: OperationPreview
  approval?: OperationApproval
}>

export type EditorProjectView = Readonly<{
  id?: string
  runtime?: boolean
  activeSequence?: string
  revision: number
  durationS: number
  fps: Readonly<{ numerator: number; denominator: number }>
  sequenceGeometry?: Readonly<{ width: number; height: number }>
  assets: readonly AssetView[]
  sourceAssetId?: string
  tracks: readonly TrackView[]
  layers?: readonly EditorLayerView[]
  operations?: readonly EditorOperationView[]
  resources?: readonly RuntimeResourceView[]
}>
