import { useEffect, useRef, useState, type PointerEvent, type ReactNode } from 'react'
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
}: {
  track: TrackView
  clip: ClipView
  durationS: number
  timelineZoom: number
  timelineWidthPx: number
  presentationInsetPx: number
  selection: EditorSelection
  select: (selection: EditorSelection) => void
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
  return (
    <button
      type="button"
      className={`timeline-clip timeline-clip--${kind}`}
      data-timeline-clip={id}
      aria-label={`${track.name} ${kind === 'video' || kind === 'audio' ? 'clip' : 'cue'}`}
      aria-pressed={selected}
      style={{ left: `${left}px`, width: `${width}px` }}
      onPointerDown={() => select({ kind, id })}
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
  const gutterRef = useRef<HTMLDivElement>(null)
  const rulerScrollRef = useRef<HTMLDivElement>(null)
  const [runtimeTimelineWidthPx, setRuntimeTimelineWidthPx] = useState(TIMELINE_WIDTH_PX)
  const durationS = project?.durationS ?? 0
  const tracks = project?.tracks ?? []
  const runtime = Boolean(project?.runtime)
  const hasMedia = durationS > 0 && tracks.length > 0
  const timelineWidthPx = runtime ? runtimeTimelineWidthPx : TIMELINE_WIDTH_PX
  const presentationInsetPx = runtime ? 0 : TIMELINE_PRESENTATION_INSET_PX
  const contentWidth = timelineWidthPx * timelineZoom
  const hasCaptionTrack = tracks.some((track) => track.kind === 'caption')
  const showCaptionTrack = hasCaptionTrack
  const reserveCaptionTrack = false
  const trackOrder: Readonly<Record<TrackView['kind'], number>> = {
    caption: 0, card: 1, 'graphic-motion': 2, video: 3, audio: 4,
  }
  const visibleTracks = tracks
    .slice()
    .sort((left, right) => trackOrder[left.kind] - trackOrder[right.kind])

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

  function seekFromPointer(event: PointerEvent<HTMLDivElement>) {
    const surface = surfaceRef.current
    if (!surface) return
    const rect = surface.getBoundingClientRect()
    const pixelX = event.clientX - rect.left + surface.scrollLeft
    seek(pxToTime(pixelX, durationS, timelineWidthPx, {
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

  const labelIntervalS = rulerLabelInterval(durationS, contentWidth)
  const rulerSeconds = Array.from({ length: Math.floor(durationS) + 1 }, (_, second) => second)
  if (rulerSeconds.at(-1) !== durationS) rulerSeconds.push(durationS)
  const rulerTicks = rulerSeconds.map((second) => {
    const terminal = second === durationS
    const regularMajor = Number.isInteger(second) && second % labelIntervalS === 0
    const terminalGapPx = timeToPx(durationS - second, durationS, timelineWidthPx, timelineZoom)
    const major = terminal || (regularMajor && (
      Number.isInteger(durationS) || second === 0 || terminalGapPx >= MIN_RULER_LABEL_SPACING_PX
    ))
    return {
      second,
      terminal,
      major,
      left: `${timeToPx(second, durationS, timelineWidthPx, timelineZoom)}px`,
      label: major ? formatRulerTime(second) : null,
    }
  })

  return (
    <section className={`timeline-panel${hasMedia ? '' : ' timeline-panel--empty'}`} role="region" aria-label="Timeline">
      <header className="timeline-toolbar" aria-label="Timeline tools">
        {!runtime && <button type="button" aria-label="Add track" disabled={!hasMedia}><Plus aria-hidden size={18} /></button>}
        <button type="button" aria-label="Select tool"><MousePointer2 aria-hidden size={18} /></button>
        <button className={snapEnabled ? 'is-active' : ''} type="button" aria-label="Toggle snap" aria-pressed={snapEnabled} onClick={() => setSnapEnabled(!snapEnabled)}><Magnet aria-hidden size={18} /></button>
        {!runtime && (
          <>
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
          </>
        )}
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
          ref={surfaceRef}
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
                    durationS={durationS}
                    timelineZoom={timelineZoom}
                    timelineWidthPx={timelineWidthPx}
                    presentationInsetPx={presentationInsetPx}
                    selection={selection}
                    select={select}
                  />
                ))}
              </div>
            )) : (
              <div className="timeline-empty-state"><span aria-hidden>▣</span><p>{runtime ? 'No timeline media in this project' : 'Drag media here to start creating'}</p></div>
            )}
            <div
              className="timeline-playhead"
              style={{ left: `${timeToPx(currentTimeS, durationS, timelineWidthPx, timelineZoom)}px` }}
              aria-hidden="true"
            ><span /></div>
          </div>
        </div>
        {hasMedia && <output className="timeline-playhead-time" aria-label="Playhead time">{formatTimelineTime(currentTimeS)}</output>}
      </div>
    </section>
  )
}
