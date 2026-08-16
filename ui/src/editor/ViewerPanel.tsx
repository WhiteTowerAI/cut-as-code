import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import {
  ArrowDownToLine,
  ArrowUpToLine,
  AlignHorizontalJustifyCenter,
  AlignHorizontalJustifyEnd,
  AlignHorizontalJustifyStart,
  AlignVerticalJustifyCenter,
  AlignVerticalJustifyEnd,
  AlignVerticalJustifyStart,
  AudioWaveform,
  Check,
  Copy,
  Crop,
  Focus,
  Maximize2,
  MoreHorizontal,
  Pause,
  Play,
  Ratio,
  RotateCw,
  ScanLine,
  Trash2,
  Volume2,
} from 'lucide-react'
import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { EditorState } from './editor-store'
import type { ReviewArtifactView } from './editor-model'
import type { ClipView } from './editor-model'

type ViewerPanelProps = {
  store: StoreApi<EditorState>
}

export function createPlaybackController(video: HTMLVideoElement) {
  return {
    play: () => video.play(),
    pause: () => video.pause(),
    seek: (timeS: number) => { video.currentTime = timeS },
    getTime: () => video.currentTime,
    getDuration: () => video.duration,
    isPlaying: () => !video.paused,
  }
}

export function programTimeToSourceTime(programTimeS: number, clips: readonly ClipView[]) {
  const clip = clips.find((candidate) =>
    programTimeS >= candidate.programRange.startS && programTimeS < candidate.programRange.endS,
  ) ?? clips.at(-1)
  if (!clip) return null
  const programDuration = clip.programRange.endS - clip.programRange.startS
  const sourceDuration = clip.sourceRange.endS - clip.sourceRange.startS
  if (programDuration <= 0 || sourceDuration <= 0) return null
  const offset = Math.min(Math.max(programTimeS - clip.programRange.startS, 0), programDuration)
  return clip.sourceRange.startS + offset * sourceDuration / programDuration
}

export function sourceTimeToProgramTime(sourceTimeS: number, clips: readonly ClipView[]) {
  const clip = clips.find((candidate) =>
    sourceTimeS >= candidate.sourceRange.startS && sourceTimeS < candidate.sourceRange.endS,
  )
  if (!clip) return null
  return sourceTimeToProgramTimeInClip(sourceTimeS, clip)
}

function sourceTimeToProgramTimeInClip(sourceTimeS: number, clip: ClipView) {
  const programDuration = clip.programRange.endS - clip.programRange.startS
  const sourceDuration = clip.sourceRange.endS - clip.sourceRange.startS
  if (programDuration <= 0 || sourceDuration <= 0) return null
  return clip.programRange.startS + (sourceTimeS - clip.sourceRange.startS) * programDuration / sourceDuration
}

function programClipAtTime(programTimeS: number, clips: readonly ClipView[]) {
  return clips.find((clip) =>
    programTimeS >= clip.programRange.startS && programTimeS < clip.programRange.endS,
  ) ?? clips.at(-1)
}

function sourceClipAtTime(sourceTimeS: number, clips: readonly ClipView[]) {
  return clips.find((clip) =>
    sourceTimeS >= clip.sourceRange.startS && sourceTimeS < clip.sourceRange.endS,
  )
}

function nextClipInProgramOrder(activeClip: ClipView, clips: readonly ClipView[]) {
  const activeIndex = clips.findIndex((clip) => clip.id === activeClip.id)
  return activeIndex >= 0 ? clips[activeIndex + 1] : undefined
}

function playbackRateForClip(clip: ClipView) {
  const sourceDuration = clip.sourceRange.endS - clip.sourceRange.startS
  const programDuration = clip.programRange.endS - clip.programRange.startS
  return sourceDuration > 0 && programDuration > 0 ? sourceDuration / programDuration : null
}

function supportsNativePlaybackRate(playbackRate: number) {
  const probe = document.createElement('video')
  try {
    probe.playbackRate = playbackRate
    return Math.abs(probe.playbackRate - playbackRate) <= 0.001
  } catch {
    return false
  }
}

function applyClipPlaybackRate(video: HTMLVideoElement, clip: ClipView) {
  const playbackRate = playbackRateForClip(clip)
  if (playbackRate !== null && Math.abs(video.playbackRate - playbackRate) > 0.001) {
    try {
      video.playbackRate = playbackRate
    } catch {
      return false
    }
  }
  return playbackRate !== null
}

export function lastPresentedSourceTime(clip: ClipView, sourceFrameDurationS: number) {
  return Math.max(clip.sourceRange.startS, clip.sourceRange.endS - sourceFrameDurationS)
}

export function nativeBoundaryDelayMs(
  currentSourceTimeS: number,
  clip: ClipView,
  sourceFrameDurationS: number,
  playbackRate: number,
) {
  const remainingSourceTimeS = Math.max(
    0,
    clip.sourceRange.endS - currentSourceTimeS,
  )
  return remainingSourceTimeS / Math.max(playbackRate, Number.EPSILON) * 1000
}

export type NativeBoundaryWakeupDecision =
  | { action: 'reschedule'; delayMs: number }
  | { action: 'boundary'; sourceTimeS: number }

export function nativeBoundaryWakeup(
  currentSourceTimeS: number,
  clip: ClipView,
  sourceFrameDurationS: number,
  playbackRate: number,
): NativeBoundaryWakeupDecision {
  if (currentSourceTimeS < clip.sourceRange.endS) {
    return {
      action: 'reschedule',
      delayMs: nativeBoundaryDelayMs(currentSourceTimeS, clip, sourceFrameDurationS, playbackRate),
    }
  }
  return {
    action: 'boundary',
    sourceTimeS: currentSourceTimeS,
  }
}

type FrameDrivenVideo = HTMLVideoElement & {
  requestVideoFrameCallback?: (callback: (now: number, metadata: VideoFrameCallbackMetadata) => void) => number
  cancelVideoFrameCallback?: (handle: number) => void
}

type FinalFrameState = {
  sourceTimeS: number
}

function formatTimecode(timeS: number, fps: number) {
  const safeTimeS = Math.max(0, Number.isFinite(timeS) ? timeS : 0)
  const wholeSeconds = Math.floor(safeTimeS)
  const frames = Math.min(Math.ceil(fps) - 1, Math.floor((safeTimeS - wholeSeconds) * fps))
  const hours = Math.floor(wholeSeconds / 3600)
  const minutes = Math.floor((wholeSeconds % 3600) / 60)
  const seconds = wholeSeconds % 60
  return [hours, minutes, seconds, frames].map((value) => String(value).padStart(2, '0')).join(':')
}

function DisabledCommand({
  name,
  descriptionId,
  children,
  menu = false,
}: {
  name: string
  descriptionId: string
  children: ReactNode
  menu?: boolean
}) {
  const description = `${name} is not available in project protocol V1.`
  return (
    <span
      className={menu ? 'viewer-menu-disabled-control' : 'viewer-disabled-control'}
      title={description}
      style={menu ? { display: 'block', width: '200px', minHeight: '36px' } : undefined}
    >
      <button
        type="button"
        role={menu ? 'menuitem' : undefined}
        disabled
        aria-label={name}
        aria-describedby={descriptionId}
        style={menu ? {
          display: 'flex',
          alignItems: 'center',
          width: '200px',
          minHeight: '36px',
          padding: '0 10px',
          border: 0,
          color: '#e8ebf0',
          background: 'transparent',
          fontSize: '13px',
          textAlign: 'left',
          cursor: 'not-allowed',
          opacity: 1,
        } : undefined}
      >
        {children}
      </button>
      <span className="sr-only" id={descriptionId}>{description}</span>
    </span>
  )
}

const toolbarCommands = [
  { name: 'Crop', id: 'viewer-crop-description', icon: Crop },
  { name: 'Rotate', id: 'viewer-rotate-description', icon: RotateCw },
  { name: 'Duplicate', id: 'viewer-duplicate-description', icon: Copy },
  { name: 'Delete', id: 'viewer-delete-description', icon: Trash2 },
  { name: 'Bring forward', id: 'viewer-bring-forward-description', icon: ArrowUpToLine },
  { name: 'Send backward', id: 'viewer-send-backward-description', icon: ArrowDownToLine },
] as const

function SelectionToolbar({
  open,
  onToggle,
}: {
  open: boolean
  onToggle: () => void
}) {
  return (
    <div className="viewer-selection-toolbar" aria-label="Selection actions">
      <DisabledCommand name="Crop" descriptionId="viewer-crop-description"><Crop aria-hidden size={20} /></DisabledCommand>
      <DisabledCommand name="Audio" descriptionId="viewer-audio-description"><AudioWaveform aria-hidden size={20} /></DisabledCommand>
      {toolbarCommands.slice(1).map(({ name, id, icon: Icon }) => (
        <DisabledCommand key={name} name={name} descriptionId={id}><Icon aria-hidden size={20} /></DisabledCommand>
      ))}
      <button
        className="viewer-toolbar-more"
        type="button"
        aria-label="More viewer actions"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={onToggle}
      >
        <MoreHorizontal aria-hidden size={20} />
      </button>
    </div>
  )
}

const moreMenuSections = [
  { label: 'TRANSFORM', items: ['Flip Horizontal', 'Flip Vertical', 'Opacity'] },
  { label: 'ALIGNMENT', items: ['Align left', 'Align center', 'Align right', 'Align top', 'Align middle', 'Align bottom'] },
  { label: 'ARRANGE', items: ['Bring to Front', 'Send to Back', 'Lock Media'] },
  { label: 'MEDIA', items: ['Replace Media', 'Reset Transform'] },
] as const

function MoreMenu() {
  const alignmentIcons = [
    AlignHorizontalJustifyStart,
    AlignHorizontalJustifyCenter,
    AlignHorizontalJustifyEnd,
    AlignVerticalJustifyStart,
    AlignVerticalJustifyCenter,
    AlignVerticalJustifyEnd,
  ]
  return (
    <div className="viewer-menu viewer-more-menu" role="menu" aria-label="More viewer actions">
      {moreMenuSections.map((section) => (
        <section className="viewer-menu-section" key={section.label}>
          <h3>{section.label}</h3>
          {section.label === 'ALIGNMENT' ? (
            <div className="viewer-alignment-row">
              {section.items.map((item, index) => (
                <button type="button" role="menuitem" disabled title={`${item} is not available in project protocol V1.`} key={item} aria-label={item}>
                  {(() => {
                    const Icon = alignmentIcons[index]
                    return <Icon aria-hidden size={18} />
                  })()}
                </button>
              ))}
            </div>
          ) : section.label === 'ARRANGE' ? section.items.map((item) => (
            <DisabledCommand
              key={item}
              name={item}
              descriptionId={`viewer-${item.toLowerCase().replaceAll(' ', '-')}-description`}
              menu
            >
              {item}
            </DisabledCommand>
          )) : section.items.map((item) => (
            <button type="button" role="menuitem" disabled title={`${item} is not available in project protocol V1.`} key={item}>
              {item}
              {item === 'Opacity' && <span className="viewer-opacity-track"><span /></span>}
            </button>
          ))}
        </section>
      ))}
    </div>
  )
}

const aspectOptions = [
  { ratio: 'Original', note: 'Keep source', shape: 'original' },
  { ratio: '16:9', note: 'YouTube / landscape', shape: 'wide' },
  { ratio: '9:16', note: 'TikTok / Reels / Shorts', shape: 'portrait' },
  { ratio: '1:1', note: 'Instagram / social', shape: 'square' },
  { ratio: '4:5', note: 'Instagram Feed', shape: 'feed' },
  { ratio: '4:3', note: 'Standard / presentations', shape: 'classic' },
] as const

function displayAspectRatio(width?: number, height?: number) {
  if (!width || !height) return 'Original'
  const ratio = width / height
  const candidates = [
    ['16:9', 16 / 9],
    ['9:16', 9 / 16],
    ['1:1', 1],
    ['4:5', 4 / 5],
    ['4:3', 4 / 3],
  ] as const
  return candidates.find(([, value]) => Math.abs(ratio - value) < 0.01)?.[0] ?? 'Original'
}

function AspectRatioMenu({ width, height, readOnly }: { width?: number; height?: number; readOnly?: boolean }) {
  const selectedRatio = displayAspectRatio(width, height)
  return (
    <div className="viewer-menu viewer-aspect-menu" role="menu" aria-label="Aspect ratio">
      {aspectOptions.map((option, index) => (
        <button
          className="viewer-aspect-option"
          data-selected={option.ratio === selectedRatio || undefined}
          role="menuitemradio"
          aria-checked={option.ratio === selectedRatio}
          type="button"
          disabled={readOnly}
          key={option.ratio}
        >
          <span className="viewer-aspect-check">{option.ratio === selectedRatio && <Check aria-hidden size={16} />}</span>
          <span className="viewer-aspect-copy"><strong>{option.ratio}</strong><small>{option.note}</small></span>
          {index > 0 && <span className={`viewer-ratio-shape viewer-ratio-shape--${option.shape}`} />}
        </button>
      ))}
    </div>
  )
}

function SelectionBounds({ kind }: { kind: 'video' | 'caption' }) {
  return (
    <div className={`viewer-selection-bounds viewer-selection-bounds--${kind}`} aria-hidden="true">
      {kind === 'caption' && <span>but technology shouldn't<br />take you away from the world</span>}
      {['tl', 'tc', 'tr', 'ml', 'mr', 'bl', 'bc', 'br'].map((position) => (
        <i className={`viewer-handle viewer-handle--${position}`} key={position} />
      ))}
    </div>
  )
}

export function ViewerPanel({ store }: ViewerPanelProps) {
  const project = useStore(store, (state) => state.project)
  const selection = useStore(store, (state) => state.selection)
  const currentTimeS = useStore(store, (state) => state.currentTimeS)
  const isPlaying = useStore(store, (state) => state.isPlaying)
  const openMenu = useStore(store, (state) => state.openMenu)
  const seek = useStore(store, (state) => state.seek)
  const setPlaying = useStore(store, (state) => state.setPlaying)
  const setOpenMenu = useStore(store, (state) => state.setOpenMenu)
  const contentCardsOperation = useStore(store, (state) => state.project?.operations?.find((operation) => operation.kind === 'content-cards'))
  const operations = useStore(store, (state) => state.project?.operations)
  const currentArtifacts = operations?.flatMap((operation) => operation.preview?.artifacts ?? []) ?? []
  const primaryArtifact = currentArtifacts.find((artifact) => artifact.mediaType.startsWith('image/'))
    ?? currentArtifacts.find((artifact) => artifact.mediaType.startsWith('video/'))
  const projectVideo = project?.sourceAssetId
    ? project.assets.find((asset) => asset.id === project.sourceAssetId && asset.kind === 'video' && asset.mediaType?.startsWith('video/') && asset.url)
    : undefined
  const videoClips = project?.tracks.find((track) => track.kind === 'video')?.clips ?? []
  const projectVideoRef = useRef<HTMLVideoElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)
  const [fitSize, setFitSize] = useState<Readonly<{ width: number; height: number }>>()
  const finalFrameStateRef = useRef<FinalFrameState | null>(null)
  const nativeProgramTimeRef = useRef<number | null>(null)
  const activeClipRef = useRef<ClipView | null>(null)
  const holdingBoundaryRef = useRef(false)
  const cancelBoundaryHoldRef = useRef<(() => boolean) | null>(null)
  const unsupportedPlaybackRate = videoClips
    .map(playbackRateForClip)
    .find((playbackRate) => playbackRate !== null && !supportsNativePlaybackRate(playbackRate))
  const canPlay = Boolean(projectVideo && !primaryArtifact && videoClips.length && unsupportedPlaybackRate === undefined)
  const hasTimeline = Boolean(project && project.durationS > 0)
  const runtime = Boolean(project?.runtime)
  const fps = project ? project.fps.numerator / project.fps.denominator : 30
  const sourceFrameDurationS = project && project.fps.numerator > 0
    ? project.fps.denominator / project.fps.numerator
    : 1 / 30
  const sequenceGeometry = project?.sequenceGeometry

  const fitPreview = useCallback(() => {
    const stage = stageRef.current
    if (!stage || !sequenceGeometry) return
    const availableWidth = Math.max(1, stage.clientWidth - 48)
    const availableHeight = Math.max(1, stage.clientHeight - 48)
    const scale = Math.min(
      availableWidth / sequenceGeometry.width,
      availableHeight / sequenceGeometry.height,
    )
    setFitSize({
      width: Math.max(1, Math.floor(sequenceGeometry.width * scale)),
      height: Math.max(1, Math.floor(sequenceGeometry.height * scale)),
    })
  }, [sequenceGeometry])

  useEffect(() => {
    fitPreview()
    const stage = stageRef.current
    if (!stage || !sequenceGeometry || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(fitPreview)
    observer.observe(stage)
    return () => observer.disconnect()
  }, [fitPreview, sequenceGeometry])

  function enterFullscreen() {
    const stage = stageRef.current
    if (!stage?.requestFullscreen) return
    void stage.requestFullscreen().then(fitPreview).catch(() => undefined)
  }

  function retireBoundaryHold() {
    const retired = cancelBoundaryHoldRef.current?.() ?? false
    if (retired) setPlaying(false)
    return retired
  }

  function seekProjectVideo(programTimeS: number) {
    retireBoundaryHold()
    const video = projectVideoRef.current
    const finalClip = videoClips.at(-1)
    if (video && project && finalClip && programTimeS >= project.durationS - 0.0001) {
      const finalSourceTimeS = lastPresentedSourceTime(finalClip, sourceFrameDurationS)
      activeClipRef.current = finalClip
      finalFrameStateRef.current = { sourceTimeS: finalSourceTimeS }
      applyClipPlaybackRate(video, finalClip)
      if (Math.abs(video.currentTime - finalSourceTimeS) >= 0.0001) {
        createPlaybackController(video).seek(finalSourceTimeS)
      }
      return
    }
    finalFrameStateRef.current = null
    const clip = programClipAtTime(programTimeS, videoClips)
    const sourceTimeS = programTimeToSourceTime(programTimeS, videoClips)
    if (!video || !clip || sourceTimeS === null) return
    activeClipRef.current = clip
    applyClipPlaybackRate(video, clip)
    if (Math.abs(video.currentTime - sourceTimeS) < 0.01) return
    createPlaybackController(video).seek(sourceTimeS)
  }

  function publishNativeProgramTime(programTimeS: number) {
    nativeProgramTimeRef.current = programTimeS
    seek(programTimeS)
  }

  useEffect(() => {
    if (nativeProgramTimeRef.current !== null && Math.abs(currentTimeS - nativeProgramTimeRef.current) < 0.0001) {
      nativeProgramTimeRef.current = null
      return
    }
    seekProjectVideo(currentTimeS)
  }, [currentTimeS, projectVideo?.url, videoClips])

  function syncProgramTime(video: HTMLVideoElement) {
    const finalFrameState = finalFrameStateRef.current
    if (finalFrameState) {
      if (Math.abs(video.currentTime - finalFrameState.sourceTimeS) >= 0.01) {
        createPlaybackController(video).seek(finalFrameState.sourceTimeS)
      }
      return
    }
    const activeClip = activeClipRef.current ?? sourceClipAtTime(video.currentTime, videoClips)
    if (!activeClip || video.currentTime < activeClip.sourceRange.startS || video.currentTime >= activeClip.sourceRange.endS) return
    applyClipPlaybackRate(video, activeClip)
    const programTimeS = sourceTimeToProgramTimeInClip(video.currentTime, activeClip)
    if (programTimeS !== null) publishNativeProgramTime(programTimeS)
  }

  function transitionToNextClip(video: HTMLVideoElement, nextClip: ClipView) {
    finalFrameStateRef.current = null
    activeClipRef.current = nextClip
    applyClipPlaybackRate(video, nextClip)
    createPlaybackController(video).seek(nextClip.sourceRange.startS)
    publishNativeProgramTime(nextClip.programRange.startS)
  }

  function finishPlayingClip(video: HTMLVideoElement, clip: ClipView) {
    const finalSourceTimeS = lastPresentedSourceTime(clip, sourceFrameDurationS)
    const finalProgramTimeS = project?.durationS ?? clip.programRange.endS
    finalFrameStateRef.current = { sourceTimeS: finalSourceTimeS }
    activeClipRef.current = clip
    const playback = createPlaybackController(video)
    playback.seek(finalSourceTimeS)
    playback.pause()
    publishNativeProgramTime(finalProgramTimeS)
    setPlaying(false)
  }

  function syncPresentedFrame(video: HTMLVideoElement, presentedSourceTimeS: number) {
    const activeClip = activeClipRef.current ?? sourceClipAtTime(presentedSourceTimeS, videoClips)
    if (!activeClip) {
      const nextClip = videoClips.find((clip) => presentedSourceTimeS < clip.sourceRange.startS)
      if (nextClip) transitionToNextClip(video, nextClip)
      else if (videoClips.at(-1)) finishPlayingClip(video, videoClips.at(-1)!)
      return true
    }
    const nextClip = nextClipInProgramOrder(activeClip, videoClips)
    if (presentedSourceTimeS >= activeClip.sourceRange.endS) {
      if (nextClip) transitionToNextClip(video, nextClip)
      else finishPlayingClip(video, activeClip)
      return true
    }
    applyClipPlaybackRate(video, activeClip)
    const programTimeS = sourceTimeToProgramTimeInClip(presentedSourceTimeS, activeClip)
    if (programTimeS !== null) publishNativeProgramTime(programTimeS)
    return presentedSourceTimeS >= lastPresentedSourceTime(activeClip, sourceFrameDurationS) - sourceFrameDurationS / 100
      ? 'hold'
      : false
  }

  useEffect(() => {
    const video = projectVideoRef.current
    if (!video || !canPlay) return
    const frameVideo = video as FrameDrivenVideo
    let cancelScheduledFrame: (() => void) | null = null
    let cancelBoundaryTimer: (() => void) | null = null
    let cancelBoundaryHold: (() => void) | null = null
    let boundaryHoldId = 0
    let disposed = false

    const stopBoundaryHold = () => {
      const canceled = cancelBoundaryHold !== null
      boundaryHoldId += 1
      cancelBoundaryHold?.()
      cancelBoundaryHold = null
      holdingBoundaryRef.current = false
      return canceled
    }
    cancelBoundaryHoldRef.current = stopBoundaryHold

    const schedulePresentedFrame = () => {
      if (disposed || video.paused || cancelScheduledFrame) return
      const tick = (presentedSourceTimeS: number) => {
        cancelScheduledFrame = null
        if (disposed || video.paused) return
        const result = syncPresentedFrame(video, presentedSourceTimeS)
        if (result === 'hold') {
          const playbackRate = Math.max(video.playbackRate, Number.EPSILON)
          stopBoundaryCheck()
          const heldClip = activeClipRef.current
          const holdId = ++boundaryHoldId
          holdingBoundaryRef.current = true
          video.pause()
          const handle = window.setTimeout(() => {
            if (disposed || holdId !== boundaryHoldId || activeClipRef.current?.id !== heldClip?.id) {
              if (holdId === boundaryHoldId) stopBoundaryHold()
              return
            }
            cancelBoundaryHold = null
            holdingBoundaryRef.current = false
            const nextClip = heldClip ? nextClipInProgramOrder(heldClip, videoClips) : undefined
            if (heldClip && nextClip) {
              transitionToNextClip(video, nextClip)
              void video.play().catch(() => setPlaying(false))
            } else if (heldClip) {
              finishPlayingClip(video, heldClip)
            }
          }, sourceFrameDurationS / playbackRate * 1000)
          cancelBoundaryHold = () => window.clearTimeout(handle)
          return
        }
        if (result) restartBoundaryTimer()
        schedulePresentedFrame()
      }
      if (frameVideo.requestVideoFrameCallback) {
        const handle = frameVideo.requestVideoFrameCallback((_now, metadata) => tick(metadata.mediaTime))
        cancelScheduledFrame = () => frameVideo.cancelVideoFrameCallback?.(handle)
      }
    }

    const scheduleBoundaryTimer = () => {
      if (disposed || video.paused || cancelBoundaryTimer) return
      const scheduledSourceTimeS = video.currentTime
      const activeClip = activeClipRef.current ?? sourceClipAtTime(scheduledSourceTimeS, videoClips)
      const scheduledDecision = activeClip
        ? nativeBoundaryWakeup(scheduledSourceTimeS, activeClip, sourceFrameDurationS, video.playbackRate)
        : { action: 'boundary', sourceTimeS: scheduledSourceTimeS } as const
      const handle = window.setTimeout(() => {
        cancelBoundaryTimer = null
        if (disposed || video.paused) return
        const decision = activeClip
          ? nativeBoundaryWakeup(video.currentTime, activeClip, sourceFrameDurationS, video.playbackRate)
          : { action: 'boundary', sourceTimeS: video.currentTime } as const
        if (decision.action === 'reschedule') {
          syncProgramTime(video)
          scheduleBoundaryTimer()
          return
        }
        syncPresentedFrame(video, decision.sourceTimeS)
        scheduleBoundaryTimer()
      }, scheduledDecision.action === 'reschedule' ? scheduledDecision.delayMs : 0)
      cancelBoundaryTimer = () => window.clearTimeout(handle)
    }

    const stopBoundaryCheck = () => {
      cancelScheduledFrame?.()
      cancelScheduledFrame = null
      cancelBoundaryTimer?.()
      cancelBoundaryTimer = null
    }

    const handlePause = () => {
      if (holdingBoundaryRef.current) return
      stopBoundaryHold()
      stopBoundaryCheck()
    }

    const restartBoundaryTimer = () => {
      cancelBoundaryTimer?.()
      cancelBoundaryTimer = null
      scheduleBoundaryTimer()
    }

    const startBoundaryCheck = () => {
      stopBoundaryHold()
      if (!frameVideo.requestVideoFrameCallback && document.hidden) {
        video.pause()
        return
      }
      schedulePresentedFrame()
      scheduleBoundaryTimer()
    }

    const restartBoundaryCheck = () => {
      if (stopBoundaryHold()) setPlaying(false)
      stopBoundaryCheck()
      startBoundaryCheck()
    }

    const pauseFallbackWhenHidden = () => {
      if (!frameVideo.requestVideoFrameCallback && document.hidden && !video.paused) video.pause()
    }

    video.addEventListener('play', startBoundaryCheck)
    video.addEventListener('pause', handlePause)
    video.addEventListener('seeked', restartBoundaryCheck)
    document.addEventListener('visibilitychange', pauseFallbackWhenHidden)
    if (!video.paused) startBoundaryCheck()
    return () => {
      disposed = true
      video.removeEventListener('play', startBoundaryCheck)
      video.removeEventListener('pause', handlePause)
      video.removeEventListener('seeked', restartBoundaryCheck)
      document.removeEventListener('visibilitychange', pauseFallbackWhenHidden)
      stopBoundaryCheck()
      if (stopBoundaryHold()) setPlaying(false)
      if (cancelBoundaryHoldRef.current === stopBoundaryHold) cancelBoundaryHoldRef.current = null
    }
  }, [canPlay, projectVideo?.url, project?.durationS, sourceFrameDurationS, videoClips])

  function togglePlayback() {
    const video = projectVideoRef.current
    if (!video) return
    const playback = createPlaybackController(video)
    if (isPlaying) {
      retireBoundaryHold()
      setPlaying(false)
      playback.pause()
      return
    }
    const restartFromBeginning = Boolean(project && currentTimeS >= project.durationS - 0.0001)
    if (restartFromBeginning) {
      finalFrameStateRef.current = null
      seek(0)
      seekProjectVideo(0)
    } else {
      seekProjectVideo(currentTimeS)
    }
    void playback.play().catch(() => setPlaying(false))
  }

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpenMenu(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [setOpenMenu])

  const selectionKind = runtime ? null : selection?.kind === 'caption' ? 'caption' : selection ? 'video' : null
  const toggleMenu = (menu: 'viewer-more' | 'aspect-ratio') => setOpenMenu(openMenu === menu ? null : menu)

  return (
    <section className="viewer-panel" role="region" aria-label="Viewer">
      <header className="viewer-titlebar">Viewer</header>
      {contentCardsOperation?.preview ? (
        <output aria-label="Preview artifact metadata" style={{ display: 'block', padding: '4px 12px', color: '#a9adb9', background: '#17191e', fontSize: 11 }}>
          Existing preview artifact: {contentCardsOperation.preview.status} (revision {contentCardsOperation.preview.revision})
        </output>
      ) : null}
      <div className="viewer-stage" ref={stageRef}>
        {hasTimeline ? (
          <>
            <div
              className={sequenceGeometry ? 'viewer-canvas viewer-canvas--fitted' : 'viewer-canvas'}
              data-sequence-width={sequenceGeometry?.width}
              data-sequence-height={sequenceGeometry?.height}
              data-fit-mode={sequenceGeometry ? 'fit' : undefined}
              style={fitSize ? { width: fitSize.width, height: fitSize.height } : undefined}
            >
              {primaryArtifact?.mediaType.startsWith('video/') ? (
                <video data-preview-media src={primaryArtifact.url} controls aria-label={primaryArtifact.name} />
              ) : primaryArtifact?.mediaType.startsWith('image/') ? (
                <img data-preview-media src={primaryArtifact.url} alt={primaryArtifact.name} />
              ) : projectVideo ? (
                <video
                  ref={projectVideoRef}
                  data-project-media
                  src={projectVideo.url}
                  aria-label={projectVideo.name}
                  onLoadedMetadata={(event) => seekProjectVideo(currentTimeS)}
                  onTimeUpdate={(event) => syncProgramTime(event.currentTarget)}
                  onSeeked={(event) => syncProgramTime(event.currentTarget)}
                  onPlay={() => setPlaying(true)}
                  onPause={() => {
                    if (!holdingBoundaryRef.current) setPlaying(false)
                  }}
                  onEnded={(event) => {
                    const finalClip = videoClips.at(-1)
                    if (finalClip) finishPlayingClip(event.currentTarget, finalClip)
                    else { seek(project?.durationS ?? 0); setPlaying(false) }
                  }}
                />
              ) : (
                <div className="viewer-empty-state" role="status">Project video unavailable</div>
              )}
            </div>
            {selectionKind && (
              <>
                <SelectionBounds kind={selectionKind} />
                <SelectionToolbar open={openMenu === 'viewer-more'} onToggle={() => toggleMenu('viewer-more')} />
              </>
            )}
          </>
        ) : <div className="viewer-empty-state" role="status">Project video unavailable</div>}
      </div>
      {currentArtifacts.length ? <ArtifactGallery artifacts={currentArtifacts} /> : null}
      <footer className="viewer-playback">
        <div className="viewer-playback-left">
          <output aria-label="Playhead time">
            {formatTimecode(currentTimeS, fps)} / {formatTimecode(project?.durationS ?? 0, fps)}
          </output>
          {!runtime && <button type="button" aria-label="Volume" disabled title="Audio monitoring is not available in project protocol V1."><Volume2 aria-hidden size={22} /></button>}
        </div>
        <button
          className="viewer-play-button"
          type="button"
          aria-label={isPlaying ? 'Pause' : 'Play'}
          disabled={!canPlay}
          title={unsupportedPlaybackRate === undefined
            ? undefined
            : `Playback rate ${unsupportedPlaybackRate} cannot be represented by this browser. Use timeline seeking for manual review.`}
          onClick={togglePlayback}
        >
          {isPlaying ? <Pause aria-hidden size={20} fill="currentColor" /> : <Play aria-hidden size={20} fill="currentColor" />}
        </button>
        <div className="viewer-playback-right">
          {!runtime && <button type="button" aria-label="Capture frame" disabled title="Frame capture is not available in project protocol V1."><ScanLine aria-hidden size={21} /></button>}
          <button type="button" aria-label="Fit preview" onClick={fitPreview} disabled={!sequenceGeometry}><Focus aria-hidden size={21} /></button>
          <button
            className="viewer-aspect-trigger"
            type="button"
            aria-label="Aspect ratio"
            aria-haspopup="menu"
            aria-expanded={openMenu === 'aspect-ratio'}
            onClick={() => toggleMenu('aspect-ratio')}
          ><Ratio aria-hidden size={22} /></button>
          <button type="button" aria-label="Fullscreen" onClick={enterFullscreen} disabled={!hasTimeline}><Maximize2 aria-hidden size={21} /></button>
        </div>
      </footer>
      {openMenu === 'viewer-more' && <MoreMenu />}
      {openMenu === 'aspect-ratio' && (
        <AspectRatioMenu
          width={sequenceGeometry?.width}
          height={sequenceGeometry?.height}
          readOnly={Boolean(sequenceGeometry)}
        />
      )}
    </section>
  )
}

function ArtifactGallery({ artifacts }: { artifacts: readonly ReviewArtifactView[] }) {
  return (
    <section role="region" aria-label="Current review artifacts" style={{ display: 'flex', gap: 8, padding: 8, overflowX: 'auto', background: '#17191e' }}>
      {artifacts.map((artifact) => (
        <figure key={artifact.id} data-artifact-url={artifact.url} style={{ flex: '0 0 180px', margin: 0 }}>
          {artifact.mediaType.startsWith('image/') ? (
            <img src={artifact.url} alt={artifact.name} style={{ width: '100%', height: 100, objectFit: 'contain' }} />
          ) : artifact.mediaType.startsWith('video/') ? (
            <video src={artifact.url} controls aria-label={artifact.name} style={{ width: '100%', height: 100 }} />
          ) : artifact.mediaType.startsWith('text/html') ? (
            <iframe src={artifact.url} title={artifact.name} sandbox="" style={{ width: '100%', height: 100, border: 0, background: '#fff' }} />
          ) : (
            <a href={artifact.url} target="_blank" rel="noreferrer">{artifact.name}</a>
          )}
          <figcaption style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11 }}>{artifact.name}</figcaption>
        </figure>
      ))}
    </section>
  )
}
