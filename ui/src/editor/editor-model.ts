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

export type TrackView = Readonly<{
  id: string
  name: string
  kind: 'video' | 'audio' | 'caption'
  clips?: readonly ClipView[]
}>

export type ClipView = Readonly<{
  id: string
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
  revision: number
  durationS: number
  fps: Readonly<{ numerator: number; denominator: number }>
  assets: readonly AssetView[]
  sourceAssetId?: string
  tracks: readonly TrackView[]
  operations?: readonly EditorOperationView[]
  resources?: readonly RuntimeResourceView[]
}>
