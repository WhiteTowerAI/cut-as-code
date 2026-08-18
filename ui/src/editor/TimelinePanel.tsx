import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent,
  type ReactNode,
} from 'react'
import {
  ArrowUpDown,
  Copy,
  Eye,
  Gauge,
  Info,
  FileText,
  Lock,
  Link,
  Link2Off,
  LocateFixed,
  Magnet,
  MousePointer2,
  Plus,
  Play,
  Power,
  Pencil,
  Redo2,
  RotateCcw,
  Ruler,
  Scissors,
  Trash2,
  Undo2,
  VolumeX,
  Volume2,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { ClipView, EditorSelection, TrackView } from './editor-model'
import type { EditorState } from './editor-store'
import { TimelineContextMenu, type TimelineContextMenuModel } from './TimelineContextMenu'
import {
  applyTimelineEdit,
  canSplitClip,
  trimSourceBounds,
  trimAudioSourceAtProgramDelta,
  trimSourceAtProgramDelta,
  moveAudioStartAtProgramDelta,
  type TimelineTrimEdge,
} from './timeline-edit'

const TIMELINE_WIDTH_PX = 876
const TIMELINE_PRESENTATION_INSET_PX = 16
const MIN_ZOOM = 0.5
const MAX_ZOOM = 2
const ZOOM_STEP = 0.25
const RULER_LABEL_INTERVALS_S = [1, 2, 5, 10, 15, 30, 60, 120, 300] as const
const MIN_RULER_LABEL_SPACING_PX = 64
type RationalFps = Readonly<{ numerator: number; denominator: number }>
type MappingOptions = Readonly<{
  zoom?: number
  fps?: RationalFps
  snapEnabled?: boolean
}>

function mappingZoom(options: number | MappingOptions) {
  const zoom = typeof options === 'number' ? options : options.zoom ?? 1
  return Number.isFinite(zoom) && zoom > 0 ? zoom : 1
}

function clamp(value: number, minimum: number, maximum: number) {
  if (!Number.isFinite(value)) return minimum
  return Math.min(Math.max(value, minimum), maximum)
}

export function isTimeInHalfOpenRange(timeS: number, startS: number, endS: number) {
  return Number.isFinite(timeS) && Number.isFinite(startS) && Number.isFinite(endS)
    && startS <= timeS
    && timeS < endS
}

export function timeToPx(
  timeS: number,
  durationS: number,
  widthPx: number,
  options: number | MappingOptions = 1,
) {
  if (!(durationS > 0) || !(widthPx > 0)) return 0
  const zoom = mappingZoom(options)
  return (clamp(timeS, 0, durationS) / durationS) * widthPx * zoom
}

export function pxToTime(
  pixelX: number,
  durationS: number,
  widthPx: number,
  options: number | MappingOptions = 1,
) {
  if (!(durationS > 0) || !(widthPx > 0)) return 0
  const zoom = mappingZoom(options)
  const unclampedTimeS = (clamp(pixelX, 0, widthPx * zoom) / (widthPx * zoom)) * durationS
  if (typeof options === 'number' || !options.snapEnabled || !options.fps) return unclampedTimeS

  const { numerator, denominator } = options.fps
  if (!(numerator > 0) || !(denominator > 0)) return unclampedTimeS
  const frameDurationS = denominator / numerator
  return clamp(Math.round(unclampedTimeS / frameDurationS) * frameDurationS, 0, durationS)
}

function formatRulerTime(timeS: number) {
  const wholeSeconds = Math.round(timeS)
  const minutes = Math.floor(wholeSeconds / 60)
  const seconds = wholeSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function formatTimelineTime(timeS: number) {
  const wholeSeconds = Math.floor(Math.max(0, timeS))
  const minutes = Math.floor(wholeSeconds / 60)
  const seconds = wholeSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function formatPreciseTime(timeS: number) {
  const totalMilliseconds = Math.round(Math.max(0, timeS) * 1000)
  const wholeSeconds = Math.floor(totalMilliseconds / 1000)
  const minutes = Math.floor(wholeSeconds / 60)
  const seconds = wholeSeconds % 60
  const milliseconds = totalMilliseconds % 1000
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}`
}

function rulerLabelInterval(durationS: number, widthPx: number) {
  if (!(durationS > 0) || !(widthPx > 0)) return 1
  return RULER_LABEL_INTERVALS_S.find((interval) => interval * widthPx / durationS >= MIN_RULER_LABEL_SPACING_PX)
    ?? RULER_LABEL_INTERVALS_S.at(-1)!
}

function DisabledTimelineCommand({
  name,
  descriptionId,
  children,
}: {
  name: string
  descriptionId: string
  children: ReactNode
}) {
  const description = `${name} is not available in project protocol V1.`
  return (
    <span className="timeline-disabled-command" title={description}>
      <button type="button" disabled aria-label={name} aria-describedby={descriptionId}>
        {children}
      </button>
      <span className="sr-only" id={descriptionId}>{description}</span>
    </span>
  )
}

function TrackHeader({ track, runtime }: { track: TrackView; runtime: boolean }) {
  const badge = track.kind === 'video' ? 'V1'
    : track.kind === 'audio' ? 'A1'
      : track.kind === 'caption' ? 'C1'
        : track.kind === 'card' ? 'K1'
          : 'M1'
  return (
    <div className={`timeline-track-header timeline-track-header--${track.kind}`}>
      <span className="timeline-track-badge">{badge}</span>
      {runtime ? <span className="timeline-track-name">{track.name}</span> : (
        <>
          <button type="button" aria-label={`Lock ${track.name} track`} disabled title="Track locking is not available in project protocol V1."><Lock aria-hidden size={14} /></button>
          <button type="button" aria-label={`Show ${track.name} track`} disabled title="Track visibility is fixed in project protocol V1."><Eye aria-hidden size={14} /></button>
          <button type="button" aria-label={`Mute ${track.name} track`} disabled title="Track muting is not available in project protocol V1."><VolumeX aria-hidden size={14} /></button>
        </>
      )}
    </div>
  )
}

function Clip({
  track,
  clip,
  durationS,
  timelineZoom,
  timelineWidthPx,
  presentationInsetPx,
  selection,
  select,
  editable,
  trimming,
  onTrimStart,
  onAudioMoveStart,
  onContextMenu,
}: {
  track: TrackView
  clip: ClipView
  durationS: number
  timelineZoom: number
  timelineWidthPx: number
  presentationInsetPx: number
  selection: EditorSelection
  select: (selection: EditorSelection) => void
  editable: boolean
  trimming: TimelineTrimEdge | null
  onTrimStart: (event: PointerEvent<HTMLButtonElement>, clip: ClipView, edge: TimelineTrimEdge, kind?: 'video' | 'audio') => void
  onAudioMoveStart: (event: PointerEvent<HTMLButtonElement>, clip: ClipView) => void
  onContextMenu: (event: ReactMouseEvent<HTMLButtonElement>, track: TrackView, clip: ClipView) => void
}) {
  const kind = track.kind
  const id = clip.id
  const selected = selection?.kind === kind && selection.id === id
  const left = presentationInsetPx * timelineZoom + timeToPx(
    clip.programRange.startS,
    durationS,
    timelineWidthPx,
    timelineZoom,
  )
  const width = timeToPx(
    clip.programRange.endS - clip.programRange.startS,
    durationS,
    timelineWidthPx,
    timelineZoom,
  )
  const programDurationS = clip.programRange.endS - clip.programRange.startS
  return (
    <div
      className={`timeline-clip-shell timeline-clip-shell--${kind}${trimming ? ' is-trimming' : ''}`}
      style={{ left: `${left}px`, width: `${width}px` }}
    >
      <button
        type="button"
        className={`timeline-clip timeline-clip--${kind}`}
        data-timeline-clip={id}
        {...(kind === 'audio' && !clip.implicit ? { 'data-linked': String(Boolean(clip.linked)) } : {})}
        aria-label={`${track.name} ${kind === 'video' || kind === 'audio' ? 'clip' : 'cue'}`}
        aria-pressed={selected}
        onPointerDown={() => select({ kind, id })}
        onPointerDownCapture={(event) => {
          if (kind === 'audio' && !clip.implicit && !clip.linked && event.button === 0) onAudioMoveStart(event, clip)
        }}
        onContextMenu={(event) => onContextMenu(event, track, clip)}
      >
        {(kind === 'caption' || kind === 'card' || kind === 'graphic-motion') && (
          <span className="timeline-caption-cue">{clip.summary || clip.displayName || 'Untitled cue'}</span>
        )}
        {(kind === 'video' || kind === 'audio') && (
          <span className="timeline-clip-label">
            {clip.displayName || 'Unknown media'}
            {kind === 'video' && clip.speed !== undefined && <span className="timeline-clip-speed">{clip.speed.toFixed(2)}x</span>}
          </span>
        )}
      </button>
      {kind === 'video' && selected && editable && (
        <>
          <button
            type="button"
            className="timeline-trim-handle timeline-trim-handle--start"
            aria-label="Trim clip start"
            title="Drag to trim or restore the clip start"
            onPointerDown={(event) => onTrimStart(event, clip, 'start')}
          ><span aria-hidden /></button>
          <button
            type="button"
            className="timeline-trim-handle timeline-trim-handle--end"
            aria-label="Trim clip end"
            title="Drag to trim or restore the clip end"
            onPointerDown={(event) => onTrimStart(event, clip, 'end')}
          ><span aria-hidden /></button>
        </>
      )}
      {kind === 'audio' && selected && editable && !clip.implicit && !clip.linked && (
        <>
          <button
            type="button"
            className="timeline-trim-handle timeline-trim-handle--start"
            aria-label="Trim audio start"
            onPointerDown={(event) => onTrimStart(event, clip, 'start', 'audio')}
          ><span aria-hidden /></button>
          <button
            type="button"
            className="timeline-trim-handle timeline-trim-handle--end"
            aria-label="Trim audio end"
            onPointerDown={(event) => onTrimStart(event, clip, 'end', 'audio')}
          ><span aria-hidden /></button>
        </>
      )}
      {kind === 'audio' && !clip.implicit && (
        <span className="timeline-audio-state" aria-hidden>
          {clip.linked ? <Link size={12} /> : <Link2Off size={12} />}
          {clip.muted ? <VolumeX size={12} /> : null}
        </span>
      )}
      {kind === 'video' && trimming && (
        <output className={`timeline-trim-readout timeline-trim-readout--${trimming}`} aria-live="polite">
          <strong>{trimming === 'start' ? 'In' : 'Out'} {formatPreciseTime(trimming === 'start' ? clip.sourceRange.startS : clip.sourceRange.endS)}</strong>
          <span>Duration {formatPreciseTime(programDurationS)}</span>
        </output>
      )}
    </div>
  )
}

type TimelinePanelProps = { store: StoreApi<EditorState> }

export function TimelinePanel({ store }: TimelinePanelProps) {
  const project = useStore(store, (state) => state.project)
  const currentTimeS = useStore(store, (state) => state.currentTimeS)
  const selection = useStore(store, (state) => state.selection)
  const timelineZoom = useStore(store, (state) => state.timelineZoom)
  const snapEnabled = useStore(store, (state) => state.snapEnabled)
  const seek = useStore(store, (state) => state.seek)
  const select = useStore(store, (state) => state.select)
  const setTimelineZoom = useStore(store, (state) => state.setTimelineZoom)
  const setSnapEnabled = useStore(store, (state) => state.setSnapEnabled)
  const editTimeline = useStore(store, (state) => state.editTimeline)
  const playRange = useStore(store, (state) => state.playRange)
  const undoTimeline = useStore(store, (state) => state.undoTimeline)
  const redoTimeline = useStore(store, (state) => state.redoTimeline)
  const timelinePast = useStore(store, (state) => state.timelinePast)
  const timelineFuture = useStore(store, (state) => state.timelineFuture)
  const timelinePending = useStore(store, (state) => state.timelinePending)
  const timelineError = useStore(store, (state) => state.timelineError)
  const surfaceRef = useRef<HTMLDivElement>(null)
  const gutterRef = useRef<HTMLDivElement>(null)
  const rulerScrollRef = useRef<HTMLDivElement>(null)
  const trimSourceRef = useRef<number | null>(null)
  const audioMoveStartRef = useRef<number | null>(null)
  const [runtimeTimelineWidthPx, setRuntimeTimelineWidthPx] = useState(TIMELINE_WIDTH_PX)
  const viewDurationRef = useRef(project?.durationS ?? 0)
  const [trimDrag, setTrimDrag] = useState<null | Readonly<{
    pointerId: number
    clipId: string
    edge: TimelineTrimEdge
    startClientX: number
    sourceS: number
    kind: 'video' | 'audio'
  }>>(null)
  const [audioMoveDrag, setAudioMoveDrag] = useState<null | Readonly<{
    pointerId: number
    clipId: string
    startClientX: number
    startS: number
  }>>(null)
  const [trimPreview, setTrimPreview] = useState<null | Readonly<{ project: NonNullable<typeof project>; sourceS: number }>>(null)
  const [contextMenu, setContextMenu] = useState<Omit<TimelineContextMenuModel, 'onClose'> | null>(null)
  const [clipInfo, setClipInfo] = useState<ClipView | null>(null)
  const [cueInfo, setCueInfo] = useState<null | Readonly<{
    clip: ClipView
    operationId: string
    view: 'source' | 'review'
  }>>(null)
  const [deleteNotice, setDeleteNotice] = useState<string | null>(null)
  const presentedProject = trimPreview?.project ?? project
  const durationS = project?.durationS ?? 0
  if (viewDurationRef.current <= 0 && durationS > 0) viewDurationRef.current = durationS
  const viewDurationS = Math.max(viewDurationRef.current, durationS)
  const tracks = presentedProject?.tracks ?? []
  const runtime = Boolean(project?.runtime)
  const timelineEditable = Boolean(project && (!runtime || project.timelineEditable))
  const hasMedia = durationS > 0 && tracks.length > 0
  const timelineWidthPx = runtime ? runtimeTimelineWidthPx : TIMELINE_WIDTH_PX
  const presentationInsetPx = runtime ? 0 : TIMELINE_PRESENTATION_INSET_PX
  const viewWidthPx = durationS > 0 && viewDurationRef.current > 0
    ? timelineWidthPx * viewDurationS / viewDurationRef.current
    : timelineWidthPx
  const contentWidth = viewWidthPx * timelineZoom
  const hasCaptionTrack = tracks.some((track) => track.kind === 'caption')
  const showCaptionTrack = hasCaptionTrack
  const reserveCaptionTrack = false
  const trackOrder: Readonly<Record<TrackView['kind'], number>> = {
    caption: 0, card: 1, 'graphic-motion': 2, video: 3, audio: 4,
  }
  const visibleTracks = tracks
    .slice()
    .sort((left, right) => trackOrder[left.kind] - trackOrder[right.kind])
  const selectedVideo = selection?.kind === 'video'
    ? project?.tracks.find((track) => track.kind === 'video')?.clips?.find((clip) => clip.id === selection.id)
    : undefined
  const splitEnabled = Boolean(
    timelineEditable && selectedVideo && canSplitClip(project!, selectedVideo.id, currentTimeS) && !timelinePending,
  )
  const deleteEnabled = Boolean(
    timelineEditable && selectedVideo && !timelinePending,
  )

  useEffect(() => {
    if (!deleteNotice) return
    const timeout = window.setTimeout(() => setDeleteNotice(null), 5000)
    return () => window.clearTimeout(timeout)
  }, [deleteNotice])

  useEffect(() => {
    if (!runtime) {
      setRuntimeTimelineWidthPx(TIMELINE_WIDTH_PX)
      return
    }
    const surface = surfaceRef.current
    if (!surface) return
    const updateWidth = () => setRuntimeTimelineWidthPx(Math.max(1, surface.clientWidth))
    updateWidth()
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(updateWidth)
    observer.observe(surface)
    return () => observer.disconnect()
  }, [runtime])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target?.matches('input, textarea, [contenteditable="true"]')) return
      const modifier = event.ctrlKey || event.metaKey
      if (modifier && event.key.toLowerCase() === 'z') {
        event.preventDefault()
        if (event.shiftKey) void redoTimeline()
        else void undoTimeline()
        return
      }
      if ((event.key === 'Delete' || event.key === 'Backspace') && deleteEnabled && selectedVideo) {
        event.preventDefault()
        void editTimeline({ type: 'delete', clipId: selectedVideo.id })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [deleteEnabled, editTimeline, redoTimeline, selectedVideo, undoTimeline])

  useEffect(() => {
    if (!trimDrag || !project) return
    const handlePointerMove = (event: globalThis.PointerEvent) => {
      if (event.pointerId !== trimDrag.pointerId) return
      const deltaProgramS = (event.clientX - trimDrag.startClientX) / (viewWidthPx * timelineZoom) * viewDurationS
      const sourceS = trimDrag.kind === 'audio'
        ? trimAudioSourceAtProgramDelta(project, trimDrag.clipId, trimDrag.edge, deltaProgramS)
        : trimSourceAtProgramDelta(project, trimDrag.clipId, trimDrag.edge, deltaProgramS)
      if (sourceS === null) return
      trimSourceRef.current = sourceS
      try {
        const preview = applyTimelineEdit(project, trimDrag.kind === 'audio'
          ? { type: 'trim-audio', audioClipId: trimDrag.clipId, edge: trimDrag.edge, sourceS }
          : { type: 'trim', clipId: trimDrag.clipId, edge: trimDrag.edge, sourceS }).project
        setTrimPreview({ project: preview, sourceS })
      } catch {
        setTrimPreview(null)
      }
    }
    const handlePointerUp = (event: globalThis.PointerEvent) => {
      if (event.pointerId !== trimDrag.pointerId) return
      const sourceS = trimSourceRef.current ?? trimDrag.sourceS
      trimSourceRef.current = null
      setTrimDrag(null)
      setTrimPreview(null)
      if (Math.abs(sourceS - trimDrag.sourceS) > 1e-7) {
        void editTimeline(trimDrag.kind === 'audio'
          ? { type: 'trim-audio', audioClipId: trimDrag.clipId, edge: trimDrag.edge, sourceS }
          : { type: 'trim', clipId: trimDrag.clipId, edge: trimDrag.edge, sourceS })
      }
    }
    const handlePointerCancel = (event: globalThis.PointerEvent) => {
      if (event.pointerId !== trimDrag.pointerId) return
      trimSourceRef.current = null
      setTrimDrag(null)
      setTrimPreview(null)
    }
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    window.addEventListener('pointercancel', handlePointerCancel)
    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
      window.removeEventListener('pointercancel', handlePointerCancel)
    }
  }, [editTimeline, project, timelineZoom, trimDrag, viewDurationS, viewWidthPx])

  useEffect(() => {
    if (!audioMoveDrag || !project) return
    const handlePointerMove = (event: globalThis.PointerEvent) => {
      if (event.pointerId !== audioMoveDrag.pointerId) return
      const deltaProgramS = (event.clientX - audioMoveDrag.startClientX) / (viewWidthPx * timelineZoom) * viewDurationS
      const startS = moveAudioStartAtProgramDelta(project, audioMoveDrag.clipId, deltaProgramS)
      if (startS === null) return
      audioMoveStartRef.current = startS
      try {
        setTrimPreview({ project: applyTimelineEdit(project, {
          type: 'move-audio', audioClipId: audioMoveDrag.clipId, startS,
        }).project, sourceS: startS })
      } catch {
        setTrimPreview(null)
      }
    }
    const finish = (event: globalThis.PointerEvent, commit: boolean) => {
      if (event.pointerId !== audioMoveDrag.pointerId) return
      const startS = audioMoveStartRef.current ?? audioMoveDrag.startS
      audioMoveStartRef.current = null
      setAudioMoveDrag(null)
      setTrimPreview(null)
      if (commit && Math.abs(startS - audioMoveDrag.startS) > 1e-7) {
        void editTimeline({ type: 'move-audio', audioClipId: audioMoveDrag.clipId, startS })
      }
    }
    const handlePointerUp = (event: globalThis.PointerEvent) => finish(event, true)
    const handlePointerCancel = (event: globalThis.PointerEvent) => finish(event, false)
    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    window.addEventListener('pointercancel', handlePointerCancel)
    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
      window.removeEventListener('pointercancel', handlePointerCancel)
    }
  }, [audioMoveDrag, editTimeline, project, timelineZoom, viewDurationS, viewWidthPx])

  function startTrim(event: PointerEvent<HTMLButtonElement>, clip: ClipView, edge: TimelineTrimEdge, kind: 'video' | 'audio' = 'video') {
    event.preventDefault()
    event.stopPropagation()
    if (!timelineEditable || timelinePending) return
    const sourceS = edge === 'start' ? clip.sourceRange.startS : clip.sourceRange.endS
    trimSourceRef.current = sourceS
    setTrimDrag({ pointerId: event.pointerId, clipId: clip.id, edge, startClientX: event.clientX, sourceS, kind })
    setTrimPreview({ project: project!, sourceS })
  }

  function startAudioMove(event: PointerEvent<HTMLButtonElement>, clip: ClipView) {
    event.preventDefault()
    event.stopPropagation()
    if (!timelineEditable || timelinePending || clip.implicit || clip.linked) return
    audioMoveStartRef.current = clip.programRange.startS
    select({ kind: 'audio', id: clip.id })
    setAudioMoveDrag({
      pointerId: event.pointerId,
      clipId: clip.id,
      startClientX: event.clientX,
      startS: clip.programRange.startS,
    })
    setTrimPreview({ project: project!, sourceS: clip.programRange.startS })
  }

  function seekFromPointer(event: PointerEvent<HTMLDivElement>) {
    const surface = surfaceRef.current
    if (!surface) return
    const rect = surface.getBoundingClientRect()
    const pixelX = event.clientX - rect.left + surface.scrollLeft
    seek(pxToTime(pixelX, viewDurationS, viewWidthPx, {
      zoom: timelineZoom,
      fps: project?.fps,
      snapEnabled,
    }))
  }

  function contextTimeFromClientX(clientX: number) {
    const surface = surfaceRef.current
    if (!surface) return currentTimeS
    const rect = surface.getBoundingClientRect()
    const pixelX = clientX - rect.left + surface.scrollLeft
    return pxToTime(pixelX, viewDurationS, viewWidthPx, {
      zoom: timelineZoom,
      fps: project?.fps,
      snapEnabled,
    })
  }

  function zoomToTime(timeS: number) {
    const surface = surfaceRef.current
    const nextZoom = Math.min(MAX_ZOOM, timelineZoom + 0.5)
    setTimelineZoom(nextZoom)
    if (!surface || nextZoom === timelineZoom) return
    window.requestAnimationFrame(() => {
      const targetX = timeToPx(timeS, viewDurationS, viewWidthPx, nextZoom)
      surface.scrollLeft = Math.max(0, targetX - surface.clientWidth / 2)
      if (rulerScrollRef.current) rulerScrollRef.current.scrollLeft = surface.scrollLeft
    })
  }

  function openTimelineContextMenu(event: ReactMouseEvent<HTMLElement>, timeS?: number) {
    event.preventDefault()
    if ((event.target as HTMLElement).closest('[data-timeline-clip], .timeline-track-header')) return
    const contextTimeS = timeS ?? contextTimeFromClientX(event.clientX)
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      title: 'Timeline',
      subtitle: formatPreciseTime(contextTimeS),
      actions: [
        {
          id: 'move-playhead',
          label: `Move playhead to ${formatPreciseTime(contextTimeS)}`,
          icon: LocateFixed,
          onSelect: () => seek(contextTimeS),
        },
        {
          id: 'copy-timecode',
          label: 'Copy timecode',
          icon: Copy,
          onSelect: () => { void navigator.clipboard.writeText(formatPreciseTime(contextTimeS)) },
        },
        {
          id: 'zoom-here',
          label: 'Zoom to this position',
          icon: ZoomIn,
          separatorBefore: true,
          disabled: timelineZoom >= MAX_ZOOM,
          onSelect: () => zoomToTime(contextTimeS),
        },
        {
          id: 'fit-timeline',
          label: 'Fit timeline',
          icon: Ruler,
          onSelect: () => setTimelineZoom(1),
        },
        {
          id: 'toggle-snap',
          label: `${snapEnabled ? 'Disable' : 'Enable'} snapping`,
          icon: Magnet,
          onSelect: () => setSnapEnabled(!snapEnabled),
        },
      ],
    })
  }

  function clipSourceTimeAtProgramTime(clip: ClipView, programTimeS: number) {
    const speed = clip.speed && clip.speed > 0 ? clip.speed : 1
    const sourceTimeS = clip.sourceRange.startS + (programTimeS - clip.programRange.startS) * speed
    return Math.min(Math.max(sourceTimeS, clip.sourceRange.startS), clip.sourceRange.endS)
  }

  function openClipContextMenu(event: ReactMouseEvent<HTMLButtonElement>, track: TrackView, clip: ClipView) {
    event.preventDefault()
    event.stopPropagation()
    select({ kind: track.kind, id: clip.id })
    const bounds = event.currentTarget.getBoundingClientRect()
    const rawContextTimeS = clip.programRange.startS
      + Math.min(Math.max((event.clientX - bounds.left) / Math.max(bounds.width, 1), 0), 1)
      * (clip.programRange.endS - clip.programRange.startS)
    const frameDurationS = project && project.fps.numerator > 0 && project.fps.denominator > 0
      ? project.fps.denominator / project.fps.numerator
      : 1 / 30
    const contextTimeS = Math.min(
      Math.max(Math.round(rawContextTimeS / frameDurationS) * frameDurationS, clip.programRange.startS),
      clip.programRange.endS,
    )
    const sourceTimeS = clipSourceTimeAtProgramTime(clip, contextTimeS)
    if (track.kind === 'caption' || track.kind === 'card' || track.kind === 'graphic-motion') {
      openCueContextMenu(event, track, clip)
      return
    }
    if (track.kind === 'audio') {
      openAudioContextMenu(event, clip, contextTimeS, sourceTimeS)
      return
    }
    const startBounds = project ? trimSourceBounds(project, clip.id, 'start') : null
    const endBounds = project ? trimSourceBounds(project, clip.id, 'end') : null
    const canRestore = Boolean(startBounds && endBounds && (
      Math.abs(clip.sourceRange.startS - startBounds.minimum) > 1e-7
      || Math.abs(clip.sourceRange.endS - endBounds.maximum) > 1e-7
    ))
    const editable = track.kind === 'video' && timelineEditable && !timelinePending
    const associatedAudio = project?.tracks.find((candidate) => candidate.kind === 'audio')?.clips
      ?.find((candidate) => candidate.linkedClipId === clip.id && !candidate.implicit)
    const programDurationS = clip.programRange.endS - clip.programRange.startS
    const copy = (value: string) => { void navigator.clipboard.writeText(value) }
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      title: clip.displayName || 'Unknown media',
      subtitle: `${formatPreciseTime(clip.programRange.startS)} – ${formatPreciseTime(clip.programRange.endS)}`,
      actions: [
        {
          id: 'split-clip',
          label: `Split at ${formatPreciseTime(contextTimeS)}`,
          icon: Scissors,
          disabled: !editable || !project || !canSplitClip(project, clip.id, contextTimeS),
          onSelect: () => { void editTimeline({ type: 'split', clipId: clip.id, atS: contextTimeS }) },
        },
        {
          id: 'trim-in-here',
          label: 'Trim in point to here',
          icon: LocateFixed,
          disabled: !editable || !startBounds || sourceTimeS > startBounds.maximum + 1e-7,
          onSelect: () => { void editTimeline({ type: 'trim', clipId: clip.id, edge: 'start', sourceS: sourceTimeS }) },
        },
        {
          id: 'trim-out-here',
          label: 'Trim out point to here',
          icon: LocateFixed,
          disabled: !editable || !endBounds || sourceTimeS < endBounds.minimum - 1e-7,
          onSelect: () => { void editTimeline({ type: 'trim', clipId: clip.id, edge: 'end', sourceS: sourceTimeS }) },
        },
        {
          id: 'restore-bounds',
          label: 'Restore available media bounds',
          icon: RotateCcw,
          disabled: !editable || !canRestore,
          onSelect: () => { void editTimeline({ type: 'restore-bounds', clipId: clip.id }) },
        },
        ...(clip.audioMode === 'detached' ? [
          {
            id: 'locate-audio',
            label: 'Locate associated audio',
            icon: LocateFixed,
            disabled: !associatedAudio,
            onSelect: () => associatedAudio && select({ kind: 'audio', id: associatedAudio.id }),
          },
          {
            id: 'unlink-audio',
            label: associatedAudio?.linked ? 'Unlink audio and video' : 'Relink audio and video',
            icon: associatedAudio?.linked ? Link2Off : Link,
            disabled: !editable || !associatedAudio,
            onSelect: () => associatedAudio && void editTimeline(associatedAudio.linked
              ? { type: 'unlink-audio', audioClipId: associatedAudio.id }
              : { type: 'link-audio', audioClipId: associatedAudio.id }),
          },
          {
            id: 'attach-audio',
            label: 'Attach audio back to video',
            icon: Link,
            disabled: !editable || !associatedAudio?.linked,
            onSelect: () => { void editTimeline({ type: 'attach-audio', clipId: clip.id }) },
          },
        ] : [
          {
            id: 'detach-audio',
            label: 'Detach audio',
            icon: Link2Off,
            disabled: !editable,
            onSelect: () => { void editTimeline({ type: 'detach-audio', clipId: clip.id }) },
          },
          {
            id: 'mute-video-audio',
            label: clip.audioMode === 'muted' ? 'Unmute original audio' : 'Mute original audio',
            icon: clip.audioMode === 'muted' ? Volume2 : VolumeX,
            disabled: !editable,
            onSelect: () => { void editTimeline({ type: 'mute-video-audio', clipId: clip.id, muted: clip.audioMode !== 'muted' }) },
          },
        ]),
        {
          id: 'move-playhead',
          label: `Move playhead to ${formatPreciseTime(contextTimeS)}`,
          icon: LocateFixed,
          separatorBefore: true,
          onSelect: () => seek(contextTimeS),
        },
        {
          id: 'copy-range',
          label: 'Copy time range',
          icon: Copy,
          submenu: [
            {
              id: 'copy-program-range',
              label: `Program ${formatPreciseTime(clip.programRange.startS)} – ${formatPreciseTime(clip.programRange.endS)}`,
              onSelect: () => copy(`${formatPreciseTime(clip.programRange.startS)} - ${formatPreciseTime(clip.programRange.endS)}`),
            },
            {
              id: 'copy-source-range',
              label: `Source ${formatPreciseTime(clip.sourceRange.startS)} – ${formatPreciseTime(clip.sourceRange.endS)}`,
              onSelect: () => copy(`${formatPreciseTime(clip.sourceRange.startS)} - ${formatPreciseTime(clip.sourceRange.endS)}`),
            },
            {
              id: 'copy-duration',
              label: `Duration ${formatPreciseTime(programDurationS)}`,
              onSelect: () => copy(formatPreciseTime(programDurationS)),
            },
          ],
        },
        {
          id: 'clip-info',
          label: 'View clip information',
          icon: Info,
          onSelect: () => setClipInfo(clip),
        },
        {
          id: 'ripple-delete',
          label: 'Ripple delete',
          shortcut: 'Delete',
          icon: Trash2,
          separatorBefore: true,
          danger: true,
          disabled: !editable,
          onSelect: () => {
            const historyLength = store.getState().timelinePast.length
            void editTimeline({ type: 'delete', clipId: clip.id }).then(() => {
              if (store.getState().timelinePast.length > historyLength) {
                setDeleteNotice(`${clip.displayName || 'Clip'} ripple deleted`)
              }
            })
          },
        },
      ],
    })
  }

  function openAudioContextMenu(
    event: ReactMouseEvent<HTMLButtonElement>,
    clip: ClipView,
    contextTimeS: number,
    sourceTimeS: number,
  ) {
    const video = project?.tracks.find((track) => track.kind === 'video')?.clips
      ?.find((candidate) => candidate.id === clip.linkedClipId)
    const editable = timelineEditable && !timelinePending
    const detached = !clip.implicit
    const canEditIndependently = detached && !clip.linked && editable
    const copy = (value: string) => { void navigator.clipboard.writeText(value) }
    const programDurationS = clip.programRange.endS - clip.programRange.startS
    const startTrimEnabled = canEditIndependently && sourceTimeS < clip.sourceRange.endS - 1e-7
    const endTrimEnabled = canEditIndependently && sourceTimeS > clip.sourceRange.startS + 1e-7
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      title: clip.displayName || 'Audio',
      subtitle: `${formatPreciseTime(clip.programRange.startS)} – ${formatPreciseTime(clip.programRange.endS)}`,
      actions: [
        {
          id: 'select-video',
          label: 'Select associated video clip',
          icon: LocateFixed,
          disabled: !video,
          onSelect: () => video && select({ kind: 'video', id: video.id }),
        },
        {
          id: 'go-to-audio-start',
          label: 'Go to clip start',
          icon: LocateFixed,
          onSelect: () => seek(clip.programRange.startS),
        },
        ...(clip.implicit ? [{
          id: 'detach-audio',
          label: 'Detach audio',
          icon: Link2Off,
          disabled: !editable || !video,
          onSelect: () => video && void editTimeline({ type: 'detach-audio', clipId: video.id }),
        }] : [{
          id: 'toggle-link',
          label: clip.linked ? 'Unlink audio and video' : 'Relink audio to video',
          icon: clip.linked ? Link2Off : Link,
          disabled: !editable || !video,
          onSelect: () => { void editTimeline(clip.linked
            ? { type: 'unlink-audio', audioClipId: clip.id }
            : { type: 'link-audio', audioClipId: clip.id }) },
        }]),
        ...(canEditIndependently ? [
          {
            id: 'trim-audio-in',
            label: 'Trim audio in point to here',
            icon: LocateFixed,
            disabled: !startTrimEnabled,
            onSelect: () => { void editTimeline({ type: 'trim-audio', audioClipId: clip.id, edge: 'start', sourceS: sourceTimeS }) },
          },
          {
            id: 'trim-audio-out',
            label: 'Trim audio out point to here',
            icon: LocateFixed,
            disabled: !endTrimEnabled,
            onSelect: () => { void editTimeline({ type: 'trim-audio', audioClipId: clip.id, edge: 'end', sourceS: sourceTimeS }) },
          },
        ] : []),
        {
          id: 'mute-audio',
          label: clip.muted ? 'Unmute audio' : 'Mute audio',
          icon: clip.muted ? Volume2 : VolumeX,
          disabled: !editable,
          onSelect: () => {
            if (clip.implicit && video) void editTimeline({ type: 'mute-video-audio', clipId: video.id, muted: !clip.muted })
            else void editTimeline({ type: 'mute-audio', audioClipId: clip.id, muted: !clip.muted })
          },
        },
        {
          id: 'copy-audio-range',
          label: 'Copy time range',
          icon: Copy,
          separatorBefore: true,
          onSelect: () => copy(`${formatPreciseTime(clip.programRange.startS)} - ${formatPreciseTime(clip.programRange.endS)}`),
        },
        {
          id: 'audio-info',
          label: 'View media information',
          icon: Info,
          onSelect: () => setClipInfo(clip),
        },
        ...(canEditIndependently ? [{
          id: 'ripple-delete-audio',
          label: 'Ripple delete audio',
          shortcut: 'Delete',
          icon: Trash2,
          separatorBefore: true,
          danger: true,
          onSelect: () => {
            const historyLength = store.getState().timelinePast.length
            void editTimeline({ type: 'delete-audio', audioClipId: clip.id }).then(() => {
              if (store.getState().timelinePast.length > historyLength) setDeleteNotice(`${clip.displayName || 'Audio'} ripple deleted`)
            })
          },
        }] : []),
      ],
    })
  }

  function cueOperationId(kind: TrackView['kind']) {
    return kind === 'caption' ? 'captions'
      : kind === 'card' ? 'content-cards'
        : kind === 'graphic-motion' ? 'graphic-motion'
          : ''
  }

  function openCueContextMenu(event: ReactMouseEvent<HTMLButtonElement>, track: TrackView, clip: ClipView) {
    const operationId = cueOperationId(track.kind)
    const operation = project?.operations?.find((candidate) => candidate.id === operationId)
    const canEdit = Boolean(operation?.editable && !store.getState().operationDrafts[operationId]?.pending)
    const canToggle = track.kind !== 'caption' && canEdit
    const kindLabel = track.kind === 'caption' ? 'Caption'
      : track.kind === 'card' ? 'Content Card'
        : 'Graphic Motion'
    const programRange = `${formatPreciseTime(clip.programRange.startS)} - ${formatPreciseTime(clip.programRange.endS)}`
    const editInInspector = () => {
      window.requestAnimationFrame(() => {
        const inspector = document.querySelector<HTMLElement>(`[data-cue-inspector="${CSS.escape(clip.id)}"]`)
        inspector?.scrollIntoView({ block: 'nearest' })
        inspector?.focus({ preventScroll: true })
      })
    }
    const toggleEnabled = () => {
      if (!canToggle) return
      const state = store.getState()
      state.editOperationDraft(operationId, { cueId: clip.id, enabled: !clip.enabled })
      void state.saveOperationDraft(operationId)
    }
    setContextMenu({
      x: event.clientX,
      y: event.clientY,
      title: kindLabel,
      subtitle: clip.summary || clip.displayName || clip.id,
      actions: [
        {
          id: 'edit-cue',
          label: 'Edit in Inspector',
          icon: Pencil,
          disabled: !canEdit,
          onSelect: editInInspector,
        },
        {
          id: 'go-to-cue-start',
          label: 'Go to Cue start',
          icon: LocateFixed,
          onSelect: () => seek(clip.programRange.startS),
        },
        {
          id: 'play-cue-only',
          label: 'Play this Cue only',
          icon: Play,
          onSelect: () => playRange(clip.programRange.startS, clip.programRange.endS),
        },
        ...(track.kind === 'caption' ? [] : [{
          id: 'toggle-cue',
          label: clip.enabled === false ? 'Enable Cue' : 'Disable Cue',
          icon: Power,
          disabled: !canToggle,
          onSelect: toggleEnabled,
        }]),
        {
          id: 'copy-cue-range',
          label: 'Copy program time range',
          icon: Copy,
          separatorBefore: true,
          onSelect: () => { void navigator.clipboard.writeText(programRange) },
        },
        {
          id: 'view-cue-source',
          label: track.kind === 'caption' ? 'View source text' : 'View source text / decision rationale',
          icon: FileText,
          onSelect: () => setCueInfo({ clip, operationId, view: 'source' }),
        },
        {
          id: 'view-cue-review',
          label: 'View preview and review evidence',
          icon: Info,
          onSelect: () => setCueInfo({ clip, operationId, view: 'review' }),
        },
      ],
    })
  }

  function handleTimelineContextKey(event: ReactKeyboardEvent<HTMLElement>) {
    if (!(event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10'))) return
    event.preventDefault()
    const rect = event.currentTarget.getBoundingClientRect()
    openTimelineContextMenu(event as unknown as ReactMouseEvent<HTMLElement>, currentTimeS)
    setContextMenu((menu) => menu ? { ...menu, x: rect.left + rect.width / 2, y: rect.top + Math.min(64, rect.height / 2) } : menu)
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    if (!hasMedia || event.button !== 0) return
    event.currentTarget.setPointerCapture(event.pointerId)
    seekFromPointer(event)
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) seekFromPointer(event)
  }

  const labelIntervalS = rulerLabelInterval(viewDurationS, contentWidth)
  const rulerSeconds = Array.from({ length: Math.floor(viewDurationS) + 1 }, (_, second) => second)
  if (rulerSeconds.at(-1) !== viewDurationS) rulerSeconds.push(viewDurationS)
  const rulerTicks = rulerSeconds.map((second) => {
    const terminal = second === viewDurationS
    const regularMajor = Number.isInteger(second) && second % labelIntervalS === 0
    const terminalGapPx = timeToPx(viewDurationS - second, viewDurationS, viewWidthPx, timelineZoom)
    const major = terminal || (regularMajor && (
      Number.isInteger(viewDurationS) || second === 0 || terminalGapPx >= MIN_RULER_LABEL_SPACING_PX
    ))
    return {
      second,
      terminal,
      major,
      left: `${timeToPx(second, viewDurationS, viewWidthPx, timelineZoom)}px`,
      label: major ? formatRulerTime(second) : null,
    }
  })

  return (
    <section className={`timeline-panel${hasMedia ? '' : ' timeline-panel--empty'}`} role="region" aria-label="Timeline">
      <header className="timeline-toolbar" aria-label="Timeline tools">
        {!runtime && <button type="button" aria-label="Add track" disabled={!hasMedia}><Plus aria-hidden size={18} /></button>}
        <button type="button" aria-label="Select tool"><MousePointer2 aria-hidden size={18} /></button>
        <button className={snapEnabled ? 'is-active' : ''} type="button" aria-label="Toggle snap" aria-pressed={snapEnabled} onClick={() => setSnapEnabled(!snapEnabled)}><Magnet aria-hidden size={18} /></button>
        {(hasMedia || timelinePast.length > 0 || timelineFuture.length > 0) && (
          <>
            <span className="timeline-toolbar-divider" />
            <button type="button" aria-label="Undo" title="Undo timeline edit (Ctrl+Z)" disabled={!timelinePast.length || timelinePending} onClick={() => void undoTimeline()}><Undo2 aria-hidden size={18} /></button>
            <button type="button" aria-label="Redo" title="Redo timeline edit (Ctrl+Shift+Z)" disabled={!timelineFuture.length || timelinePending} onClick={() => void redoTimeline()}><Redo2 aria-hidden size={18} /></button>
            <span className="timeline-toolbar-divider" />
            <button type="button" aria-label="Split" title={timelineEditable ? 'Split selected clip at playhead' : 'This project has no editable cut operation'} disabled={!splitEnabled} onClick={() => selectedVideo && void editTimeline({ type: 'split', clipId: selectedVideo.id, atS: currentTimeS })}><Scissors aria-hidden size={18} /></button>
            {!runtime && <DisabledTimelineCommand name="Speed" descriptionId="timeline-speed-description"><Gauge aria-hidden size={18} /></DisabledTimelineCommand>}
            {!runtime && <DisabledTimelineCommand name="Reverse" descriptionId="timeline-reverse-description"><RotateCcw aria-hidden size={18} /></DisabledTimelineCommand>}
            {!runtime && <DisabledTimelineCommand name="Duplicate" descriptionId="timeline-duplicate-description"><Copy aria-hidden size={18} /></DisabledTimelineCommand>}
            {!runtime && <DisabledTimelineCommand name="Copy" descriptionId="timeline-copy-description"><Copy aria-hidden size={18} /></DisabledTimelineCommand>}
            {!runtime && <DisabledTimelineCommand name="Reorder tracks" descriptionId="timeline-reorder-description"><ArrowUpDown aria-hidden size={18} /></DisabledTimelineCommand>}
            <button type="button" aria-label="Delete clip" title={timelineEditable ? 'Delete selected clip (Delete)' : 'This project has no editable cut operation'} disabled={!deleteEnabled} onClick={() => selectedVideo && void editTimeline({ type: 'delete', clipId: selectedVideo.id })}><Trash2 aria-hidden size={18} /></button>
          </>
        )}
        {timelinePending && <span className="timeline-edit-status" role="status">Saving timeline…</span>}
        {!timelinePending && timelineError && <span className="timeline-edit-status timeline-edit-status--error" role="alert" title={timelineError}>{timelineError}</span>}
        <span className="timeline-toolbar-spacer" />
        <button type="button" aria-label="Fit timeline" onClick={() => setTimelineZoom(1)}><Ruler aria-hidden size={20} /></button>
        <button type="button" aria-label="Zoom out timeline" disabled={timelineZoom <= MIN_ZOOM} onClick={() => setTimelineZoom(timelineZoom - ZOOM_STEP)}><ZoomOut aria-hidden size={20} /></button>
        <button type="button" aria-label="Zoom in timeline" disabled={timelineZoom >= MAX_ZOOM} onClick={() => setTimelineZoom(timelineZoom + ZOOM_STEP)}><ZoomIn aria-hidden size={20} /></button>
      </header>
      <div className="timeline-body">
        {hasMedia && (
          <>
            <div className="timeline-ruler-gutter" />
            <div className="timeline-ruler-scroll" ref={rulerScrollRef} onContextMenu={openTimelineContextMenu}>
              <div className="timeline-ruler" style={{ width: `${contentWidth}px` }}>
                {rulerTicks.map((tick) => (
                  <i
                    key={tick.second}
                    className={`timeline-ruler-tick${tick.major ? ' timeline-ruler-tick--major' : ''}${tick.terminal ? ' timeline-ruler-tick--terminal' : ''}`}
                    data-timeline-ruler-tick={tick.second}
                    style={{ left: tick.left }}
                  >
                    {tick.label && <span>{tick.label}</span>}
                  </i>
                ))}
              </div>
            </div>
          </>
        )}
        <div
          className={`timeline-gutter${showCaptionTrack ? ' timeline-gutter--with-captions' : ''}`}
          ref={gutterRef}
          onScroll={(event) => {
            if (surfaceRef.current && surfaceRef.current.scrollTop !== event.currentTarget.scrollTop) {
              surfaceRef.current.scrollTop = event.currentTarget.scrollTop
            }
          }}
        >
          {reserveCaptionTrack && <div className="timeline-track-reserved" aria-hidden="true" />}
          {visibleTracks.map((track) => <TrackHeader key={track.id} track={track} runtime={runtime} />)}
        </div>
        <div
          className="timeline-surface"
          data-timeline-surface
          tabIndex={0}
          aria-label="Timeline canvas"
          ref={surfaceRef}
          onContextMenu={openTimelineContextMenu}
          onKeyDown={handleTimelineContextKey}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={(event) => event.currentTarget.releasePointerCapture(event.pointerId)}
          onPointerCancel={(event) => event.currentTarget.releasePointerCapture(event.pointerId)}
          onScroll={(event) => {
            if (rulerScrollRef.current) rulerScrollRef.current.scrollLeft = event.currentTarget.scrollLeft
            if (gutterRef.current && gutterRef.current.scrollTop !== event.currentTarget.scrollTop) {
              gutterRef.current.scrollTop = event.currentTarget.scrollTop
            }
          }}
        >
          <div
            className={`timeline-content${showCaptionTrack ? ' timeline-content--with-captions' : ''}`}
            style={{ width: hasMedia ? `${contentWidth}px` : 'calc(100% - 48px)' }}
          >
            {hasMedia && reserveCaptionTrack && <div className="timeline-lane timeline-lane--reserved" aria-hidden="true" />}
            {hasMedia ? visibleTracks.map((track) => (
              <div className={`timeline-lane timeline-lane--${track.kind}`} key={track.id}>
                {(track.clips ?? []).map((clip) => (
                  <Clip
                    key={clip.id}
                    track={track}
                    clip={clip}
                    durationS={viewDurationS}
                    timelineZoom={timelineZoom}
                    timelineWidthPx={viewWidthPx}
                    presentationInsetPx={presentationInsetPx}
                    selection={selection}
                    select={select}
                    editable={timelineEditable && (
                      track.kind === 'video'
                      || (track.kind === 'audio' && !clip.implicit && !clip.linked)
                    )}
                    trimming={trimDrag?.clipId === clip.id ? trimDrag.edge : null}
                    onTrimStart={startTrim}
                    onAudioMoveStart={startAudioMove}
                    onContextMenu={openClipContextMenu}
                  />
                ))}
              </div>
            )) : (
              <div className="timeline-empty-state"><span aria-hidden>▣</span><p>{runtime ? 'No timeline media in this project' : 'Drag media here to start creating'}</p></div>
            )}
            <div
              className="timeline-playhead"
              style={{ left: `${timeToPx(currentTimeS, viewDurationS, viewWidthPx, timelineZoom)}px` }}
              aria-hidden="true"
            ><span /></div>
          </div>
        </div>
        {hasMedia && <output className="timeline-playhead-time" aria-label="Playhead time">{formatTimelineTime(currentTimeS)}</output>}
      </div>
      {contextMenu ? <TimelineContextMenu {...contextMenu} onClose={() => setContextMenu(null)} /> : null}
      {deleteNotice ? (
        <div className="timeline-undo-toast" role="status">
          <span>{deleteNotice}</span>
          <button type="button" onClick={() => { void undoTimeline().then(() => setDeleteNotice(null)) }}>Undo</button>
          <button type="button" aria-label="Dismiss delete notification" onClick={() => setDeleteNotice(null)}>×</button>
        </div>
      ) : null}
      {clipInfo ? (
        <div className="timeline-dialog-backdrop" role="presentation" onMouseDown={() => setClipInfo(null)}>
          <section className="timeline-clip-info-dialog" role="dialog" aria-modal="true" aria-labelledby="clip-info-title" onMouseDown={(event) => event.stopPropagation()}>
            <header><h2 id="clip-info-title">{clipInfo.displayName || 'Unknown media'}</h2><button type="button" aria-label="Close clip information" onClick={() => setClipInfo(null)}>×</button></header>
            <dl>
              <div><dt>Clip ID</dt><dd>{clipInfo.id}</dd></div>
              <div><dt>Program range</dt><dd>{formatPreciseTime(clipInfo.programRange.startS)} – {formatPreciseTime(clipInfo.programRange.endS)}</dd></div>
              <div><dt>Source range</dt><dd>{formatPreciseTime(clipInfo.sourceRange.startS)} – {formatPreciseTime(clipInfo.sourceRange.endS)}</dd></div>
              <div><dt>Duration</dt><dd>{formatPreciseTime(clipInfo.programRange.endS - clipInfo.programRange.startS)}</dd></div>
              <div><dt>Speed</dt><dd>{(clipInfo.speed ?? 1).toFixed(2)}×</dd></div>
            </dl>
          </section>
        </div>
      ) : null}
      {cueInfo ? (
        <div className="timeline-dialog-backdrop" role="presentation" onMouseDown={() => setCueInfo(null)}>
          <section className="timeline-clip-info-dialog timeline-cue-info-dialog" role="dialog" aria-modal="true" aria-labelledby="cue-info-title" onMouseDown={(event) => event.stopPropagation()}>
            <header><h2 id="cue-info-title">{cueInfo.view === 'source' ? 'Cue source and decision' : 'Cue review evidence'}</h2><button type="button" aria-label="Close Cue information" onClick={() => setCueInfo(null)}>×</button></header>
            <dl>
              <div><dt>Cue ID</dt><dd>{cueInfo.clip.id}</dd></div>
              <div><dt>Program range</dt><dd>{formatPreciseTime(cueInfo.clip.programRange.startS)} – {formatPreciseTime(cueInfo.clip.programRange.endS)}</dd></div>
              {cueInfo.view === 'source' ? (
                <>
                  <div><dt>Source range</dt><dd>{formatPreciseTime(cueInfo.clip.sourceRange.startS)} – {formatPreciseTime(cueInfo.clip.sourceRange.endS)}</dd></div>
                  <div><dt>Source text</dt><dd>{cueInfo.clip.sourceText || cueInfo.clip.summary || 'No source text recorded'}</dd></div>
                  <div><dt>Decision rationale</dt><dd>{cueInfo.clip.decisionRationale || 'No cue-specific rationale recorded'}</dd></div>
                  {cueInfo.clip.evidenceRefs?.length ? <div><dt>Evidence refs</dt><dd>{cueInfo.clip.evidenceRefs.join(', ')}</dd></div> : null}
                </>
              ) : (
                <>
                  <div><dt>Review status</dt><dd>{cueInfo.clip.reviewStatus || 'Not recorded'}</dd></div>
                  <div><dt>Decision mode</dt><dd>{cueInfo.clip.reviewMode || 'Not recorded'}</dd></div>
                  <div><dt>Evidence</dt><dd>{[
                    ...(cueInfo.clip.reviewEvidence ?? []),
                    ...(project?.operations?.find((operation) => operation.id === cueInfo.operationId)?.preview?.evidenceHashes ?? []),
                  ].join(', ') || 'No review evidence recorded'}</dd></div>
                </>
              )}
              {Object.entries(cueInfo.clip.metadata ?? {}).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
            </dl>
          </section>
        </div>
      ) : null}
    </section>
  )
}
