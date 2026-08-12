import { useRef, type PointerEvent, type ReactNode } from 'react'
import {
  ArrowUpDown,
  Copy,
  Eye,
  Gauge,
  Lock,
  Magnet,
  MousePointer2,
  Plus,
  Redo2,
  RotateCcw,
  Ruler,
  Scissors,
  Trash2,
  Undo2,
  VolumeX,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { ClipView, EditorSelection, TrackView } from './editor-model'
import type { EditorState } from './editor-store'

const TIMELINE_WIDTH_PX = 876
const CLIP_CONTENT_WIDTH_PX = 780
const MIN_ZOOM = 0.5
const MAX_ZOOM = 2
const ZOOM_STEP = 0.25

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

function TrackHeader({ track }: { track: TrackView }) {
  const badge = track.kind === 'video' ? 'V1' : track.kind === 'audio' ? 'A1' : 'C1'
  return (
    <div className={`timeline-track-header timeline-track-header--${track.kind}`}>
      <span className="timeline-track-badge">{badge}</span>
      <button type="button" aria-label={`Lock ${track.name} track`} disabled title="Track locking is not available in project protocol V1."><Lock aria-hidden size={14} /></button>
      <button type="button" aria-label={`Show ${track.name} track`} disabled title="Track visibility is fixed in project protocol V1."><Eye aria-hidden size={14} /></button>
      <button type="button" aria-label={`Mute ${track.name} track`} disabled title="Track muting is not available in project protocol V1."><VolumeX aria-hidden size={14} /></button>
    </div>
  )
}

function Waveform() {
  return (
    <span className="timeline-waveform" aria-hidden="true">
      {Array.from({ length: 76 }, (_, index) => (
        <i key={index} style={{ height: `${8 + ((index * 11) % 28)}px` }} />
      ))}
    </span>
  )
}

function Clip({
  track,
  clip,
  durationS,
  selection,
  select,
}: {
  track: TrackView
  clip: ClipView
  durationS: number
  selection: EditorSelection
  select: (selection: EditorSelection) => void
}) {
  const kind = track.kind
  const id = clip.id
  const selected = selection?.kind === kind && selection.id === id
  const left = 16 + timeToPx(clip.programRange.startS, durationS, CLIP_CONTENT_WIDTH_PX)
  const width = timeToPx(
    clip.programRange.endS - clip.programRange.startS,
    durationS,
    CLIP_CONTENT_WIDTH_PX,
  )
  return (
    <button
      type="button"
      className={`timeline-clip timeline-clip--${kind}`}
      data-timeline-clip={id}
      aria-label={`${track.name} clip`}
      aria-pressed={selected}
      style={{ left: `${left}px`, width: `${width}px` }}
      onPointerDown={() => select({ kind, id })}
    >
      {kind === 'video' && <span className="timeline-thumbnails" aria-hidden="true">{Array.from({ length: 10 }, (_, index) => <i key={index} />)}</span>}
      {kind === 'audio' && <Waveform />}
      {kind === 'caption' && <span className="timeline-caption-cue">{['Opening hook', "technology shouldn't", 'take you away', 'from the world', 'keep you curious'][Number(id.at(-1)) - 1]}</span>}
      {kind !== 'caption' && <span className="timeline-clip-label">{kind === 'audio' ? 'City Walk - Audio' : 'City Walk.mp4'}</span>}
    </button>
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
  const surfaceRef = useRef<HTMLDivElement>(null)
  const rulerScrollRef = useRef<HTMLDivElement>(null)
  const durationS = project?.durationS ?? 0
  const tracks = project?.tracks ?? []
  const hasMedia = durationS > 0 && tracks.length > 0
  const contentWidth = TIMELINE_WIDTH_PX * timelineZoom
  const hasCaptionTrack = tracks.some((track) => track.kind === 'caption')
  const showCaptionTrack = hasCaptionTrack && selection?.kind === 'caption'
  const reserveCaptionTrack = hasCaptionTrack && !showCaptionTrack
  const trackOrder: Readonly<Record<TrackView['kind'], number>> = { caption: 0, video: 1, audio: 2 }
  const visibleTracks = tracks
    .filter((track) => track.kind !== 'caption' || showCaptionTrack)
    .slice()
    .sort((left, right) => trackOrder[left.kind] - trackOrder[right.kind])

  function seekFromPointer(event: PointerEvent<HTMLDivElement>) {
    const surface = surfaceRef.current
    if (!surface) return
    const rect = surface.getBoundingClientRect()
    const pixelX = event.clientX - rect.left + surface.scrollLeft
    seek(pxToTime(pixelX, durationS, TIMELINE_WIDTH_PX, {
      zoom: timelineZoom,
      fps: project?.fps,
      snapEnabled,
    }))
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    if (!hasMedia || event.button !== 0) return
    event.currentTarget.setPointerCapture(event.pointerId)
    seekFromPointer(event)
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) seekFromPointer(event)
  }

  const rulerTicks = Array.from({ length: 11 }, (_, index) => ({
    left: `${index * 10}%`,
    label: formatRulerTime((durationS * index) / 10),
  }))

  return (
    <section className={`timeline-panel${hasMedia ? '' : ' timeline-panel--empty'}`} role="region" aria-label="Timeline">
      <header className="timeline-toolbar" aria-label="Timeline tools">
        <button type="button" aria-label="Add track" disabled={!hasMedia}><Plus aria-hidden size={18} /></button>
        <button type="button" aria-label="Select tool"><MousePointer2 aria-hidden size={18} /></button>
        <button className={snapEnabled ? 'is-active' : ''} type="button" aria-label="Toggle snap" aria-pressed={snapEnabled} onClick={() => setSnapEnabled(!snapEnabled)}><Magnet aria-hidden size={18} /></button>
        <span className="timeline-toolbar-divider" />
        <button type="button" aria-label="Undo" disabled><Undo2 aria-hidden size={18} /></button>
        <button type="button" aria-label="Redo" disabled><Redo2 aria-hidden size={18} /></button>
        <span className="timeline-toolbar-divider" />
        <button type="button" aria-label="Split" disabled><Scissors aria-hidden size={18} /></button>
        <DisabledTimelineCommand name="Speed" descriptionId="timeline-speed-description"><Gauge aria-hidden size={18} /></DisabledTimelineCommand>
        <DisabledTimelineCommand name="Reverse" descriptionId="timeline-reverse-description"><RotateCcw aria-hidden size={18} /></DisabledTimelineCommand>
        <DisabledTimelineCommand name="Duplicate" descriptionId="timeline-duplicate-description"><Copy aria-hidden size={18} /></DisabledTimelineCommand>
        <DisabledTimelineCommand name="Copy" descriptionId="timeline-copy-description"><Copy aria-hidden size={18} /></DisabledTimelineCommand>
        <DisabledTimelineCommand name="Reorder tracks" descriptionId="timeline-reorder-description"><ArrowUpDown aria-hidden size={18} /></DisabledTimelineCommand>
        <button type="button" aria-label="Delete clip" disabled><Trash2 aria-hidden size={18} /></button>
        <span className="timeline-toolbar-spacer" />
        <button type="button" aria-label="Fit timeline" onClick={() => setTimelineZoom(1)}><Ruler aria-hidden size={20} /></button>
        <button type="button" aria-label="Zoom out timeline" disabled={timelineZoom <= MIN_ZOOM} onClick={() => setTimelineZoom(timelineZoom - ZOOM_STEP)}><ZoomOut aria-hidden size={20} /></button>
        <button type="button" aria-label="Zoom in timeline" disabled={timelineZoom >= MAX_ZOOM} onClick={() => setTimelineZoom(timelineZoom + ZOOM_STEP)}><ZoomIn aria-hidden size={20} /></button>
      </header>
      <div className="timeline-body">
        {hasMedia && (
          <>
            <div className="timeline-ruler-gutter" />
            <div className="timeline-ruler-scroll" ref={rulerScrollRef}>
              <div className="timeline-ruler" style={{ width: `${contentWidth}px` }}>
                {rulerTicks.map((tick) => <span key={tick.left} style={{ left: tick.left }}>{tick.label}</span>)}
              </div>
            </div>
          </>
        )}
        <div className="timeline-gutter">
          {reserveCaptionTrack && <div className="timeline-track-reserved" aria-hidden="true" />}
          {visibleTracks.map((track) => <TrackHeader key={track.id} track={track} />)}
        </div>
        <div
          className="timeline-surface"
          data-timeline-surface
          ref={surfaceRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={(event) => event.currentTarget.releasePointerCapture(event.pointerId)}
          onPointerCancel={(event) => event.currentTarget.releasePointerCapture(event.pointerId)}
          onScroll={(event) => {
            if (rulerScrollRef.current) rulerScrollRef.current.scrollLeft = event.currentTarget.scrollLeft
          }}
        >
          <div
            className={`timeline-content${showCaptionTrack ? ' timeline-content--with-captions' : ''}`}
            style={{ width: hasMedia ? `${contentWidth}px` : 'calc(100% - 48px)' }}
          >
            {hasMedia && reserveCaptionTrack && <div className="timeline-lane timeline-lane--reserved" aria-hidden="true" />}
            {hasMedia ? visibleTracks.map((track) => (
              <div className={`timeline-lane timeline-lane--${track.kind}`} key={track.id}>
                {(track.clips ?? [{
                  id: track.kind === 'caption' ? 'caption-1' : track.id,
                  sourceRange: { startS: 0, endS: durationS },
                  programRange: { startS: 0, endS: durationS },
                }]).map((clip) => (
                  <Clip key={clip.id} track={track} clip={clip} durationS={durationS} selection={selection} select={select} />
                ))}
              </div>
            )) : (
              <div className="timeline-empty-state"><span aria-hidden>▣</span><p>Drag media here to start creating</p></div>
            )}
            <div
              className="timeline-playhead"
              style={{ left: `${timeToPx(currentTimeS, durationS, TIMELINE_WIDTH_PX, timelineZoom)}px` }}
              aria-hidden="true"
            ><span /></div>
          </div>
        </div>
        {hasMedia && <output className="timeline-playhead-time" aria-label="Playhead time">{formatTimelineTime(currentTimeS)}</output>}
      </div>
    </section>
  )
}
