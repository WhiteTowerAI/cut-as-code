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
}>

export type TrackView = Readonly<{
  id: string
  name: string
  kind: 'video' | 'audio' | 'caption'
}>

export type EditorProjectView = Readonly<{
  revision: number
  durationS: number
  fps: Readonly<{ numerator: number; denominator: number }>
  assets: readonly AssetView[]
  tracks: readonly TrackView[]
}>
