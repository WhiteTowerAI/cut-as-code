import { useState, type ComponentType } from 'react'
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
import { ProjectReviewPanel } from './ProjectReviewPanel'
import { createEditorStore } from './editor-store'
import { getScenario } from './scenarios'
import type { RuntimeSnapshot } from '../runtime/types'

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

function Workspace({ store }: { store: ReturnType<typeof createEditorStore> }) {
  const contentCardsOperation = useStore(store, (state) => state.project?.operations?.find((operation) => operation.kind === 'content-cards'))
  return (
    <>
      <header className="workspace-operation-bar">
        <strong>Cut as code</strong>
        <button type="button" disabled title="Export is not connected in this verification surface">Export</button>
      </header>
      {contentCardsOperation ? <ProjectReviewPanel operation={contentCardsOperation} store={store} /> : null}
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
}>

export function EditorShell({ runtime }: { runtime?: RuntimeProjectStatus }) {
  const scenarioId = new URLSearchParams(window.location.search).get('scenario') ?? '1-84'
  const scenario = getScenario(scenarioId) ?? getScenario('1-84')!
  const [store] = useState(() => {
    const next = createEditorStore(scenario.initialState)
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
  const viewerScenarios = new Set(['1-282', '57-152', '1-1026', '1-528', '123-79'])
  const timelineScenarios = new Set(['1-324', '1-1115', '1-754', '123-167'])
  const isViewerScenario = viewerScenarios.has(scenarioId)
  const isTimelineScenario = timelineScenarios.has(scenarioId)
  const isMenuFrame = scenarioId === '57-152' || scenarioId === '1-528'
  const isWorkspaceScenario = scenarioId === '1-60' || scenarioId === '1-1373' || scenarioId.startsWith('review-content-cards')
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
        <Workspace store={store} />
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
