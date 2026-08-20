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
import { applyTimelineEdit, type TimelineEditCommand } from './timeline-edit'

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

export type ActivityLogEntry = Readonly<{
  id: number
  timestamp: string
  category: 'save' | 'export' | 'timeline'
  status: 'running' | 'succeeded' | 'failed'
  message: string
  operationId?: string
  detail?: string
}>

type TimelineHistoryEntry = Readonly<{
  undo: TimelineEditCommand
  redo: TimelineEditCommand
}>

export type PlaybackRange = Readonly<{
  startS: number
  endS: number
  requestId: number
}>

export type TimelineWorkspace = Readonly<{
  inS?: number
  outS?: number
}>

export type TimelineMarker = Readonly<{
  id: string
  timeS: number
  kind: 'marker' | 'review-note'
  label: string
}>

export type TimelineTrackDensity = 'compact' | 'standard' | 'relaxed'

export type TimelineTrackView = Readonly<{
  collapsed?: boolean
  density?: TimelineTrackDensity
}>

function timelineCommandMessage(command: TimelineEditCommand) {
  if (command.type === 'split') return 'Clip split'
  if (command.type === 'delete') return 'Clip deleted'
  if (command.type === 'trim') return `${command.edge === 'start' ? 'In point' : 'Out point'} trimmed`
  if (command.type === 'restore-bounds') return 'Media bounds restored'
  if (command.type === 'set-range') return 'Clip range restored'
  if (command.type === 'detach-audio') return 'Audio detached'
  if (command.type === 'attach-audio') return 'Audio attached'
  if (command.type === 'unlink-audio') return 'Audio and video unlinked'
  if (command.type === 'link-audio') return 'Audio and video linked'
  if (command.type === 'move-audio') return 'Audio moved'
  if (command.type === 'trim-audio') return 'Audio trimmed'
  if (command.type === 'delete-audio') return 'Audio ripple deleted'
  if (command.type === 'mute-audio' || command.type === 'mute-video-audio') return 'Audio mute changed'
  if (command.type === 'join') return 'Split undone'
  return 'Clip restored'
}

export type ExportBlocker = Readonly<{
  operationId: string
  state: 'unsaved' | 'saving' | 'conflict' | 'error'
}>

function sanitizeActivityDetail(detail: string | undefined) {
  const summary = detail?.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).at(-1)
  if (!summary) return undefined
  return summary
    .replace(/[A-Za-z]:(?:\\\\|\\)[^'"\r\n]+/g, '[local path]')
    .replace(/[A-Za-z]:\\(?:[^\\\s:]+\\)*[^\\\s:]*/g, '[local path]')
    .replace(/\/(?:[^/\s:]+\/)+[^/\s:]*/g, '[local path]')
    .slice(0, 500)
}

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
  return typeof x === 'number' && Number.isFinite(x) && x >= -2 && x <= 3
    && typeof y === 'number' && Number.isFinite(y) && y >= -2 && y <= 3
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

function applyDraftChangesToFields(
  fields: Readonly<Record<string, unknown>>,
  changes: readonly ContentCardsDraftChange[],
) {
  const cues = Array.isArray(fields.cues) ? fields.cues : []
  if (!cues.length || !changes.some((change) => change.cueId)) {
    return { ...fields, ...changes.reduce((next, change) => ({ ...next, ...change }), {}) }
  }
  return {
    ...fields,
    cues: cues.map((cue) => {
      if (!cue || typeof cue !== 'object') return cue
      const cueId = (cue as { id?: unknown }).id
      const change = changes.find((candidate) => candidate.cueId === cueId)
      if (!change) return cue
      const { cueId: _cueId, ...cueFields } = change
      return { ...(cue as Readonly<Record<string, unknown>>), ...cueFields }
    }),
  }
}

function applyDraftChangesToTracks(
  project: EditorProjectView,
  operationId: string,
  changes: readonly ContentCardsDraftChange[],
) {
  const kind = operationId === 'captions' ? 'caption'
    : operationId === 'content-cards' ? 'card'
      : operationId === 'graphic-motion' ? 'graphic-motion'
        : null
  if (!kind) return project.tracks
  return project.tracks.map((track) => track.kind !== kind ? track : {
    ...track,
    clips: track.clips?.map((clip) => {
      const change = changes.find((candidate) => candidate.cueId === clip.id)
      if (!change) return clip
      return {
        ...clip,
        ...(change.enabled !== undefined ? { enabled: change.enabled } : {}),
        ...(change.text !== undefined ? { summary: change.text } : {}),
        ...(change.copy !== undefined ? { summary: change.copy } : {}),
        ...(change.layout !== undefined || change.placement !== undefined ? {
          metadata: {
            ...clip.metadata,
            ...(change.layout !== undefined ? { layout: change.layout } : {}),
            ...(change.placement !== undefined ? { placement: change.placement } : {}),
          },
        } : {}),
      }
    }),
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
  playbackRange: PlaybackRange | null
  timelineWorkspace: TimelineWorkspace
  timelineMarkers: readonly TimelineMarker[]
  timelineTrackViews: Readonly<Record<string, TimelineTrackView>>
  timelineSoloTrackId?: string
  timelineZoom: number
  snapEnabled: boolean
  openMenu: MenuId
  operationDrafts: Readonly<Record<string, OperationDraft | undefined>>
  activityLog: readonly ActivityLogEntry[]
  timelinePast: readonly TimelineHistoryEntry[]
  timelineFuture: readonly TimelineHistoryEntry[]
  timelinePending: boolean
  timelineError?: string
  setProject: (project: EditorProjectView | null) => void
  seek: (timeS: number) => void
  setPlaying: (isPlaying: boolean) => void
  playRange: (startS: number, endS: number) => void
  clearPlaybackRange: () => void
  setTimelineWorkspaceBoundary: (edge: 'in' | 'out', timeS: number) => void
  clearTimelineWorkspace: () => void
  addTimelineMarker: (kind: TimelineMarker['kind'], timeS: number, label: string) => void
  setTimelineTrackCollapsed: (trackId: string, collapsed: boolean) => void
  setTimelineTrackDensity: (trackId: string, density: TimelineTrackDensity) => void
  setTimelineSoloTrack: (trackId?: string) => void
  select: (selection: EditorSelection) => void
  setActiveTab: (tab: LibraryTab) => void
  setTimelineZoom: (zoom: number) => void
  setSnapEnabled: (enabled: boolean) => void
  setOpenMenu: (menu: MenuId) => void
  editTimeline: (command: TimelineEditCommand) => Promise<void>
  undoTimeline: () => Promise<void>
  redoTimeline: () => Promise<void>
  editOperationDraft: (operationId: string, change: ContentCardsDraftChange) => void
  discardOperationDraft: (operationId: string) => void
  restoreOperationDraft: (operationId: string, draft: OperationDraft) => void
  saveOperationDraft: (operationId: string) => Promise<void>
  saveAllOperationDrafts: () => Promise<void>
  recordReviewDecision: (operationId: string, decision: 'approved' | 'rejected', rationale?: string) => Promise<void>
  getOperationDraft: (operationId: string) => OperationDraft | null
  canSaveOperation: (operationId: string) => boolean
  canSaveAllOperations: () => boolean
  hasUnsavedChanges: () => boolean
  exportBlockers: () => readonly ExportBlocker[]
  addActivity: (entry: Omit<ActivityLogEntry, 'id' | 'timestamp'>) => void
  clearActivityLog: () => void
  canApproveOperation: (operationId: string) => boolean
}

export type EditorRuntimeAdapter = Readonly<{
  save: (operationId: string, draft: ContentCardsDraftChange) => Promise<EditorProjectView>
  review: (operationId: string, decision: 'approved' | 'rejected', rationale?: string) => Promise<EditorProjectView>
  timelineEdit?: (command: TimelineEditCommand) => Promise<EditorProjectView>
  persistDraft?: (operationId: string, draft: Pick<OperationDraft, 'baseRevision' | 'changes'>) => Promise<void>
  discardDraft?: (operationId: string) => Promise<void>
}>

export function draftFieldsForCue(draft: OperationDraft | null | undefined, cueId: string) {
  return draft?.changes.find((change) => change.cueId === cueId)
}

export type EditorInitialState = Omit<
  EditorState,
  | 'setProject'
  | 'seek'
  | 'setPlaying'
  | 'playRange'
  | 'clearPlaybackRange'
  | 'setTimelineWorkspaceBoundary'
  | 'clearTimelineWorkspace'
  | 'addTimelineMarker'
  | 'setTimelineTrackCollapsed'
  | 'setTimelineTrackDensity'
  | 'setTimelineSoloTrack'
  | 'select'
  | 'setActiveTab'
  | 'setTimelineZoom'
  | 'setSnapEnabled'
  | 'setOpenMenu'
  | 'editTimeline'
  | 'undoTimeline'
  | 'redoTimeline'
  | 'editOperationDraft'
  | 'discardOperationDraft'
  | 'restoreOperationDraft'
  | 'saveOperationDraft'
  | 'saveAllOperationDrafts'
  | 'recordReviewDecision'
  | 'getOperationDraft'
  | 'canSaveOperation'
  | 'canSaveAllOperations'
  | 'hasUnsavedChanges'
  | 'exportBlockers'
  | 'addActivity'
  | 'clearActivityLog'
  | 'canApproveOperation'
  | 'operationDrafts'
  | 'activityLog'
  | 'timelinePast'
  | 'timelineFuture'
  | 'timelinePending'
  | 'timelineError'
  | 'timelineWorkspace'
  | 'timelineMarkers'
  | 'timelineTrackViews'
  | 'timelineSoloTrackId'
>

export function createEditorStore(initialState: EditorInitialState, runtime?: EditorRuntimeAdapter) {
  let nextActivityId = 1
  let nextPlaybackRequestId = 1
  let nextTimelineMarkerId = 1
  const draftPersistence = new Map<string, Promise<void>>()
  const enqueueDraftPersistence = (operationId: string, action: () => Promise<void>) => {
    const pending = (draftPersistence.get(operationId) ?? Promise.resolve())
      .catch(() => {})
      .then(action)
    draftPersistence.set(operationId, pending)
    void pending.then(
      () => { if (draftPersistence.get(operationId) === pending) draftPersistence.delete(operationId) },
      () => { if (draftPersistence.get(operationId) === pending) draftPersistence.delete(operationId) },
    )
    return pending
  }
  return createStore<EditorState>()((set, get) => ({
    ...initialState,
    operationDrafts: {},
    activityLog: [],
    timelinePast: [],
    timelineFuture: [],
    timelinePending: false,
    playbackRange: null,
    timelineWorkspace: {},
    timelineMarkers: [],
    timelineTrackViews: {},
    timelineSoloTrackId: undefined,
    addActivity: (entry) => set((state) => ({
      activityLog: [...state.activityLog, {
        ...entry,
        detail: sanitizeActivityDetail(entry.detail),
        id: nextActivityId++,
        timestamp: new Date().toISOString(),
      }].slice(-100),
    })),
    clearActivityLog: () => set({ activityLog: [] }),
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
    setPlaying: (isPlaying) => set({ isPlaying, ...(!isPlaying ? { playbackRange: null } : {}) }),
    playRange: (startS, endS) => {
      const durationS = get().project?.durationS ?? 0
      const start = Math.min(Math.max(startS, 0), durationS)
      const end = Math.min(Math.max(endS, start), durationS)
      if (!(end > start)) return
      set({
        currentTimeS: start,
        isPlaying: true,
        playbackRange: { startS: start, endS: end, requestId: nextPlaybackRequestId++ },
      })
    },
    clearPlaybackRange: () => set({ playbackRange: null }),
    setTimelineWorkspaceBoundary: (edge, timeS) => {
      const state = get()
      const durationS = state.project?.durationS ?? 0
      const fps = state.project?.fps
      const frameDurationS = fps && fps.numerator > 0 && fps.denominator > 0
        ? fps.denominator / fps.numerator
        : 1 / 30
      const snapped = Math.min(Math.max(Math.round(timeS / frameDurationS) * frameDurationS, 0), durationS)
      const workspace = { ...state.timelineWorkspace, [`${edge}S`]: snapped }
      if (edge === 'in' && workspace.outS !== undefined && workspace.outS <= snapped) delete workspace.outS
      if (edge === 'out' && workspace.inS !== undefined && workspace.inS >= snapped) delete workspace.inS
      set({ timelineWorkspace: workspace })
    },
    clearTimelineWorkspace: () => set({ timelineWorkspace: {} }),
    addTimelineMarker: (kind, timeS, label) => {
      const state = get()
      const durationS = state.project?.durationS ?? 0
      const fps = state.project?.fps
      const frameDurationS = fps && fps.numerator > 0 && fps.denominator > 0
        ? fps.denominator / fps.numerator
        : 1 / 30
      const marker: TimelineMarker = {
        id: `timeline-${kind}-${nextTimelineMarkerId++}`,
        timeS: Math.min(Math.max(Math.round(timeS / frameDurationS) * frameDurationS, 0), durationS),
        kind,
        label: label.trim() || (kind === 'marker' ? 'Marker' : 'Review note'),
      }
      set({ timelineMarkers: [...state.timelineMarkers, marker] })
    },
    setTimelineTrackCollapsed: (trackId, collapsed) => set((state) => ({
      timelineTrackViews: {
        ...state.timelineTrackViews,
        [trackId]: { ...state.timelineTrackViews[trackId], collapsed },
      },
    })),
    setTimelineTrackDensity: (trackId, density) => set((state) => ({
      timelineTrackViews: {
        ...state.timelineTrackViews,
        [trackId]: { ...state.timelineTrackViews[trackId], density },
      },
    })),
    setTimelineSoloTrack: (trackId) => set({ timelineSoloTrackId: trackId }),
    select: (selection) => set({ selection }),
    setActiveTab: (activeTab) => set({ activeTab }),
    setTimelineZoom: (zoom) => {
      const timelineZoom = Number.isFinite(zoom) ? Math.min(Math.max(zoom, 0.5), 2) : 1
      set({ timelineZoom })
    },
    setSnapEnabled: (snapEnabled) => set({ snapEnabled }),
    setOpenMenu: (openMenu) => set({ openMenu }),
    editTimeline: async (command) => {
      const state = get()
      if (!state.project || state.timelinePending) return
      if (Object.values(state.operationDrafts).some((draft) => draft?.pending || draft?.dirty)) {
        set({ timelineError: 'Save or discard other timeline changes before editing clips' })
        return
      }
      let edit
      try {
        edit = applyTimelineEdit(state.project, command)
      } catch (error) {
        set({ timelineError: error instanceof Error ? error.message : 'Timeline edit failed' })
        return
      }
      set({ timelinePending: true, timelineError: undefined })
      try {
        if (runtime && !runtime.timelineEdit) throw new Error('Timeline editing is unavailable for this project')
        const project = runtime ? await runtime.timelineEdit!(command) : edit.project
        set({
          project,
          selection: edit.selection,
          currentTimeS: Math.min(get().currentTimeS, project.durationS),
          timelinePast: [...state.timelinePast, { undo: edit.inverse, redo: command }].slice(-100),
          timelineFuture: [],
          timelinePending: false,
        })
        get().addActivity({ category: 'timeline', status: 'succeeded', message: timelineCommandMessage(command) })
      } catch (error) {
        const project = error && typeof error === 'object' && 'project' in error
          ? error.project as EditorProjectView
          : undefined
        set({
          ...(project ? { project } : {}),
          ...(project ? { timelinePast: [], timelineFuture: [] } : {}),
          timelinePending: false,
          timelineError: error instanceof Error ? error.message : 'Timeline edit failed',
        })
        get().addActivity({
          category: 'timeline',
          status: 'failed',
          message: timelineCommandMessage(command),
          detail: error instanceof Error ? error.message : 'Timeline edit failed',
        })
      }
    },
    undoTimeline: async () => {
      const state = get()
      const entry = state.timelinePast.at(-1)
      if (!entry || !state.project || state.timelinePending) return
      let edit
      try {
        edit = applyTimelineEdit(state.project, entry.undo)
      } catch (error) {
        set({ timelineError: error instanceof Error ? error.message : 'Timeline undo failed' })
        return
      }
      set({ timelinePending: true, timelineError: undefined })
      try {
        if (runtime && !runtime.timelineEdit) throw new Error('Timeline editing is unavailable for this project')
        const project = runtime ? await runtime.timelineEdit!(entry.undo) : edit.project
        set({
          project,
          selection: edit.selection,
          currentTimeS: Math.min(state.currentTimeS, project.durationS),
          timelinePast: state.timelinePast.slice(0, -1),
          timelineFuture: [...state.timelineFuture, entry].slice(-100),
          timelinePending: false,
        })
      } catch (error) {
        const project = error && typeof error === 'object' && 'project' in error
          ? error.project as EditorProjectView
          : undefined
        set({
          ...(project ? { project } : {}),
          ...(project ? { timelinePast: [], timelineFuture: [] } : {}),
          timelinePending: false,
          timelineError: error instanceof Error ? error.message : 'Timeline undo failed',
        })
      }
    },
    redoTimeline: async () => {
      const state = get()
      const entry = state.timelineFuture.at(-1)
      if (!entry || !state.project || state.timelinePending) return
      let edit
      try {
        edit = applyTimelineEdit(state.project, entry.redo)
      } catch (error) {
        set({ timelineError: error instanceof Error ? error.message : 'Timeline redo failed' })
        return
      }
      set({ timelinePending: true, timelineError: undefined })
      try {
        if (runtime && !runtime.timelineEdit) throw new Error('Timeline editing is unavailable for this project')
        const project = runtime ? await runtime.timelineEdit!(entry.redo) : edit.project
        set({
          project,
          selection: edit.selection,
          currentTimeS: Math.min(state.currentTimeS, project.durationS),
          timelinePast: [...state.timelinePast, entry].slice(-100),
          timelineFuture: state.timelineFuture.slice(0, -1),
          timelinePending: false,
        })
      } catch (error) {
        const project = error && typeof error === 'object' && 'project' in error
          ? error.project as EditorProjectView
          : undefined
        set({
          ...(project ? { project } : {}),
          ...(project ? { timelinePast: [], timelineFuture: [] } : {}),
          timelinePending: false,
          timelineError: error instanceof Error ? error.message : 'Timeline redo failed',
        })
      }
    },
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
      if (!runtime?.persistDraft) return
      const persistedDraft = { baseRevision: draft.baseRevision, changes: draft.changes }
      void enqueueDraftPersistence(operationId, () => runtime.persistDraft!(operationId, persistedDraft)).catch((error) => {
        const current = get().operationDrafts[operationId]
        if (current?.changes !== draft.changes) return
        set({ operationDrafts: { ...get().operationDrafts, [operationId]: {
          ...current, error: error instanceof Error ? error.message : 'Could not preserve draft',
        } } })
      })
    },
    discardOperationDraft: (operationId) => {
      const { [operationId]: _discarded, ...operationDrafts } = get().operationDrafts
      set({ operationDrafts })
      if (runtime?.discardDraft) void enqueueDraftPersistence(operationId, () => runtime.discardDraft!(operationId)).catch(() => {})
    },
    restoreOperationDraft: (operationId, draft) => {
      const operation = getOperation(get().project, operationId)
      if (!isSupportedOperation(operation) || !draft.changes.length
        || draft.changes.some((change) => !isOperationDraftChange(operation, change))) return
      const changes = draft.changes.filter((change) => !fieldsMatch(operation.fields, change))
      if (!changes.length) {
        if (runtime?.discardDraft) void enqueueDraftPersistence(operationId, () => runtime.discardDraft!(operationId)).catch(() => {})
        return
      }
      set({ operationDrafts: { ...get().operationDrafts, [operationId]: {
        baseRevision: draft.baseRevision,
        fields: changes.at(-1)!,
        changes,
        dirty: true,
        conflict: draft.conflict || operation.revision !== draft.baseRevision,
      } } })
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
        get().addActivity({ category: 'save', status: 'running', operationId, message: 'Save started' })
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
            const rebasedDraft: OperationDraft = {
              baseRevision: getOperation(project, operationId)?.revision ?? current.baseRevision,
              fields: newerChanges.at(-1)!, changes: newerChanges, dirty: true, conflict: false, pending: false,
              requestId,
            }
            set({ project, operationDrafts: {
              ...get().operationDrafts,
              [operationId]: rebasedDraft,
            } })
            if (runtime.persistDraft) {
              await enqueueDraftPersistence(operationId, () => runtime.persistDraft!(operationId, {
                baseRevision: rebasedDraft.baseRevision,
                changes: rebasedDraft.changes,
              }))
            }
          } else {
            const { [operationId]: _saved, ...operationDrafts } = get().operationDrafts
            set({ project, operationDrafts })
            if (runtime.discardDraft) await enqueueDraftPersistence(operationId, () => runtime.discardDraft!(operationId))
          }
          get().addActivity({ category: 'save', status: 'succeeded', operationId, message: 'Save completed' })
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
          get().addActivity({
            category: 'save', status: 'failed', operationId, message: 'Save failed',
            detail: error instanceof Error ? error.message : 'Unknown save error',
          })
        }
        return
      }
      const operations = state.project?.operations?.map((candidate) =>
        candidate.id === operationId
          ? {
              ...candidate,
              revision: candidate.revision + 1,
              fields: applyDraftChangesToFields(candidate.fields, draft.changes),
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
      set({
        project: state.project ? {
          ...state.project,
          revision: state.project.revision + 1,
          tracks: applyDraftChangesToTracks(state.project, operationId, draft.changes),
          operations,
        } : null,
        operationDrafts,
      })
    },
    saveAllOperationDrafts: async () => {
      const kindOrder = new Map<EditorOperationView['kind'], number>([
        ['captions', 0],
        ['content-cards', 1],
        ['graphic-motion', 2],
      ])
      const operationIds = (get().project?.operations ?? [])
        .filter((operation) => isSupportedOperation(operation) && get().operationDrafts[operation.id]?.dirty)
        .sort((left, right) => (kindOrder.get(left.kind) ?? 99) - (kindOrder.get(right.kind) ?? 99))
        .map((operation) => operation.id)
      for (const operationId of operationIds) {
        const draft = get().operationDrafts[operationId]
        if (!draft?.dirty) continue
        if (draft.pending || draft.conflict) break
        await get().saveOperationDraft(operationId)
        const remaining = get().operationDrafts[operationId]
        if (remaining?.conflict || remaining?.error) break
      }
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
    canSaveAllOperations: () => {
      const drafts = Object.values(get().operationDrafts)
      return !drafts.some((draft) => draft?.pending)
        && drafts.some((draft) => draft?.dirty && !draft.conflict)
    },
    hasUnsavedChanges: () => Object.values(get().operationDrafts).some((draft) => draft?.dirty || draft?.pending),
    exportBlockers: () => Object.entries(get().operationDrafts).flatMap(([operationId, draft]) => {
      if (!draft || (!draft.dirty && !draft.pending)) return []
      const state: ExportBlocker['state'] = draft.pending ? 'saving'
        : draft.conflict ? 'conflict'
          : draft.error ? 'error'
            : 'unsaved'
      return [{ operationId, state }]
    }),
    canApproveOperation: (operationId) => {
      const state = get()
      return canRecordReviewDecision(state.project, operationId, state.operationDrafts[operationId])
    },
  }))
}
