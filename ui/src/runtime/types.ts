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
  }>
  resources: readonly RuntimeResource[]
  media: readonly RuntimeFile[]
  artifacts: readonly RuntimeFile[]
}>

export type SnapshotResponse = Readonly<{
  ok: boolean
  snapshot: RuntimeSnapshot
}>
