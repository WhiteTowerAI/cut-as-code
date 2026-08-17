import { useEffect, useMemo, useState, type ComponentType } from 'react'
import { useStore } from 'zustand'
import {
  ArrowDownToLine,
  ArrowUpToLine,
  CheckCircle2,
  AudioWaveform,
  Copy,
  Crop,
  Filter,
  Focus,
  FolderOpen,
  Gauge,
  Magnet,
  Maximize2,
  MoreHorizontal,
  MousePointer2,
  Play,
  ExternalLink,
  Plus,
  Ratio,
  Redo2,
  RotateCcw,
  RotateCw,
  Ruler,
  ScanLine,
  Scissors,
  Search,
  Trash2,
  Undo2,
  Upload,
  Volume2,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { LibraryPanel } from './LibraryPanel'
import { TimelinePanel } from './TimelinePanel'
import { ViewerPanel } from './ViewerPanel'
import { ProjectReviewPanel, ProtocolResourceInspector } from './ProjectReviewPanel'
import { createEditorStore } from './editor-store'
import { getScenario } from './scenarios'
import type { ContentCardsReview, RuntimeExportJob, RuntimeReadSet, RuntimeSnapshot } from '../runtime/types'
import { RuntimeApiClient, RuntimeConflictError } from '../runtime/api-client'
import type { ContentCardsDraftChange } from './editor-store'
import type { EditorProjectView } from './editor-model'

type IconItem = Readonly<{
  label: string
  icon: ComponentType<{ 'aria-hidden'?: boolean; size?: number; strokeWidth?: number }>
}>

const iconGroups: ReadonlyArray<Readonly<{ label: string; icons: readonly IconItem[] }>> = [
  {
    label: 'My Assets',
    icons: [
      { label: 'Search', icon: Search },
      { label: 'Import', icon: Upload },
      { label: 'Filter', icon: Filter },
    ],
  },
  {
    label: 'Viewer',
    icons: [
      { label: 'Crop', icon: Crop },
      { label: 'Audio', icon: AudioWaveform },
      { label: 'Rotate', icon: RotateCw },
      { label: 'Duplicate', icon: Copy },
      { label: 'Delete', icon: Trash2 },
      { label: 'Bring forward', icon: ArrowUpToLine },
      { label: 'Send backward', icon: ArrowDownToLine },
      { label: 'More', icon: MoreHorizontal },
      { label: 'Volume', icon: Volume2 },
      { label: 'Play', icon: Play },
      { label: 'Capture frame', icon: ScanLine },
      { label: 'Fit to window', icon: Focus },
      { label: 'Aspect ratio', icon: Ratio },
      { label: 'Fullscreen', icon: Maximize2 },
    ],
  },
  {
    label: 'Timeline',
    icons: [
      { label: 'Add', icon: Plus },
      { label: 'Select', icon: MousePointer2 },
      { label: 'Snap', icon: Magnet },
      { label: 'Undo', icon: Undo2 },
      { label: 'Redo', icon: Redo2 },
      { label: 'Split', icon: Scissors },
      { label: 'Speed', icon: Gauge },
      { label: 'Reverse', icon: RotateCcw },
      { label: 'Copy', icon: Copy },
      { label: 'Delete', icon: Trash2 },
      { label: 'Track fit', icon: Ruler },
      { label: 'Zoom out', icon: ZoomOut },
      { label: 'Zoom in', icon: ZoomIn },
    ],
  },
]

function Workspace({
  store,
  runtime,
  showDiagnostics = false,
}: {
  store: ReturnType<typeof createEditorStore>
  runtime?: RuntimeProjectStatus
  showDiagnostics?: boolean
}) {
  const [exportJob, setExportJob] = useState<RuntimeExportJob>({ status: 'idle' })
  const [exportError, setExportError] = useState<string | null>(null)
  const [exportConnectionError, setExportConnectionError] = useState<string | null>(null)
  const [exportNow, setExportNow] = useState(() => Date.now())
  const [activityOpen, setActivityOpen] = useState(false)
  const [activityCopied, setActivityCopied] = useState(false)
  const activityLog = useStore(store, (state) => state.activityLog)
  const operationDrafts = useStore(store, (state) => state.operationDrafts)
  const exportBlockers = useMemo(() => Object.entries(operationDrafts).flatMap(([operationId, draft]) => {
    if (!draft || (!draft.dirty && !draft.pending)) return []
    return [{
      operationId,
      state: draft.pending ? 'saving' : draft.conflict ? 'conflict' : draft.error ? 'error' : 'unsaved',
    } as const]
  }), [operationDrafts])
  const clearActivityLog = useStore(store, (state) => state.clearActivityLog)
  const addActivity = useStore(store, (state) => state.addActivity)
  const hasUnsavedChanges = exportBlockers.length > 0
  const activeOperation = useStore(store, (state) => {
    const selectedOperationId = state.selection?.kind === 'card' ? 'content-cards'
      : state.selection?.kind === 'caption' ? 'captions'
        : state.selection?.kind === 'graphic-motion' ? 'graphic-motion'
          : undefined
    const operationId = selectedOperationId
      ?? (state.activeTab === 'cards' ? 'content-cards'
        : state.activeTab === 'captions' ? 'captions'
          : state.activeTab === 'graphic-motion' ? 'graphic-motion'
            : undefined)
    return operationId
      ? state.project?.operations?.find((operation) => operation.id === operationId)
      : undefined
  })
  useEffect(() => {
    if (!runtime) return
    let active = true
    runtime.client.getExportStatus().then((job) => {
      if (active) setExportJob(job)
    }).catch((error) => {
      if (active) setExportConnectionError(error instanceof Error ? error.message : 'Could not restore export status')
    })
    return () => { active = false }
  }, [runtime])

  useEffect(() => {
    if (exportJob.status !== 'running') return
    const timer = window.setInterval(() => setExportNow(Date.now()), 1_000)
    return () => window.clearInterval(timer)
  }, [exportJob.status])
  useEffect(() => {
    if (!runtime || exportJob.status !== 'running') return
    let active = true
    const timer = window.setTimeout(async () => {
      try {
        const next = await runtime.client.getExportStatus()
        if (active) {
          setExportConnectionError(null)
          setExportJob(next)
          if (next.status === 'succeeded') {
            addActivity({ category: 'export', status: 'succeeded', message: 'Export completed' })
          } else if (next.status === 'failed') {
            addActivity({ category: 'export', status: 'failed', message: 'Export failed', detail: next.error })
          }
        }
      } catch (error) {
        if (!active) return
        setExportConnectionError(error instanceof Error ? error.message : 'Export status connection lost')
      }
    }, 100)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [addActivity, exportJob, runtime])

  const startExport = async () => {
    if (!runtime || exportJob.status === 'running') return
    setExportError(null)
    setExportConnectionError(null)
    addActivity({ category: 'export', status: 'running', message: 'Export started' })
    try {
      setExportJob(await runtime.client.startExport())
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Video export failed'
      setExportError(detail)
      setExportJob({ status: 'failed' })
      addActivity({ category: 'export', status: 'failed', message: 'Export failed', detail })
    }
  }

  const blockerText = exportBlockers.map(({ operationId, state }) => `${operationId}: ${state}`).join(', ')
  const copyActivityLog = async () => {
    const text = activityLog.map((entry) => [
      entry.timestamp,
      entry.status.toUpperCase(),
      entry.operationId ? `[${entry.operationId}]` : '',
      entry.message,
      entry.detail ?? '',
    ].filter(Boolean).join(' ')).join('\n')
    await navigator.clipboard.writeText(text)
    setActivityCopied(true)
    window.setTimeout(() => setActivityCopied(false), 1_500)
  }

  const exportAction = async (action: 'open' | 'reveal') => {
    if (!runtime) return
    try {
      setExportError(null)
      await runtime.client.openExport(action)
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Could not open the exported video')
    }
  }

  const startedAt = exportJob.startedAt ? Date.parse(exportJob.startedAt) : Number.NaN
  const finishedAt = exportJob.finishedAt ? Date.parse(exportJob.finishedAt) : Number.NaN
  const elapsedSeconds = Number.isFinite(startedAt)
    ? Math.max(0, Math.round(((Number.isFinite(finishedAt) ? finishedAt : exportNow) - startedAt) / 1_000))
    : undefined
  const formatDuration = (seconds: number) => seconds >= 60
    ? `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, '0')}s`
    : `${seconds}s`
  const formatSize = (size: number) => `${(size / 1024 / 1024).toFixed(1)} MB`
  const outputName = exportJob.output?.split(/[\\/]/).at(-1)
  const stage = exportJob.stage ?? (exportJob.status === 'running' ? 'rendering' : exportJob.status === 'succeeded' ? 'complete' : undefined)
  const exportMessage = exportError
    ?? (exportJob.status === 'running' ? `${stage === 'preparing' ? 'Preparing' : stage === 'finalizing' ? 'Finalizing' : 'Rendering'} video`
      : exportJob.status === 'succeeded' ? 'Export complete'
        : exportJob.status === 'failed' ? exportJob.error ?? 'Export failed'
          : exportConnectionError ?? '')
  return (
    <>
      <header className="workspace-operation-bar">
        {runtime ? (
          <>
            <RuntimeStatus status={runtime} />
            <div className="workspace-export-controls">
              {hasUnsavedChanges ? <span className="workspace-export-blocked" role="status" aria-label="Export blockers">Export blocked: {blockerText}</span> : null}
              {exportMessage ? (
                <div role="status" aria-label="Export status" className={`workspace-export-status workspace-export-status--${exportJob.status}`}>
                  <span className="workspace-export-summary">
                    {exportJob.status === 'succeeded' ? <CheckCircle2 aria-hidden size={14} /> : null}
                    <strong>{exportMessage}</strong>
                    {elapsedSeconds !== undefined ? <span>{formatDuration(elapsedSeconds)}</span> : null}
                    {outputName ? <span>{outputName}</span> : null}
                    {exportJob.size !== undefined ? <span>{formatSize(exportJob.size)}</span> : null}
                  </span>
                  {exportJob.output ? <span className="workspace-export-path" title={exportJob.output}>{exportJob.output}</span> : null}
                  {exportJob.finishedAt ? <time dateTime={exportJob.finishedAt}>{new Date(exportJob.finishedAt).toLocaleString()}</time> : null}
                  {exportConnectionError && exportJob.status === 'running' ? <span className="workspace-export-connection">Connection lost — retrying</span> : null}
                  {exportJob.status === 'succeeded' ? <span className="workspace-export-actions">
                    <button type="button" aria-label="Open exported video" onClick={() => exportAction('open')}><ExternalLink aria-hidden size={13} />Open file</button>
                    <button type="button" aria-label="Show exported video in folder" onClick={() => exportAction('reveal')}><FolderOpen aria-hidden size={13} />Show in folder</button>
                  </span> : null}
                </div>
              ) : null}
              <button
                className="workspace-activity-button"
                type="button"
                aria-expanded={activityOpen}
                onClick={() => setActivityOpen((open) => !open)}
              >Activity Log{activityLog.length ? ` (${activityLog.length})` : ''}</button>
              <button
                type="button"
                onClick={startExport}
                disabled={runtime.snapshot.read_only || exportJob.status === 'running' || hasUnsavedChanges}
                title={runtime.snapshot.read_only ? 'This project is read only' : hasUnsavedChanges ? `Export blocked — ${blockerText}` : 'Render the saved project to its final delivery'}
              >
                {exportJob.status === 'running' ? 'Rendering video' : exportJob.status === 'failed' ? 'Retry Export' : 'Export Video'}
              </button>
            </div>
          </>
        ) : (
          <>
            <strong>Cut as code</strong>
            <button type="button" disabled title="Export is not connected in this verification surface">Export</button>
          </>
        )}
      </header>
      {activityOpen ? (
        <section className="workspace-activity-log" role="region" aria-label="Activity Log">
          <header>
            <strong>Activity Log</strong>
            <span>Current browser session</span>
            <button type="button" aria-label="Copy log" disabled={!activityLog.length} onClick={copyActivityLog}>{activityCopied ? 'Copied' : 'Copy log'}</button>
            <button type="button" disabled={!activityLog.length} onClick={clearActivityLog}>Clear</button>
          </header>
          {activityLog.length ? (
            <ol>
              {[...activityLog].reverse().map((entry) => (
                <li key={entry.id} data-activity-status={entry.status}>
                  <time dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleTimeString()}</time>
                  <strong>{entry.message}</strong>
                  {entry.operationId ? <span>{entry.operationId}</span> : null}
                  {entry.detail ? <code>{entry.detail}</code> : null}
                </li>
              ))}
            </ol>
          ) : <p>No activity yet.</p>}
        </section>
      ) : null}
      {activeOperation?.editable ? (
        <div className="workspace-review">
          <ProjectReviewPanel operation={activeOperation} store={store} />
        </div>
      ) : null}
      {runtime && showDiagnostics && runtime.snapshot.resources.length ? (
        <div className="workspace-project-data">
          <ProtocolResourceInspector resources={runtime.snapshot.resources} client={runtime.client} />
        </div>
      ) : null}
      <div className="workspace-primary">
        <LibraryPanel store={store} />
        <ViewerPanel store={store} />
      </div>
      <div className="workspace-timeline">
        <TimelinePanel store={store} />
      </div>
    </>
  )
}

function IconLibrary() {
  return (
    <section className="icon-library" data-icon-library aria-label="Icon library verification">
      <header className="icon-library-header">
        <h1>Icon Library</h1>
        <p>My Assets&nbsp; / &nbsp;Viewer&nbsp; / &nbsp;Timeline</p>
      </header>
      {iconGroups.map((group) => (
        <section className="icon-library-section" key={group.label} aria-labelledby={`icon-group-${group.label.replace(' ', '-').toLowerCase()}`}>
          <h2 id={`icon-group-${group.label.replace(' ', '-').toLowerCase()}`}>{group.label}</h2>
          <div className="icon-library-grid">
            {group.icons.map(({ label, icon: Icon }) => (
              <div className="icon-library-tile" role="img" aria-label={label} title={label} key={label}>
                <Icon aria-hidden size={24} strokeWidth={2} />
              </div>
            ))}
          </div>
        </section>
      ))}
    </section>
  )
}

export type RuntimeProjectStatus = Readonly<{
  projectId: string
  snapshot: RuntimeSnapshot
  client: RuntimeApiClient
}>

export function EditorShell({ runtime }: { runtime?: RuntimeProjectStatus }) {
  const searchParams = new URLSearchParams(window.location.search)
  const scenarioId = searchParams.get('scenario') ?? '1-84'
  const showDiagnostics = searchParams.get('debug') === '1'
  const scenario = getScenario(scenarioId) ?? getScenario('1-84')!
  const [bridge] = useState(() => runtime ? runtimeAdapter(runtime.client, runtime.snapshot) : undefined)
  const [store] = useState(() => {
    const runtimeProject = runtime ? projectFromSnapshot(null, runtime.snapshot) : null
    const next = createEditorStore(
      runtimeProject ? {
        ...scenario.initialState,
        project: runtimeProject,
        activeTab: 'assets',
        selection: null,
        currentTimeS: 0,
        isPlaying: false,
        openMenu: null,
      } : scenario.initialState,
      bridge,
    )
    if (scenarioId === 'review-content-cards-conflict') {
      next.getState().editOperationDraft('content-cards', { copy: 'Local review note' })
      const project = next.getState().project
      next.getState().setProject(project ? {
        ...project,
        revision: project.revision + 1,
        operations: project.operations?.map((operation) => operation.id === 'content-cards'
          ? { ...operation, revision: operation.revision + 1, fields: { ...operation.fields, copy: 'Agent update' } }
          : operation),
      } : null)
    }
    return next
  })
  useEffect(() => {
    if (!runtime || !bridge) return
    bridge.sync(runtime.snapshot)
    store.getState().setProject(projectFromSnapshot(null, runtime.snapshot))
  }, [bridge, runtime, scenario.initialState.project, store])
  const viewerScenarios = new Set(['1-282', '57-152', '1-1026', '1-528', '123-79'])
  const timelineScenarios = new Set(['1-324', '1-1115', '1-754', '123-167'])
  const isViewerScenario = viewerScenarios.has(scenarioId)
  const isTimelineScenario = timelineScenarios.has(scenarioId)
  const isMenuFrame = scenarioId === '57-152' || scenarioId === '1-528'
  const isWorkspaceScenario = Boolean(runtime) || scenarioId === '1-60' || scenarioId === '1-1373' || scenarioId.startsWith('review-content-cards')
  const isIconLibraryScenario = scenarioId === '76-2'

  if (isIconLibraryScenario) {
    return (
      <main className="editor-shell editor-shell--icon-library" data-editor-shell data-scenario-id={scenarioId}>
        <IconLibrary />
      </main>
    )
  }

  return (
    <main
      className={isWorkspaceScenario
        ? 'editor-shell editor-shell--workspace'
        : isMenuFrame
          ? 'editor-shell editor-shell--menu-frame'
          : 'editor-shell'}
      data-editor-shell
      data-scenario-id={scenarioId}
      aria-label="Video editor"
    >
      {isWorkspaceScenario ? (
        <Workspace store={store} runtime={runtime} showDiagnostics={showDiagnostics} />
      ) : isTimelineScenario ? (
        <TimelinePanel store={store} />
      ) : isViewerScenario ? (
        <ViewerPanel store={store} />
      ) : (
        <LibraryPanel store={store} />
      )}
    </main>
  )
}

function runtimeAdapter(client: RuntimeApiClient, initial: RuntimeSnapshot) {
  let snapshot = initial
  const readSet = (operationId: string): RuntimeReadSet => {
    const operation = snapshot.view.operations?.find((item) => item.id === operationId)
    const project = snapshot.resources.find((item) => item.kind === 'project')
    const plan = snapshot.resources.find((item) => item.operation_id === operationId)
    if (!operation || !project || !plan) throw new Error(`${operationId} read set is incomplete`)
    return { project: project.etag, operation: operation.etag, plan: plan.etag }
  }
  const currentProject = (next: RuntimeSnapshot) => {
    snapshot = next
    const project = projectFromSnapshot(null, next)
    if (!project) throw new Error('Content Cards snapshot is unavailable')
    return project
  }
  return {
    sync: (next: RuntimeSnapshot) => { snapshot = next },
    save: async (operationId: string, draft: ContentCardsDraftChange) => {
      let review: Readonly<Record<string, unknown>>
      if (operationId === 'content-cards') {
        const template = snapshot.view.content_cards_edit?.review_template
        if (!template) throw new Error('Content Cards review template is unavailable')
        const targetId = draft.cueId ?? template.cards[0]?.id
        if (!targetId || !template.cards.some((card) => card.id === targetId)) throw new Error('Content Card cue is unavailable')
        const transformOnly = draft.transform !== undefined
          && draft.copy === undefined && draft.layout === undefined
          && draft.placement === undefined && draft.enabled === undefined
        const editorContentBounds = draft.contentBounds
          ? { cue_id: targetId, ...draft.contentBounds }
          : undefined
        review = transformOnly ? {
          schema_version: 1,
          editor_transform: { cue_id: targetId, ...draft.transform },
          ...(editorContentBounds ? { editor_content_bounds: editorContentBounds } : {}),
        } : {
          schema_version: 1,
          cards: template.cards.map((card) => card.id === targetId ? {
            ...card,
            ...(draft.copy !== undefined ? { copy: draft.copy } : {}),
            ...(draft.layout !== undefined ? { visual_treatment: draft.layout } : {}),
            ...(draft.placement !== undefined ? { placement: draft.placement } : {}),
            ...(draft.enabled !== undefined ? { selected: draft.enabled } : {}),
          } : card),
          ...(draft.transform ? {
            editor_transform: { cue_id: targetId, ...draft.transform },
          } : {}),
          ...(editorContentBounds ? { editor_content_bounds: editorContentBounds } : {}),
        } satisfies ContentCardsReview
      } else if (operationId === 'captions') {
        const cue = snapshot.view.captions_edit?.cues.find((item) => item.id === draft.cueId)
        if (!draft.cueId || !cue) throw new Error('Caption cue is required')
        review = {
          schema_version: 1,
          cue_id: draft.cueId,
          ...(draft.text !== undefined ? { text: draft.text } : {}),
          ...(draft.transform ? { editor_transform: draft.transform } : {}),
          ...(draft.contentBounds ? { editor_content_bounds: draft.contentBounds } : {}),
        }
      } else if (operationId === 'graphic-motion') {
        const cue = snapshot.view.graphic_motion_edit?.cues.find((item) => item.id === draft.cueId)
        if (!draft.cueId || !cue) throw new Error('Graphic Motion cue is required')
        review = {
          schema_version: 1,
          cue_id: draft.cueId,
          ...(draft.enabled !== undefined ? { enabled: draft.enabled } : {}),
          ...(draft.transform ? { editor_transform: draft.transform } : {}),
          ...(draft.contentBounds ? { editor_content_bounds: draft.contentBounds } : {}),
        }
      } else {
        throw new Error('Operation is not editable')
      }
      try {
        const response = await client.updatePlan(operationId, readSet(operationId), review)
        return currentProject(response.snapshot ?? await client.getSnapshot())
      } catch (error) {
        if (error instanceof RuntimeConflictError) {
          const project = error.snapshot ? projectFromSnapshot(null, error.snapshot) : null
          throw Object.assign(error, { conflict: true, ...(project ? { project } : {}) })
        }
        throw error
      }
    },
    review: async (operationId: string, decision: 'approved' | 'rejected', rationale?: string) => {
      const operation = snapshot.view.operations?.find((item) => item.id === operationId)
      const reviews = snapshot.view.reviews?.filter((item) =>
        item.status === 'draft' && item.based_on?.[operationId] === operation?.revision &&
        item.snapshot_etag && item.evidence_hashes?.length,
      ) ?? []
      if (reviews.length !== 1) throw new Error('A unique current review is required')
      const review = reviews[0]
      try {
        const response = await client.recordReview(operationId, readSet(operationId), {
          review_id: review.id, decision, snapshot_etag: review.snapshot_etag,
          evidence_hashes: review.evidence_hashes, actor: 'local-user',
          rationale: rationale?.trim(),
        })
        return currentProject(response.snapshot ?? await client.getSnapshot())
      } catch (error) {
        if (error instanceof RuntimeConflictError) {
          const project = error.snapshot ? projectFromSnapshot(null, error.snapshot) : null
          throw Object.assign(error, { conflict: true, ...(project ? { project } : {}) })
        }
        throw error
      }
    },
  }
}

export function projectFromSnapshot(base: EditorProjectView | null, snapshot: RuntimeSnapshot): EditorProjectView | null {
  const runtimeOperations = snapshot.view.operations ?? []
  const edit = snapshot.view.content_cards_edit
  const captionsEdit = snapshot.view.captions_edit
  const graphicMotionEdit = snapshot.view.graphic_motion_edit
  const timeline = snapshot.view.timeline
  const assets = snapshot.media.map((item) => ({
    id: item.id,
    name: item.name,
    kind: item.media_type?.startsWith('audio/') ? 'audio' as const : 'video' as const,
    mediaType: item.media_type,
    url: item.url,
    ...(item.id === snapshot.view.source_media_id && snapshot.view.source_media ? {
      durationS: snapshot.view.source_media.duration_s,
      width: snapshot.view.source_media.width,
      height: snapshot.view.source_media.height,
    } : {}),
  }))
  const sourceAsset = snapshot.view.source_media_id
    ? assets.find((asset) => asset.id === snapshot.view.source_media_id)
    : undefined
  const videoClips = timeline?.clips.map((clip) => ({
    id: clip.id,
    trackId: 'track-video',
    sourceAssetId: sourceAsset?.id,
    displayName: sourceAsset?.name ?? 'Unknown source',
    speed: clip.speed,
    sourceRange: { startS: clip.source_range.start_s, endS: clip.source_range.end_s },
    programRange: { startS: clip.program_range.start_s, endS: clip.program_range.end_s },
  })) ?? []
  const hasVideo = assets.some((asset) => asset.kind === 'video')
  const hasAudio = snapshot.view.source_media?.has_audio
    ?? (assets.some((asset) => asset.kind === 'audio') || hasVideo)
  const audioSource = sourceAsset?.kind === 'audio' ? sourceAsset : undefined
  const audioClips = audioSource ? timeline?.clips.map((clip) => ({
    id: `${clip.id}:audio`,
    trackId: 'track-audio',
    sourceAssetId: audioSource.id,
    displayName: audioSource.name,
    speed: clip.speed,
    sourceRange: { startS: clip.source_range.start_s, endS: clip.source_range.end_s },
    programRange: { startS: clip.program_range.start_s, endS: clip.program_range.end_s },
  })) ?? [] : []
  const captionClips = captionsEdit?.cues.map((cue) => ({
    id: cue.id,
    trackId: 'track-captions',
    displayName: `Caption ${cue.index ?? ''}`.trim(),
    summary: cue.text,
    sourceRange: cue.source_ranges?.[0]
      ? { startS: cue.source_ranges[0].start_s, endS: cue.source_ranges[0].end_s }
      : { startS: cue.program_range.start_s, endS: cue.program_range.end_s },
    programRange: { startS: cue.program_range.start_s, endS: cue.program_range.end_s },
  })) ?? []
  const cardClips = edit?.cues?.map((cue) => ({
    id: cue.id,
    trackId: 'track-content-cards',
    displayName: cue.card_type ? `Card: ${cue.card_type}` : 'Content card',
    summary: cue.copy,
    enabled: cue.enabled,
    sourceRange: { startS: cue.program_range.start_s, endS: cue.program_range.end_s },
    programRange: { startS: cue.program_range.start_s, endS: cue.program_range.end_s },
  })) ?? []
  const motionClips = graphicMotionEdit?.cues.map((cue) => ({
    id: cue.id,
    trackId: 'track-graphic-motion',
    displayName: cue.recipe_id ? `Motion: ${cue.recipe_id}` : 'Graphic motion',
    summary: cue.content,
    enabled: cue.enabled,
    sourceRange: { startS: cue.program_range.start_s, endS: cue.program_range.end_s },
    programRange: { startS: cue.program_range.start_s, endS: cue.program_range.end_s },
  })) ?? []
  const tracks = [
    ...(hasVideo ? [{ id: 'track-video', name: 'Video', kind: 'video' as const, clips: videoClips }] : []),
    ...(hasAudio ? [{ id: 'track-audio', name: 'Audio', kind: 'audio' as const, clips: audioClips }] : []),
    ...(captionsEdit ? [{ id: 'track-captions', name: 'Captions', kind: 'caption' as const, clips: captionClips }] : []),
    ...(edit?.cues ? [{ id: 'track-content-cards', name: 'Cards', kind: 'card' as const, clips: cardClips }] : []),
    ...(graphicMotionEdit ? [{ id: 'track-graphic-motion', name: 'Graphic Motion', kind: 'graphic-motion' as const, clips: motionClips }] : []),
  ]
  const layers = snapshot.view.layers?.map((layer) => ({
    id: layer.id,
    operationId: layer.operation_id,
    cueId: layer.cue_id,
    kind: layer.kind,
    mediaType: layer.media_type,
    zIndex: layer.z_index,
    programRange: {
      startS: layer.program_range.start_s,
      endS: layer.program_range.end_s,
    },
    transform: { ...layer.transform },
    content: { ...layer.content },
    ...(layer.image_sequence ? {
      imageSequence: {
        pattern: layer.image_sequence.pattern,
        startNumber: layer.image_sequence.start_number,
        fps: {
          numerator: layer.image_sequence.fps.num,
          denominator: layer.image_sequence.fps.den,
        },
        frameCount: layer.image_sequence.frame_count,
        ...(layer.image_sequence.frame_url_template ? {
          frameUrlTemplate: layer.image_sequence.frame_url_template,
        } : {}),
        ...(layer.image_sequence.content_bounds ? {
          contentBounds: { ...layer.image_sequence.content_bounds },
        } : {}),
      },
    } : {}),
  })) ?? []

  return {
    id: snapshot.view.project_id,
    runtime: true,
    activeSequence: snapshot.view.active_sequence,
    revision: snapshot.view.project_revision ?? 1,
    durationS: timeline?.duration_s ?? 0,
    fps: { numerator: timeline?.fps.num ?? 30, denominator: timeline?.fps.den ?? 1 },
    sequenceGeometry: snapshot.view.sequence_geometry,
    assets,
    sourceAssetId: snapshot.view.source_media_id && assets.some((asset) => asset.id === snapshot.view.source_media_id)
      ? snapshot.view.source_media_id
      : undefined,
    tracks,
    layers,
    operations: runtimeOperations.map((operation) => operationFromSnapshot(
      operation.id,
      operation.revision,
      snapshot,
      operation.id === 'content-cards' ? (edit ? { ...edit.fields, cues: edit.cues ?? [] } : undefined)
        : operation.id === 'captions' ? { style: captionsEdit?.style ?? {}, cues: captionsEdit?.cues ?? [] }
          : operation.id === 'graphic-motion' ? { cues: graphicMotionEdit?.cues ?? [] }
            : undefined,
    )),
    resources: snapshot.resources.map((resource) => ({
      id: resource.id,
      kind: resource.kind,
      etag: resource.etag,
      size: resource.size,
      ...(resource.operation_id ? { operationId: resource.operation_id } : {}),
    })),
  }
}

function operationFromSnapshot(
  operationId: string,
  revision: number,
  snapshot: RuntimeSnapshot,
  fields?: Readonly<Record<string, unknown>>,
) {
  const currentArtifactHashes = new Set(snapshot.artifacts.flatMap((artifact) => artifact.sha256 ? [`sha256:${artifact.sha256}`] : []))
  const hasEvidence = (receipt: NonNullable<RuntimeSnapshot['view']['reviews']>[number]) =>
    Boolean(receipt.evidence_hashes?.length && receipt.evidence_hashes.every((hash) => currentArtifactHashes.has(hash)))
  const operationReviews = snapshot.view.reviews?.filter((item) =>
    typeof item.based_on?.[operationId] === 'number' && item.evidence_hashes?.length,
  ) ?? []
  const currentReviews = operationReviews.filter((item) =>
    item.status === 'draft' && item.based_on?.[operationId] === revision &&
    item.snapshot_etag === snapshot.snapshot_etag && item.evidence_hashes?.length,
  )
  const review = currentReviews.length === 1 ? currentReviews[0] : undefined
  const terminalReviews = operationReviews.filter((item) =>
    (item.status === 'approved' || item.status === 'rejected') &&
    item.based_on?.[operationId] === revision && item.snapshot_etag === snapshot.snapshot_etag &&
    (!review || (item.id === review.id && item.snapshot_etag === review.snapshot_etag)),
  )
  const terminal = terminalReviews.length === 1 ? terminalReviews[0] : undefined
  const historical = operationReviews
    .filter((item) => item.based_on?.[operationId] !== revision || item.snapshot_etag !== snapshot.snapshot_etag)
    .sort((left, right) =>
      (right.based_on?.[operationId] ?? -1) - (left.based_on?.[operationId] ?? -1) || right.revision - left.revision,
    )[0]
  const previewReceipt = review ?? terminal ?? historical
  const previewRevision = previewReceipt?.based_on?.[operationId] ?? revision
  const previewIsCurrent = Boolean(
    previewReceipt && previewRevision === revision &&
    previewReceipt.snapshot_etag === snapshot.snapshot_etag && hasEvidence(previewReceipt),
  )
  const evidence = new Set(previewReceipt?.evidence_hashes ?? [])
  const artifacts = snapshot.artifacts.flatMap((artifact) => {
    if (!artifact.sha256 || !artifact.media_type || !artifact.url || !evidence.has(`sha256:${artifact.sha256}`)) return []
    return [{
      id: artifact.id,
      name: artifact.name,
      size: artifact.size,
      sha256: artifact.sha256,
      mediaType: artifact.media_type,
      url: artifact.url,
    }]
  })
  return {
      id: operationId, kind: operationId, revision,
      editable: ['content-cards', 'captions', 'graphic-motion'].includes(operationId)
        && !snapshot.read_only && Boolean(fields), fields: fields ?? {},
      ...(previewReceipt ? { preview: {
        status: previewIsCurrent ? 'current' : 'stale', revision: previewRevision,
        reviewId: previewReceipt.id, snapshotEtag: previewReceipt.snapshot_etag ?? '',
        evidenceHashes: previewReceipt.evidence_hashes ?? [], artifacts,
      } as const } : {}),
      approval: terminal
        ? { status: (hasEvidence(terminal) ? terminal.status : 'invalidated') as 'approved' | 'rejected' | 'invalidated', revision,
            rationale: terminal.rationale, reviewId: terminal.id, snapshotEtag: terminal.snapshot_etag,
            evidenceHashes: terminal.evidence_hashes }
        : historical && (historical.status === 'approved' || historical.status === 'rejected')
          ? { status: 'invalidated' as const, revision: previewRevision, rationale: historical.rationale,
              reviewId: historical.id, snapshotEtag: historical.snapshot_etag,
              evidenceHashes: historical.evidence_hashes }
        : { status: 'none' as const },
  }
}

function RuntimeStatus({ status }: { status: RuntimeProjectStatus }) {
  const { projectId, snapshot } = status
  const resourceFingerprint = snapshot.resources.map((resource) => resource.etag).join(':')
  return (
    <div
      data-runtime-project-status
      data-resource-fingerprint={resourceFingerprint}
      aria-label="Runtime project status"
    >
      <strong>Cut as Code</strong>
      <span>{projectId}</span>
      <span>{snapshot.view.active_sequence ?? 'No active sequence'}</span>
      <span className="runtime-status-chip">{snapshot.read_only ? 'Read only' : 'Writable'}</span>
      <span className="runtime-status-secondary">{snapshot.resources.length} resources</span>
      <span className="runtime-status-secondary">{snapshot.errors.length ? `${snapshot.errors.length} protocol errors` : 'No protocol errors'}</span>
    </div>
  )
}
