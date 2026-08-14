import { useEffect, useState, type ComponentType } from 'react'
import { useStore } from 'zustand'
import {
  ArrowDownToLine,
  ArrowUpToLine,
  AudioWaveform,
  Copy,
  Crop,
  Filter,
  Focus,
  Gauge,
  Magnet,
  Maximize2,
  MoreHorizontal,
  MousePointer2,
  Play,
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
import type { ContentCardsReview, RuntimeReadSet, RuntimeSnapshot } from '../runtime/types'
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

function Workspace({ store, runtime }: { store: ReturnType<typeof createEditorStore>; runtime?: RuntimeProjectStatus }) {
  const contentCardsOperation = useStore(store, (state) => state.project?.operations?.find((operation) => operation.kind === 'content-cards'))
  return (
    <>
      <header className="workspace-operation-bar">
        <strong>Cut as code</strong>
        <button type="button" disabled title="Export is not connected in this verification surface">Export</button>
      </header>
      {contentCardsOperation ? <ProjectReviewPanel operation={contentCardsOperation} store={store} /> : null}
      {runtime && runtime.snapshot.resources.length ? (
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
  const scenarioId = new URLSearchParams(window.location.search).get('scenario') ?? '1-84'
  const scenario = getScenario(scenarioId) ?? getScenario('1-84')!
  const [bridge] = useState(() => runtime ? runtimeAdapter(runtime.client, runtime.snapshot) : undefined)
  const [store] = useState(() => {
    const runtimeProject = runtime ? projectFromSnapshot(null, runtime.snapshot) : null
    const next = createEditorStore(
      { ...scenario.initialState, project: runtimeProject ?? scenario.initialState.project },
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
      {runtime ? <RuntimeStatus status={runtime} /> : null}
      {isWorkspaceScenario ? (
        <Workspace store={store} runtime={runtime} />
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
  const readSet = (): RuntimeReadSet => {
    const operation = snapshot.view.operations?.find((item) => item.id === 'content-cards')
    const project = snapshot.resources.find((item) => item.kind === 'project')
    const plan = snapshot.resources.find((item) => item.operation_id === 'content-cards')
    if (!operation || !project || !plan) throw new Error('Content Cards read set is incomplete')
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
    save: async (_operationId: string, draft: ContentCardsDraftChange) => {
      const template = snapshot.view.content_cards_edit?.review_template
      if (!template) throw new Error('Content Cards review template is unavailable')
      const review: ContentCardsReview = {
        schema_version: 1,
        cards: template.cards.map((card, index) => index === 0 ? {
          ...card,
          ...(draft.copy !== undefined ? { copy: draft.copy } : {}),
          ...(draft.layout !== undefined ? { visual_treatment: draft.layout } : {}),
          ...(draft.placement !== undefined ? { placement: draft.placement } : {}),
          ...(draft.enabled !== undefined ? { selected: draft.enabled } : {}),
        } : card),
      }
      try {
        const response = await client.updateContentCards(readSet(), review)
        return currentProject(response.snapshot ?? await client.getSnapshot())
      } catch (error) {
        if (error instanceof RuntimeConflictError) {
          const project = error.snapshot ? projectFromSnapshot(null, error.snapshot) : null
          throw Object.assign(error, { conflict: true, ...(project ? { project } : {}) })
        }
        throw error
      }
    },
    review: async (_operationId: string, decision: 'approved' | 'rejected', rationale?: string) => {
      const operation = snapshot.view.operations?.find((item) => item.id === 'content-cards')
      const reviews = snapshot.view.reviews?.filter((item) =>
        item.status === 'draft' && item.based_on?.['content-cards'] === operation?.revision &&
        item.snapshot_etag && item.evidence_hashes?.length,
      ) ?? []
      if (reviews.length !== 1) throw new Error('A unique current review is required')
      const review = reviews[0]
      try {
        const response = await client.recordContentCardsReview(readSet(), {
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
  const timeline = snapshot.view.timeline
  const assets = snapshot.media.map((item) => ({
    id: item.id,
    name: item.name,
    kind: item.media_type?.startsWith('audio/') ? 'audio' as const : 'video' as const,
  }))
  const clips = timeline?.clips.map((clip) => ({
    id: clip.id,
    sourceRange: { startS: clip.source_range.start_s, endS: clip.source_range.end_s },
    programRange: { startS: clip.program_range.start_s, endS: clip.program_range.end_s },
  })) ?? []
  const hasVideo = assets.some((asset) => asset.kind === 'video')
  const hasAudio = assets.some((asset) => asset.kind === 'audio') || hasVideo
  const hasCaptions = runtimeOperations.some((item) => item.id === 'captions')
  const tracks = [
    ...(hasVideo ? [{ id: 'track-video', name: 'Video', kind: 'video' as const, clips }] : []),
    ...(hasAudio ? [{ id: 'track-audio', name: 'Audio', kind: 'audio' as const, clips }] : []),
    ...(hasCaptions ? [{ id: 'track-captions', name: 'Captions', kind: 'caption' as const, clips: [] }] : []),
  ]

  return {
    revision: snapshot.view.project_revision ?? 1,
    durationS: timeline?.duration_s ?? 0,
    fps: { numerator: timeline?.fps.num ?? 30, denominator: timeline?.fps.den ?? 1 },
    assets,
    tracks,
    operations: runtimeOperations.map((operation) => operationFromSnapshot(
      operation.id,
      operation.revision,
      snapshot,
      operation.id === 'content-cards' ? edit?.fields : undefined,
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
  const hasCurrentEvidence = (receipt: NonNullable<RuntimeSnapshot['view']['reviews']>[number]) =>
    Boolean(receipt.evidence_hashes?.length && receipt.evidence_hashes.every((hash) => currentArtifactHashes.has(hash)))
  const currentReviews = snapshot.view.reviews?.filter((item) =>
    item.status === 'draft' && item.based_on?.[operationId] === revision &&
    item.snapshot_etag === snapshot.snapshot_etag && item.evidence_hashes?.length,
  ) ?? []
  const review = currentReviews.length === 1 ? currentReviews[0] : undefined
  const terminalReviews = snapshot.view.reviews?.filter((item) =>
    (item.status === 'approved' || item.status === 'rejected') &&
    item.based_on?.[operationId] === revision && item.snapshot_etag === snapshot.snapshot_etag &&
    (!review || (item.id === review.id && item.snapshot_etag === review.snapshot_etag)),
  ) ?? []
  const terminal = terminalReviews.length === 1 ? terminalReviews[0] : undefined
  const previewReceipt = review ?? terminal
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
      editable: operationId === 'content-cards' && !snapshot.read_only && Boolean(fields), fields: fields ?? {},
      ...(previewReceipt ? { preview: {
        status: hasCurrentEvidence(previewReceipt) ? 'current' : 'stale', revision,
        reviewId: previewReceipt.id, snapshotEtag: previewReceipt.snapshot_etag ?? '',
        evidenceHashes: previewReceipt.evidence_hashes ?? [], artifacts,
      } as const } : {}),
      approval: terminal
        ? { status: (hasCurrentEvidence(terminal) ? terminal.status : 'invalidated') as 'approved' | 'rejected' | 'invalidated', revision,
            rationale: terminal.rationale, reviewId: terminal.id, snapshotEtag: terminal.snapshot_etag,
            evidenceHashes: terminal.evidence_hashes }
        : { status: 'none' as const },
  }
}

function RuntimeStatus({ status }: { status: RuntimeProjectStatus }) {
  const { projectId, snapshot } = status
  const resourceFingerprint = snapshot.resources.map((resource) => resource.etag).join(':')
  return (
    <aside
      data-runtime-project-status
      data-resource-fingerprint={resourceFingerprint}
      aria-label="Runtime project status"
      style={{
        position: 'fixed',
        zIndex: 100,
        right: 12,
        top: 12,
        display: 'flex',
        gap: 8,
        alignItems: 'center',
        padding: '6px 8px',
        border: '1px solid #393b42',
        borderRadius: 6,
        color: '#f0f1f6',
        background: '#202126',
        font: '11px Inter, ui-sans-serif, system-ui, sans-serif',
      }}
    >
      <span>{projectId}</span>
      <span>{snapshot.view.active_sequence ?? 'No active sequence'}</span>
      <span>{snapshot.read_only ? 'Read only' : 'Writable'}</span>
      <span>{snapshot.resources.length} resources</span>
      <span>{snapshot.errors.length ? `${snapshot.errors.length} protocol errors` : 'No protocol errors'}</span>
    </aside>
  )
}
