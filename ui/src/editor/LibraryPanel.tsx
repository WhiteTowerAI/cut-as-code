import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type KeyboardEvent, type ReactNode } from 'react'
import { Plus, Search, Upload } from 'lucide-react'
import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { AssetView, EditorOperationView, EditorSelection, LibraryTab } from './editor-model'
import { draftFieldsForCue, type EditorState } from './editor-store'

type LibraryPanelProps = {
  store: StoreApi<EditorState>
  importAssets?: (files: readonly File[]) => Promise<void>
}

type TileItem = {
  id: string
  label: string
  preview: 'asset' | 'product' | 'founder' | 'brand' | 'city' | 'runtime'
  image?: string
  previewText?: string
  duration?: string
  status?: string
  accent?: 'teal' | 'cyan' | 'yellow' | 'green' | 'pink'
  mediaUrl?: string
  mediaType?: string
}

const tabs: ReadonlyArray<{ id: LibraryTab; label: string }> = [
  { id: 'assets', label: 'My Assets' },
]

// Captions, Cards, and Graphic Motion panels remain implemented below for a future restore.

function tileForAsset(asset: AssetView, runtime = false): TileItem {
  if (runtime) {
    return {
      id: asset.id,
      label: asset.name,
      preview: 'asset',
      mediaUrl: asset.url,
      mediaType: asset.mediaType,
      duration: asset.durationS === undefined ? undefined : `${asset.durationS.toFixed(1)}s`,
    }
  }
  return { id: asset.id, label: asset.name, preview: 'asset' }
}

const captionStyles: readonly TileItem[] = [
  { id: 'caption-clean', label: 'Clean', preview: 'product', image: '/assets/editor/caption-clean.png', previewText: 'Caption', status: 'Added' },
  { id: 'caption-minimal', label: 'Minimal', preview: 'founder', image: '/assets/editor/caption-minimal.png', previewText: 'Caption' },
  { id: 'caption-social', label: 'Social bold', preview: 'brand', image: '/assets/editor/caption-social-bold.png', previewText: 'STAY CURIOUS' },
  { id: 'caption-pill', label: 'Pill', preview: 'city', image: '/assets/editor/caption-pill.png', previewText: 'Caption' },
  { id: 'caption-boxed', label: 'Boxed', preview: 'product', image: '/assets/editor/caption-boxed.png', previewText: 'Caption' },
  { id: 'caption-stroked', label: 'Stroked', preview: 'founder', image: '/assets/editor/caption-stroked.png', previewText: 'Caption' },
  { id: 'caption-shorts', label: 'Shorts', preview: 'brand', image: '/assets/editor/caption-shorts.png', previewText: 'keep creating' },
]

const contentCards: readonly TileItem[] = [
  { id: 'card-lower-third', label: 'Lower third', preview: 'product', image: '/assets/editor/card-lower-third.png', previewText: 'Presenter', duration: '00:18', status: 'Added', accent: 'teal' },
  { id: 'card-quote', label: 'Quote', preview: 'founder', image: '/assets/editor/card-quote.png', previewText: 'Pull quote', duration: '18:42', accent: 'cyan' },
  { id: 'card-stat', label: 'Stat', preview: 'brand', image: '/assets/editor/card-stat.png', previewText: '72%', duration: '00:08', accent: 'yellow' },
  { id: 'card-split', label: 'Split', preview: 'city', image: '/assets/editor/card-split.png', previewText: 'Before / after', duration: '00:05', accent: 'green' },
  { id: 'card-cta', label: 'CTA', preview: 'product', image: '/assets/editor/card-cta.png', previewText: 'Try it now', duration: '00:18', status: 'Added', accent: 'pink' },
  { id: 'card-product', label: 'Product', preview: 'founder', image: '/assets/editor/card-product.png', previewText: 'Feature callout', duration: '18:42', accent: 'teal' },
]

const motionRecipes: readonly TileItem[] = [
  { id: 'xyz-fade-up', label: 'XYZ Fade Up', preview: 'product', previewText: 'Fade up', accent: 'teal' },
  { id: 'xyz-fade-left', label: 'XYZ Fade Left', preview: 'founder', previewText: 'Fade left', accent: 'cyan' },
  { id: 'xyz-fade-big', label: 'XYZ Fade Big', preview: 'brand', previewText: 'Fade big', accent: 'yellow' },
  { id: 'xyz-fade-small', label: 'XYZ Fade Small', preview: 'city', previewText: 'Fade small', accent: 'green' },
]

function SearchField({
  placeholder,
  compact = false,
  value,
  onChange,
}: {
  placeholder: string
  compact?: boolean
  value?: string
  onChange?: (value: string) => void
}) {
  return (
    <label className={compact ? 'library-search library-search--compact' : 'library-search'}>
      <Search className="library-control-icon" aria-hidden="true" />
      <input
        aria-label={placeholder}
        placeholder={placeholder}
        {...(value === undefined ? {} : { value })}
        onChange={onChange ? (event) => onChange(event.currentTarget.value) : undefined}
      />
    </label>
  )
}

function AssetControls({
  onImport,
  disabled,
  query,
  onQueryChange,
}: {
  onImport?: (files: readonly File[]) => void
  disabled?: boolean
  query: string
  onQueryChange: (value: string) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  return (
    <div className="library-controls" role="search">
      <SearchField placeholder="Search assets" compact value={query} onChange={onQueryChange} />
      <input ref={inputRef} className="asset-file-input" type="file" accept="video/mp4,video/quicktime,video/webm,audio/mpeg,audio/wav,image/jpeg,image/png,image/webp,image/gif" multiple onChange={(event) => {
        onImport?.([...event.currentTarget.files ?? []])
        event.currentTarget.value = ''
      }} />
      <button className="library-icon-button" type="button" aria-label="Import assets" title="Import assets" disabled={disabled} onClick={() => inputRef.current?.click()}>
        <Upload className="library-control-icon" aria-hidden="true" />
      </button>
    </div>
  )
}

function Preview({ item }: { item: TileItem }) {
  return (
    <span className={`library-preview library-preview--${item.preview}`}>
      {item.mediaUrl && item.mediaType?.startsWith('video/') && <video data-library-preview src={item.mediaUrl} muted preload="metadata" />}
      {item.mediaUrl && item.mediaType?.startsWith('image/') && <img data-library-preview src={item.mediaUrl} alt="" />}
      {item.image && <img data-library-preview src={item.image} alt="" />}
      {!item.image && item.accent && <span className={`library-preview-accent library-preview-accent--${item.accent}`} />}
      {!item.image && item.status && <span className="library-preview-badge library-preview-status">{item.status}</span>}
      {!item.image && item.duration && <span className="library-preview-badge library-preview-duration">{item.duration}</span>}
      {!item.image && item.previewText && <span className="library-preview-copy">{item.previewText}</span>}
    </span>
  )
}

function TileGrid({
  items,
  kind,
  selectedId,
  onSelect,
  assetSize = false,
}: {
  items: readonly TileItem[]
  kind: NonNullable<EditorSelection>['kind']
  selectedId?: string
  onSelect: (selection: NonNullable<EditorSelection>) => void
  assetSize?: boolean
}) {
  const gridClassName = assetSize
    ? 'library-grid library-grid--assets'
    : kind === 'card' ? 'library-grid library-grid--cards' : 'library-grid'

  return (
    <div className={gridClassName}>
      {items.map((item) => (
        <button
          className={assetSize ? 'library-tile library-tile--asset' : 'library-tile'}
          type="button"
          key={item.id}
          data-asset-id={assetSize ? item.id : undefined}
          aria-pressed={selectedId === item.id}
          onClick={() => onSelect({ kind, id: item.id })}
        >
          <Preview item={item} />
          <span className="library-tile-label" title={item.label}>{item.label}</span>
        </button>
      ))}
    </div>
  )
}

function EmptyAssets({ onImport, disabled }: { onImport?: () => void; disabled?: boolean }) {
  return (
    <div className="asset-dropzone">
      <button className="asset-import-action" type="button" disabled={disabled} onClick={onImport}>
        <span className="asset-import-icon"><Plus aria-hidden="true" size={20} /></span>
        <span>Import media</span>
      </button>
      <p>Drag and drop videos, photos, and audio files here</p>
      <small>MP4, MOV, WebM, MP3, WAV, JPG, PNG</small>
    </div>
  )
}

function RuntimeEmpty({ children }: { children: ReactNode }) {
  return <div className="library-runtime-empty" role="status">{children}</div>
}

function AssetsPanel({ store, importAssets }: LibraryPanelProps) {
  const project = useStore(store, (state) => state.project)
  const selection = useStore(store, (state) => state.selection)
  const select = useStore(store, (state) => state.select)
  const runtime = Boolean(project?.runtime)
  const assetTiles = project?.assets.map((asset) => tileForAsset(asset, runtime)) ?? []
  const [importError, setImportError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const importInputRef = useRef<HTMLInputElement>(null)
  const normalizedQuery = query.trim().toLocaleLowerCase()
  const visibleAssetTiles = normalizedQuery
    ? assetTiles.filter((asset) => asset.label.toLocaleLowerCase().includes(normalizedQuery))
    : assetTiles
  const importFiles = async (files: readonly File[]) => {
    if (!importAssets || !files.length) return
    setImportError(null)
    try {
      await importAssets(files)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'Could not import media')
    }
  }
  const importFromInput = (event: ChangeEvent<HTMLInputElement>) => {
    void importFiles([...event.currentTarget.files ?? []])
    event.currentTarget.value = ''
  }
  const importFromDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    void importFiles([...event.dataTransfer.files])
  }

  return (
    <>
      <AssetControls
        onImport={(files) => { void importFiles(files) }}
        disabled={!importAssets}
        query={query}
        onQueryChange={setQuery}
      />
      <input ref={importInputRef} className="asset-file-input" type="file" accept="video/mp4,video/quicktime,video/webm,audio/mpeg,audio/wav,image/jpeg,image/png,image/webp,image/gif" multiple onChange={importFromInput} />
      {visibleAssetTiles.length ? (
        <TileGrid items={visibleAssetTiles} kind="asset" selectedId={selection?.id} onSelect={select} assetSize />
      ) : assetTiles.length ? (
        <RuntimeEmpty>No assets match "{query.trim()}"</RuntimeEmpty>
      ) : (
        <div onDrop={importFromDrop} onDragOver={(event) => event.preventDefault()}>
          <EmptyAssets onImport={() => importInputRef.current?.click()} disabled={!importAssets} />
        </div>
      )}
      {importError ? <RuntimeEmpty>{importError}</RuntimeEmpty> : null}
    </>
  )
}

function ThemeControls() {
  return (
    <>
      <div className="caption-theme-row">
        <span>Theme</span>
        {['outline', 'yellow', 'green', 'cyan', 'pink'].map((theme) => (
          <button key={theme} type="button" className={`theme-swatch theme-swatch--${theme}`} aria-label={`${theme} theme`} />
        ))}
      </div>
      <label className="word-highlight-row">
        <span>Word highlight</span>
        <input type="checkbox" defaultChecked />
      </label>
    </>
  )
}

function CaptionsPanel({ store }: LibraryPanelProps) {
  const project = useStore(store, (state) => state.project)
  const selection = useStore(store, (state) => state.selection)
  const select = useStore(store, (state) => state.select)
  const operation = project?.operations?.find((item) => item.id === 'captions')
  const runtime = Boolean(project?.runtime)
  const captionCues = project?.tracks.find((track) => track.kind === 'caption')?.clips ?? []
  if (runtime) {
    const items: TileItem[] = captionCues.map((cue) => ({
      id: cue.id, label: cue.summary || 'Untitled caption', preview: 'runtime', previewText: cue.summary || 'Untitled caption',
    }))
    return (
      <>
        {items.length
          ? <TileGrid items={items} kind="caption" selectedId={selection?.id} onSelect={select} />
          : <RuntimeEmpty>No caption cues</RuntimeEmpty>}
        {operation?.editable ? <CaptionFields operation={operation} store={store} /> : null}
      </>
    )
  }
  return (
    <>
      <SearchField placeholder="Search caption styles" />
      <TileGrid items={captionStyles} kind="caption" selectedId={selection?.id} onSelect={select} />
      <ThemeControls />
    </>
  )
}

function PlacementControls() {
  return (
    <div className="placement-control">
      <span>Placement</span>
      <div className="placement-options" role="group" aria-label="Placement">
        <button type="button" aria-pressed="true">Lower third</button>
        <button type="button" aria-pressed="false">Center</button>
        <button type="button" aria-pressed="false">Full frame</button>
      </div>
    </div>
  )
}

function CaptionFields({ operation, store }: { operation: EditorOperationView; store: StoreApi<EditorState> }) {
  const selection = useStore(store, (state) => state.selection)
  const draft = useStore(store, (state) => state.getOperationDraft(operation.id))
  const edit = useStore(store, (state) => state.editOperationDraft)
  const cues = Array.isArray(operation.fields.cues) ? operation.fields.cues as readonly Readonly<Record<string, unknown>>[] : []
  const selectedId = selection?.kind === 'caption' ? selection.id : draft?.fields.cueId ?? cues[0]?.id
  const cue = cues.find((item) => item.id === selectedId)
  if (!cue || typeof selectedId !== 'string') return null
  const text = draftFieldsForCue(draft, selectedId)?.text ?? cue.text
  return (
    <fieldset aria-label="Caption fields" className="library-inspector-fields">
      <legend>{String(cue.id)}</legend>
      <label>
        Caption text
        <textarea aria-label="Caption text" value={String(text ?? '')} onChange={(event) => edit(operation.id, { cueId: selectedId, text: event.target.value })} />
      </label>
      <output>{formatCueRange(cue.program_range)}</output>
    </fieldset>
  )
}

function formatCueRange(value: unknown) {
  if (!value || typeof value !== 'object') return 'Unknown range'
  const range = value as { start_s?: unknown; end_s?: unknown }
  return typeof range.start_s === 'number' && typeof range.end_s === 'number'
    ? `${range.start_s.toFixed(3)}s - ${range.end_s.toFixed(3)}s`
    : 'Unknown range'
}

function CardsPanel({ store, operation }: LibraryPanelProps & { operation?: EditorOperationView }) {
  const project = useStore(store, (state) => state.project)
  const selection = useStore(store, (state) => state.selection)
  const select = useStore(store, (state) => state.select)
  const runtime = Boolean(project?.runtime)
  if (runtime) {
    const cues = project?.tracks.find((track) => track.kind === 'card')?.clips ?? []
    const items: TileItem[] = cues.map((cue) => ({
      id: cue.id, label: cue.summary || cue.displayName || 'Untitled card', preview: 'runtime', previewText: cue.summary || 'Untitled card',
    }))
    return (
      <>
        {items.length
          ? <TileGrid items={items} kind="card" selectedId={selection?.id} onSelect={select} />
          : <RuntimeEmpty>No content card cues</RuntimeEmpty>}
      </>
    )
  }
  return (
    <>
      <SearchField placeholder="Search content cards" />
      <TileGrid items={contentCards} kind="card" selectedId={selection?.id} onSelect={select} />
      <PlacementControls />
      <button className="library-primary-action" type="button">Insert content card</button>
    </>
  )
}

function MotionPanel({ store }: LibraryPanelProps) {
  const project = useStore(store, (state) => state.project)
  const selection = useStore(store, (state) => state.selection)
  const select = useStore(store, (state) => state.select)
  const [query, setQuery] = useState('')
  const runtime = Boolean(project?.runtime)
  if (runtime) {
    const cues = project?.tracks.find((track) => track.kind === 'graphic-motion')?.clips ?? []
    const items: TileItem[] = cues.map((cue) => ({
      id: cue.id, label: cue.summary || cue.displayName || 'Untitled motion', preview: 'runtime', previewText: cue.summary || 'Untitled motion',
    }))
    return (
      <>
        {items.length
          ? <TileGrid items={items} kind="graphic-motion" selectedId={selection?.id} onSelect={select} />
          : <RuntimeEmpty>No graphic motion cues</RuntimeEmpty>}
      </>
    )
  }
  const results = motionRecipes.filter((recipe) => recipe.label.toLowerCase().includes(query.trim().toLowerCase()))

  return (
    <>
      <label className="library-search">
        <img className="library-control-icon" src="/assets/editor/icon-search.svg" alt="" />
        <input
          aria-label="Search motion recipes"
          placeholder="Search motion recipes"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <TileGrid items={results} kind="graphic-motion" selectedId={selection?.id} onSelect={select} />
      <PlacementControls />
      <button className="library-primary-action" type="button">Insert motion</button>
    </>
  )
}

function PanelContent({ activeTab, store, operation }: { activeTab: LibraryTab; store: StoreApi<EditorState>; operation?: EditorOperationView }): ReactNode {
  if (activeTab === 'assets') return <AssetsPanel store={store} />
  if (activeTab === 'captions') return <CaptionsPanel store={store} />
  if (activeTab === 'cards') return <CardsPanel store={store} operation={operation} />
  return <MotionPanel store={store} />
}

export function LibraryPanel({ store, importAssets }: LibraryPanelProps) {
  const activeTab = useStore(store, (state) => state.activeTab)
  const visibleActiveTab: LibraryTab = activeTab === 'assets' ? activeTab : 'assets'
  const setActiveTab = useStore(store, (state) => state.setActiveTab)
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])
  const contentCardsOperation = useStore(store, (state) => state.project?.operations?.find((operation) => operation.kind === 'content-cards'))

  useEffect(() => {
    if (activeTab !== 'assets') setActiveTab('assets')
    tabRefs.current[tabs.findIndex((tab) => tab.id === visibleActiveTab)]?.scrollIntoView({
      block: 'nearest',
      inline: 'nearest',
    })
  }, [activeTab, setActiveTab, visibleActiveTab])

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex = index
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = tabs.length - 1
    else return

    event.preventDefault()
    setActiveTab(tabs[nextIndex].id)
    requestAnimationFrame(() => tabRefs.current[nextIndex]?.focus())
  }

  return (
    <section className="library-panel" role="region" aria-label="Library">
      <header className="library-titlebar">
        <div className="library-tabs" role="tablist" aria-label="Library sections">
          {tabs.map((tab, index) => {
            const selected = visibleActiveTab === tab.id
            return (
              <button
                key={tab.id}
                ref={(element) => { tabRefs.current[index] = element }}
                className="library-tab"
                data-tab={tab.id}
                id={`library-tab-${tab.id}`}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-controls="library-panel-content"
                tabIndex={selected ? 0 : -1}
                onClick={() => setActiveTab(tab.id)}
                onKeyDown={(event) => handleTabKeyDown(event, index)}
              >
                {tab.label}
              </button>
            )
          })}
        </div>
      </header>
      <div
        className="library-content"
        id="library-panel-content"
        role="tabpanel"
        aria-labelledby={`library-tab-${visibleActiveTab}`}
      >
        <AssetsPanel store={store} importAssets={importAssets} />
      </div>
    </section>
  )
}
