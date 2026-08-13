import { createStore } from 'zustand/vanilla'
import type {
  ContentCardEditableField,
  ContentCardLayout,
  ContentCardPlacement,
  EditorOperationView,
  EditorProjectView,
  EditorSelection,
  LibraryTab,
  MenuId,
} from './editor-model'

export type ContentCardsDraftChange = Readonly<{
  copy?: string
  layout?: ContentCardLayout
  placement?: ContentCardPlacement
  enabled?: boolean
}>

export type OperationDraft = Readonly<{
  baseRevision: number
  fields: ContentCardsDraftChange
  dirty: boolean
  conflict: boolean
}>

const contentCardFields: readonly ContentCardEditableField[] = [
  'copy',
  'layout',
  'placement',
  'enabled',
]

const contentCardLayouts: readonly ContentCardLayout[] = ['lower-third', 'quote', 'statistic']
const contentCardPlacements: readonly ContentCardPlacement[] = [
  'top-left',
  'top-right',
  'bottom-left',
  'bottom-right',
]

function getOperation(project: EditorProjectView | null, operationId: string) {
  return project?.operations?.find((operation) => operation.id === operationId)
}

function isSupportedOperation(
  operation: EditorOperationView | undefined,
): operation is EditorOperationView {
  return operation?.kind === 'content-cards' && operation.editable
}

function isContentCardsDraftChange(value: unknown): value is ContentCardsDraftChange {
  if (!value || typeof value !== 'object') return false
  return Object.entries(value).every(([field, fieldValue]) => {
    if (!contentCardFields.includes(field as ContentCardEditableField)) return false
    if (field === 'enabled') return typeof fieldValue === 'boolean'
    if (field === 'copy') return typeof fieldValue === 'string'
    if (field === 'layout') return contentCardLayouts.includes(fieldValue as ContentCardLayout)
    return contentCardPlacements.includes(fieldValue as ContentCardPlacement)
  })
}

function fieldsMatch(
  authority: Readonly<Record<string, unknown>>,
  draft: ContentCardsDraftChange,
) {
  return Object.entries(draft).every(([field, value]) => authority[field] === value)
}

function hasReviewEvidence(operation: EditorOperationView) {
  const preview = operation.preview
  return Boolean(
    preview &&
      preview.reviewId.trim() &&
      preview.snapshotEtag.trim() &&
      preview.evidenceHashes.length &&
      preview.evidenceHashes.every((hash) => hash.trim()),
  )
}

function canRecordReviewDecision(
  project: EditorProjectView | null,
  operationId: string,
  draft: OperationDraft | undefined,
) {
  const operation = getOperation(project, operationId)
  const preview = operation?.preview
  return Boolean(
    operation &&
      isSupportedOperation(operation) &&
      !draft?.dirty &&
      !draft?.conflict &&
      preview?.status === 'current' &&
      preview.revision === operation.revision &&
      hasReviewEvidence(operation) &&
      operation.approval?.status === 'none',
  )
}

export type EditorState = {
  project: EditorProjectView | null
  activeTab: LibraryTab
  selection: EditorSelection
  currentTimeS: number
  isPlaying: boolean
  timelineZoom: number
  snapEnabled: boolean
  openMenu: MenuId
  operationDrafts: Readonly<Record<string, OperationDraft | undefined>>
  setProject: (project: EditorProjectView | null) => void
  seek: (timeS: number) => void
  setPlaying: (isPlaying: boolean) => void
  select: (selection: EditorSelection) => void
  setActiveTab: (tab: LibraryTab) => void
  setTimelineZoom: (zoom: number) => void
  setSnapEnabled: (enabled: boolean) => void
  setOpenMenu: (menu: MenuId) => void
  editOperationDraft: (operationId: string, change: ContentCardsDraftChange) => void
  discardOperationDraft: (operationId: string) => void
  saveOperationDraft: (operationId: string) => void
  recordReviewDecision: (operationId: string, decision: 'approved' | 'rejected', rationale?: string) => void
  getOperationDraft: (operationId: string) => OperationDraft | null
  canSaveOperation: (operationId: string) => boolean
  canApproveOperation: (operationId: string) => boolean
}

export type EditorInitialState = Omit<
  EditorState,
  | 'setProject'
  | 'seek'
  | 'setPlaying'
  | 'select'
  | 'setActiveTab'
  | 'setTimelineZoom'
  | 'setSnapEnabled'
  | 'setOpenMenu'
  | 'editOperationDraft'
  | 'discardOperationDraft'
  | 'saveOperationDraft'
  | 'recordReviewDecision'
  | 'getOperationDraft'
  | 'canSaveOperation'
  | 'canApproveOperation'
  | 'operationDrafts'
>

export function createEditorStore(initialState: EditorInitialState) {
  return createStore<EditorState>()((set, get) => ({
    ...initialState,
    operationDrafts: {},
    setProject: (project) => {
      const operationDrafts = { ...get().operationDrafts }
      for (const [operationId, draft] of Object.entries(operationDrafts)) {
        const operation = getOperation(project, operationId)
        if (!operation || operation.revision !== draft?.baseRevision) {
          if (draft?.dirty) {
            operationDrafts[operationId] = { ...draft, conflict: true }
          } else {
            delete operationDrafts[operationId]
          }
        }
      }
      set({ project, operationDrafts })
    },
    seek: (timeS) => {
      const durationS = get().project?.durationS ?? 0
      const currentTimeS = Number.isFinite(timeS) ? Math.min(Math.max(timeS, 0), durationS) : 0
      set({ currentTimeS })
    },
    setPlaying: (isPlaying) => set({ isPlaying }),
    select: (selection) => set({ selection }),
    setActiveTab: (activeTab) => set({ activeTab }),
    setTimelineZoom: (zoom) => {
      const timelineZoom = Number.isFinite(zoom) ? Math.min(Math.max(zoom, 0.5), 2) : 1
      set({ timelineZoom })
    },
    setSnapEnabled: (snapEnabled) => set({ snapEnabled }),
    setOpenMenu: (openMenu) => set({ openMenu }),
    editOperationDraft: (operationId, change) => {
      const operation = getOperation(get().project, operationId)
      if (!isSupportedOperation(operation) || !isContentCardsDraftChange(change)) return

      const current = get().operationDrafts[operationId]
      if (current?.conflict) return
      const nextFields = { ...(current?.fields ?? {}), ...change }
      const draft: OperationDraft = {
        baseRevision: current?.baseRevision ?? operation.revision,
        fields: nextFields,
        dirty: !fieldsMatch(operation.fields, nextFields),
        conflict: false,
      }
      set({ operationDrafts: { ...get().operationDrafts, [operationId]: draft } })
    },
    discardOperationDraft: (operationId) => {
      const { [operationId]: _discarded, ...operationDrafts } = get().operationDrafts
      set({ operationDrafts })
    },
    saveOperationDraft: (operationId) => {
      const state = get()
      const draft = state.operationDrafts[operationId]
      const operation = getOperation(state.project, operationId)
      if (!draft || !operation || !isSupportedOperation(operation) || draft.conflict) return
      if (!draft.dirty) {
        state.discardOperationDraft(operationId)
        return
      }
      const operations = state.project?.operations?.map((candidate) =>
        candidate.id === operationId
          ? {
              ...candidate,
              revision: candidate.revision + 1,
              fields: { ...candidate.fields, ...draft.fields },
              preview: candidate.preview
                ? { ...candidate.preview, status: 'stale' as const }
                : candidate.preview,
              approval:
                candidate.approval?.status !== 'none'
                  ? { ...candidate.approval, status: 'invalidated' as const }
                  : candidate.approval,
            }
          : candidate,
      )
      const { [operationId]: _saved, ...operationDrafts } = state.operationDrafts
      set({ project: state.project ? { ...state.project, operations } : null, operationDrafts })
    },
    recordReviewDecision: (operationId, decision, rationale) => {
      const state = get()
      const operation = getOperation(state.project, operationId)
      if (!operation || !canRecordReviewDecision(state.project, operationId, state.operationDrafts[operationId])) return
      const cleanRationale = rationale?.trim()
      if (decision === 'rejected' && !cleanRationale) return
      const operations = state.project?.operations?.map((candidate) =>
        candidate.id === operationId
          ? {
              ...candidate,
              approval: {
                status: decision,
                revision: candidate.revision,
                ...(decision === 'rejected' ? { rationale: cleanRationale } : {}),
                reviewId: operation.preview!.reviewId,
                snapshotEtag: operation.preview!.snapshotEtag,
                evidenceHashes: operation.preview!.evidenceHashes,
              },
            }
          : candidate,
      )
      set({ project: state.project ? { ...state.project, operations } : null })
    },
    getOperationDraft: (operationId) => get().operationDrafts[operationId] ?? null,
    canSaveOperation: (operationId) => {
      const draft = get().operationDrafts[operationId]
      return Boolean(draft?.dirty && !draft.conflict)
    },
    canApproveOperation: (operationId) => {
      const state = get()
      return canRecordReviewDecision(state.project, operationId, state.operationDrafts[operationId])
    },
  }))
}
