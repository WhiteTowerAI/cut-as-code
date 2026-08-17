import { createStore } from 'zustand/vanilla'
import type {
  ContentCardLayout,
  ContentCardPlacement,
  EditorOperationView,
  EditorProjectView,
  EditorSelection,
  LibraryTab,
  MenuId,
  LayerTransform,
} from './editor-model'

export type ContentCardsDraftChange = Readonly<{
  cueId?: string
  copy?: string
  layout?: ContentCardLayout
  placement?: ContentCardPlacement
  enabled?: boolean
  text?: string
  transform?: LayerTransform
  contentBounds?: Readonly<{ x: number; y: number; width: number; height: number }>
}>

export type OperationDraft = Readonly<{
  baseRevision: number
  fields: ContentCardsDraftChange
  changes: readonly ContentCardsDraftChange[]
  dirty: boolean
  conflict: boolean
  pending?: boolean
  requestId?: number
  error?: string
}>

const contentCardLayouts: readonly ContentCardLayout[] = ['lower-third', 'quote', 'statistic', 'default', 'metric-spotlight', 'bar-chart', 'pie-chart', 'line-chart', 'side-by-side', 'parallel-columns']
const contentCardPlacements: readonly ContentCardPlacement[] = [
  'top-left',
  'top-right',
  'bottom-left',
  'bottom-right',
  'top',
  'bottom',
  'left',
  'right',
  'center',
]

function getOperation(project: EditorProjectView | null, operationId: string) {
  return project?.operations?.find((operation) => operation.id === operationId)
}

function isSupportedOperation(
  operation: EditorOperationView | undefined,
): operation is EditorOperationView {
  return Boolean(operation?.editable && ['content-cards', 'captions', 'graphic-motion'].includes(operation.kind))
}

function isOperationDraftChange(operation: EditorOperationView, value: unknown): value is ContentCardsDraftChange {
  if (!value || typeof value !== 'object') return false
  const allowed = operation.kind === 'content-cards'
    ? ['cueId', 'copy', 'layout', 'placement', 'enabled', 'transform', 'contentBounds']
    : operation.kind === 'captions'
      ? ['cueId', 'text', 'transform', 'contentBounds']
      : ['cueId', 'enabled', 'transform', 'contentBounds']
  return Object.entries(value).every(([field, fieldValue]) => {
    if (!allowed.includes(field)) return false
    if (field === 'cueId') return typeof fieldValue === 'string' && Boolean(fieldValue.trim())
    if (field === 'enabled') return typeof fieldValue === 'boolean'
    if (field === 'copy' || field === 'text') return typeof fieldValue === 'string'
    if (field === 'transform') return isLayerTransform(fieldValue)
    if (field === 'contentBounds') return isContentBounds(fieldValue)
    if (field === 'layout') return contentCardLayouts.includes(fieldValue as ContentCardLayout)
    return contentCardPlacements.includes(fieldValue as ContentCardPlacement)
  })
}

function isContentBounds(value: unknown) {
  if (!value || typeof value !== 'object') return false
  const bounds = value as Record<string, unknown>
  if (Object.keys(bounds).length !== 4 || !['x', 'y', 'width', 'height'].every((field) => field in bounds)) return false
  const { x, y, width, height } = bounds
  return [x, y, width, height].every((item) => typeof item === 'number' && Number.isFinite(item))
    && (x as number) >= 0 && (y as number) >= 0
    && (width as number) > 0 && (height as number) > 0
    && (x as number) + (width as number) <= 1
    && (y as number) + (height as number) <= 1
}

function isLayerTransform(value: unknown): value is LayerTransform {
  if (!value || typeof value !== 'object') return false
  const transform = value as Record<string, unknown>
  const fields = Object.keys(transform)
  const legacy = fields.length === 3 && ['x', 'y', 'scale'].every((field) => field in transform)
  const axis = fields.length === 4 && ['x', 'y', 'scale_x', 'scale_y'].every((field) => field in transform)
  if (!legacy && !axis) return false
  const { x, y } = transform
  const scaleX = legacy ? transform.scale : transform.scale_x
  const scaleY = legacy ? transform.scale : transform.scale_y
  return typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1
    && typeof y === 'number' && Number.isFinite(y) && y >= 0 && y <= 1
    && typeof scaleX === 'number' && Number.isFinite(scaleX) && scaleX >= 0.1 && scaleX <= 4
    && typeof scaleY === 'number' && Number.isFinite(scaleY) && scaleY >= 0.1 && scaleY <= 4
}

function fieldValueMatches(authority: unknown, draft: unknown) {
  if (isLayerTransform(authority) && isLayerTransform(draft)) {
    const authorityX = typeof authority.scale === 'number' ? authority.scale : authority.scale_x
    const authorityY = typeof authority.scale === 'number' ? authority.scale : authority.scale_y
    const draftX = typeof draft.scale === 'number' ? draft.scale : draft.scale_x
    const draftY = typeof draft.scale === 'number' ? draft.scale : draft.scale_y
    return authority.x === draft.x && authority.y === draft.y
      && authorityX === draftX && authorityY === draftY
  }
  return authority === draft
}

function fieldsMatch(
  authority: Readonly<Record<string, unknown>>,
  draft: ContentCardsDraftChange,
) {
  const cueId = draft.cueId
  const cues = Array.isArray(authority.cues) ? authority.cues : []
  const cue = cueId
    ? cues.find((item) => item && typeof item === 'object' && (item as { id?: string }).id === cueId) as Readonly<Record<string, unknown>> | undefined
    : undefined
  return Object.entries(draft).every(([field, value]) => {
    if (field === 'cueId') return Boolean(cue)
    return fieldValueMatches((cue ?? authority)[field], value)
  })
}

function hasReviewEvidence(operation: EditorOperationView) {
  const preview = operation.preview
  return Boolean(
    preview &&
      typeof preview.reviewId === 'string' && preview.reviewId.trim() &&
      typeof preview.snapshotEtag === 'string' && preview.snapshotEtag.trim() &&
      Array.isArray(preview.evidenceHashes) && preview.evidenceHashes.length &&
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
      !draft?.pending &&
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
  saveOperationDraft: (operationId: string) => Promise<void>
  recordReviewDecision: (operationId: string, decision: 'approved' | 'rejected', rationale?: string) => Promise<void>
  getOperationDraft: (operationId: string) => OperationDraft | null
  canSaveOperation: (operationId: string) => boolean
  hasUnsavedChanges: () => boolean
  canApproveOperation: (operationId: string) => boolean
}

export type EditorRuntimeAdapter = Readonly<{
  save: (operationId: string, draft: ContentCardsDraftChange) => Promise<EditorProjectView>
  review: (operationId: string, decision: 'approved' | 'rejected', rationale?: string) => Promise<EditorProjectView>
}>

export function draftFieldsForCue(draft: OperationDraft | null | undefined, cueId: string) {
  return draft?.changes.find((change) => change.cueId === cueId)
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
  | 'hasUnsavedChanges'
  | 'canApproveOperation'
  | 'operationDrafts'
>

export function createEditorStore(initialState: EditorInitialState, runtime?: EditorRuntimeAdapter) {
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
      if (!isSupportedOperation(operation) || !isOperationDraftChange(operation, change)) return

      const current = get().operationDrafts[operationId]
      if (current?.conflict) return
      const currentCueFields = change.cueId
        ? current?.changes.find((candidate) => candidate.cueId === change.cueId)
        : current?.changes.find((candidate) => !candidate.cueId)
      const nextFields = { ...(currentCueFields ?? {}), ...change }
      const changes = [
        ...(current?.changes.filter((candidate) => change.cueId ? candidate.cueId !== change.cueId : candidate.cueId) ?? []),
        nextFields,
      ].filter((candidate) => !fieldsMatch(operation.fields, candidate))
      const draft: OperationDraft = {
        baseRevision: current?.baseRevision ?? operation.revision,
        fields: nextFields,
        changes,
        dirty: changes.length > 0,
        conflict: false,
        pending: current?.pending ?? false,
        requestId: current?.requestId,
      }
      set({ operationDrafts: { ...get().operationDrafts, [operationId]: draft } })
    },
    discardOperationDraft: (operationId) => {
      const { [operationId]: _discarded, ...operationDrafts } = get().operationDrafts
      set({ operationDrafts })
    },
    saveOperationDraft: async (operationId) => {
      const state = get()
      const draft = state.operationDrafts[operationId]
      const operation = getOperation(state.project, operationId)
      if (!draft || !operation || !isSupportedOperation(operation) || draft.conflict || draft.pending) return
      if (!draft.dirty) {
        state.discardOperationDraft(operationId)
        return
      }
      if (runtime) {
        const requestId = (draft.requestId ?? 0) + 1
        const submittedChanges = [...draft.changes]
        set({ operationDrafts: {
          ...get().operationDrafts,
          [operationId]: { ...draft, requestId, pending: true, error: undefined },
        } })
        try {
          let project = state.project!
          for (const change of submittedChanges) project = await runtime.save(operationId, change)
          const current = get().operationDrafts[operationId]
          if (current?.requestId !== requestId) return
          const submittedCueIds = new Set(submittedChanges.map((change) => change.cueId ?? ''))
          const newerChanges = current.changes.filter((change) => !submittedCueIds.has(change.cueId ?? '') ||
            !submittedChanges.some((submitted) => JSON.stringify(submitted) === JSON.stringify(change)))
          if (newerChanges.length) {
            set({ project, operationDrafts: {
              ...get().operationDrafts,
              [operationId]: {
                baseRevision: getOperation(project, operationId)?.revision ?? current.baseRevision,
                fields: newerChanges.at(-1)!, changes: newerChanges, dirty: true, conflict: false, pending: false,
                requestId,
              },
            } })
          } else {
            const { [operationId]: _saved, ...operationDrafts } = get().operationDrafts
            set({ project, operationDrafts })
          }
        } catch (error) {
          const current = get().operationDrafts[operationId]
          if (current?.requestId !== requestId) return
          if (error && typeof error === 'object' && 'conflict' in error && 'project' in error) {
            set({ operationDrafts: {
              ...get().operationDrafts,
              [operationId]: { ...current, conflict: true, pending: false },
            }, project: error.project as EditorProjectView })
          } else {
            set({ operationDrafts: {
              ...get().operationDrafts,
              [operationId]: { ...current, pending: false, error: error instanceof Error ? error.message : 'Save failed' },
            } })
          }
        }
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
    recordReviewDecision: async (operationId, decision, rationale) => {
      const state = get()
      const operation = getOperation(state.project, operationId)
      if (!operation || !canRecordReviewDecision(state.project, operationId, state.operationDrafts[operationId])) return
      const cleanRationale = rationale?.trim()
      if (!cleanRationale) return
      if (runtime) {
        const currentDraft = state.operationDrafts[operationId]
        if (currentDraft?.pending) return
        const requestId = (currentDraft?.requestId ?? 0) + 1
        const pendingDraft: OperationDraft = currentDraft
          ? { ...currentDraft, requestId, pending: true, error: undefined }
          : { baseRevision: operation.revision, fields: {}, changes: [], dirty: false, conflict: false, requestId, pending: true }
        set({ operationDrafts: { ...get().operationDrafts, [operationId]: pendingDraft } })
        try {
          const project = await runtime.review(operationId, decision, cleanRationale)
          const current = get().operationDrafts[operationId]
          if (current?.requestId !== requestId) return
          const { [operationId]: _reviewed, ...operationDrafts } = get().operationDrafts
          set({ project, operationDrafts })
        } catch (error) {
          const current = get().operationDrafts[operationId]
          if (current?.requestId !== requestId) return
          if (error && typeof error === 'object' && 'conflict' in error && 'project' in error) {
            set({ operationDrafts: {
              ...get().operationDrafts,
              [operationId]: { ...current, conflict: true, pending: false },
            }, project: error.project as EditorProjectView })
          } else {
            set({ operationDrafts: {
              ...get().operationDrafts,
              [operationId]: { ...current, pending: false, error: error instanceof Error ? error.message : 'Review failed' },
            } })
          }
        }
        return
      }
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
      return Boolean(draft?.dirty && !draft.conflict && !draft.pending)
    },
    hasUnsavedChanges: () => Object.values(get().operationDrafts).some((draft) => draft?.dirty || draft?.pending),
    canApproveOperation: (operationId) => {
      const state = get()
      return canRecordReviewDecision(state.project, operationId, state.operationDrafts[operationId])
    },
  }))
}
