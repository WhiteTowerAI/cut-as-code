import { useEffect, type ReactNode } from 'react'
import {
  ArrowDownToLine,
  ArrowUpToLine,
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

function formatTimecode(timeS: number, fps: number) {
  const safeTimeS = Math.max(0, Number.isFinite(timeS) ? timeS : 0)
  const wholeSeconds = Math.floor(safeTimeS)
  const frames = Math.min(fps - 1, Math.floor((safeTimeS - wholeSeconds) * fps))
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
  { label: 'ALIGNMENT', items: ['Align left', 'Align center', 'Align right'] },
  { label: 'ARRANGE', items: ['Bring to Front', 'Send to Back', 'Lock Media'] },
  { label: 'MEDIA', items: ['Replace Media', 'Reset Transform'] },
] as const

function MoreMenu() {
  return (
    <div className="viewer-menu viewer-more-menu" role="menu" aria-label="More viewer actions">
      {moreMenuSections.map((section) => (
        <section className="viewer-menu-section" key={section.label}>
          <h3>{section.label}</h3>
          {section.label === 'ALIGNMENT' ? (
            <div className="viewer-alignment-row">
              {section.items.map((item, index) => (
                <button type="button" role="menuitem" disabled title={`${item} is not available in project protocol V1.`} key={item} aria-label={item}>
                  {index === 0 ? <ArrowUpToLine aria-hidden size={18} /> : index === 1 ? <ScanLine aria-hidden size={18} /> : <ArrowDownToLine aria-hidden size={18} />}
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
  { ratio: 'Original', note: 'Keep source', shape: 'original', selected: false },
  { ratio: '16:9', note: 'YouTube / landscape', shape: 'wide', selected: false },
  { ratio: '9:16', note: 'TikTok / Reels / Shorts', shape: 'portrait', selected: true },
  { ratio: '1:1', note: 'Instagram / social', shape: 'square', selected: false },
  { ratio: '4:5', note: 'Instagram Feed', shape: 'feed', selected: false },
  { ratio: '4:3', note: 'Standard / presentations', shape: 'classic', selected: false },
] as const

function AspectRatioMenu() {
  return (
    <div className="viewer-menu viewer-aspect-menu" role="menu" aria-label="Aspect ratio">
      {aspectOptions.map((option, index) => (
        <div
          className="viewer-aspect-option"
          data-selected={option.selected || undefined}
          role="menuitemradio"
          aria-checked={option.selected ?? false}
          aria-disabled="true"
          key={option.ratio}
        >
          <span className="viewer-aspect-check">{option.selected && <Check aria-hidden size={16} />}</span>
          <span className="viewer-aspect-copy"><strong>{option.ratio}</strong><small>{option.note}</small></span>
          {index > 0 && <span className={`viewer-ratio-shape viewer-ratio-shape--${option.shape}`} />}
        </div>
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
  const hasMedia = Boolean(project && project.durationS > 0)
  const fps = project ? project.fps.numerator / project.fps.denominator : 30

  useEffect(() => {
    if (!isPlaying || !project?.durationS) return
    let frameId = 0
    let previous = performance.now()
    const tick = (now: number) => {
      const elapsedS = (now - previous) / 1000
      previous = now
      const state = store.getState()
      const nextTimeS = state.currentTimeS + elapsedS
      if (nextTimeS >= project.durationS) {
        state.seek(project.durationS)
        state.setPlaying(false)
        return
      }
      state.seek(nextTimeS)
      frameId = requestAnimationFrame(tick)
    }
    frameId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameId)
  }, [isPlaying, project?.durationS, store])

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpenMenu(null)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [setOpenMenu])

  const selectionKind = selection?.kind === 'caption' ? 'caption' : selection ? 'video' : null
  const toggleMenu = (menu: 'viewer-more' | 'aspect-ratio') => setOpenMenu(openMenu === menu ? null : menu)

  return (
    <section className="viewer-panel" role="region" aria-label="Viewer">
      <header className="viewer-titlebar">Viewer</header>
      <div className="viewer-stage">
        {hasMedia && (
          <>
            <div className="viewer-canvas">
              <img data-preview-media src="/fixtures/viewer-poster.png" alt="Project preview" />
            </div>
            {selectionKind && (
              <>
                <SelectionBounds kind={selectionKind} />
                <SelectionToolbar open={openMenu === 'viewer-more'} onToggle={() => toggleMenu('viewer-more')} />
              </>
            )}
          </>
        )}
      </div>
      <footer className="viewer-playback">
        <div className="viewer-playback-left">
          <output aria-label="Playhead time">
            {formatTimecode(currentTimeS, fps)} / {formatTimecode(project?.durationS ?? 0, fps)}
          </output>
          <button type="button" aria-label="Volume" disabled title="Audio monitoring is not available in project protocol V1."><Volume2 aria-hidden size={22} /></button>
        </div>
        <button
          className="viewer-play-button"
          type="button"
          aria-label={isPlaying ? 'Pause' : 'Play'}
          disabled={!hasMedia}
          onClick={() => setPlaying(!isPlaying)}
        >
          {isPlaying ? <Pause aria-hidden size={20} fill="currentColor" /> : <Play aria-hidden size={20} fill="currentColor" />}
        </button>
        <div className="viewer-playback-right">
          <button type="button" aria-label="Capture frame" disabled title="Frame capture is not available in project protocol V1."><ScanLine aria-hidden size={21} /></button>
          <button type="button" aria-label="Fit preview" onClick={() => seek(currentTimeS)}><Focus aria-hidden size={21} /></button>
          <button
            className="viewer-aspect-trigger"
            type="button"
            aria-label="Aspect ratio"
            aria-haspopup="menu"
            aria-expanded={openMenu === 'aspect-ratio'}
            onClick={() => toggleMenu('aspect-ratio')}
          ><Ratio aria-hidden size={22} /></button>
          <button type="button" aria-label="Fullscreen" disabled title="Fullscreen preview is not available in this fixture."><Maximize2 aria-hidden size={21} /></button>
        </div>
      </footer>
      {openMenu === 'viewer-more' && <MoreMenu />}
      {openMenu === 'aspect-ratio' && <AspectRatioMenu />}
    </section>
  )
}
