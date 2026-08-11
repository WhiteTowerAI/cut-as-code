import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { Filter, Plus, Search, Upload } from 'lucide-react'
import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { AssetView, EditorSelection, LibraryTab } from './editor-model'
import type { EditorState } from './editor-store'

type LibraryPanelProps = {
  store: StoreApi<EditorState>
}

type TileItem = {
  id: string
  label: string
  preview: 'product' | 'founder' | 'brand' | 'city'
  previewText?: string
  duration?: string
  status?: string
  accent?: 'purple' | 'cyan' | 'yellow' | 'green' | 'pink'
}

const tabs: ReadonlyArray<{ id: LibraryTab; label: string }> = [
  { id: 'assets', label: 'My Assets' },
  { id: 'captions', label: 'Captions' },
  { id: 'cards', label: 'Cards' },
  { id: 'graphic-motion', label: 'Graphic Motion' },
]

const assetPreviewMetadata: Readonly<Record<string, Pick<TileItem, 'preview' | 'duration' | 'status'>>> = {
  'asset-product': { preview: 'product', duration: '00:18', status: 'Added' },
  'asset-interview': { preview: 'founder', duration: '18:42' },
  'asset-brand': { preview: 'brand', duration: '00:08' },
  'asset-city': { preview: 'city', duration: '00:05' },
}

const fallbackPreviews: readonly TileItem['preview'][] = ['product', 'founder', 'brand', 'city']

function tileForAsset(asset: AssetView): TileItem {
  const fallbackIndex = [...asset.id].reduce((sum, character) => sum + character.charCodeAt(0), 0) % fallbackPreviews.length
  const previewMetadata = assetPreviewMetadata[asset.id] ?? { preview: fallbackPreviews[fallbackIndex] }
  return { id: asset.id, label: asset.name, ...previewMetadata }
}

const captionStyles: readonly TileItem[] = [
  { id: 'caption-clean', label: 'Clean', preview: 'product', previewText: 'Caption', status: 'Added' },
  { id: 'caption-minimal', label: 'Minimal', preview: 'founder', previewText: 'Caption' },
  { id: 'caption-social', label: 'Social bold', preview: 'brand', previewText: 'STAY CURIOUS' },
  { id: 'caption-pill', label: 'Pill', preview: 'city', previewText: 'Caption' },
  { id: 'caption-boxed', label: 'Boxed', preview: 'product', previewText: 'Caption' },
  { id: 'caption-stroked', label: 'Stroked', preview: 'founder', previewText: 'Caption' },
  { id: 'caption-shorts', label: 'Shorts', preview: 'brand', previewText: 'keep creating' },
]

const contentCards: readonly TileItem[] = [
  { id: 'card-lower-third', label: 'Lower third', preview: 'product', previewText: 'Presenter', duration: '00:18', status: 'Added', accent: 'purple' },
  { id: 'card-quote', label: 'Quote', preview: 'founder', previewText: 'Pull quote', duration: '18:42', accent: 'cyan' },
  { id: 'card-stat', label: 'Stat', preview: 'brand', previewText: '72%', duration: '00:08', accent: 'yellow' },
  { id: 'card-split', label: 'Split', preview: 'city', previewText: 'Before / after', duration: '00:05', accent: 'green' },
  { id: 'card-cta', label: 'CTA', preview: 'product', previewText: 'Try it now', duration: '00:18', status: 'Added', accent: 'pink' },
  { id: 'card-product', label: 'Product', preview: 'founder', previewText: 'Feature callout', duration: '18:42', accent: 'purple' },
]

const motionRecipes: readonly TileItem[] = [
  { id: 'xyz-fade-up', label: 'XYZ Fade Up', preview: 'product', previewText: 'Fade up', accent: 'purple' },
  { id: 'xyz-fade-left', label: 'XYZ Fade Left', preview: 'founder', previewText: 'Fade left', accent: 'cyan' },
  { id: 'xyz-fade-big', label: 'XYZ Fade Big', preview: 'brand', previewText: 'Fade big', accent: 'yellow' },
  { id: 'xyz-fade-small', label: 'XYZ Fade Small', preview: 'city', previewText: 'Fade small', accent: 'green' },
]

function SearchField({ placeholder, compact = false }: { placeholder: string; compact?: boolean }) {
  return (
    <label className={compact ? 'library-search library-search--compact' : 'library-search'}>
      <Search aria-hidden="true" size={16} strokeWidth={1.7} />
      <input aria-label={placeholder} placeholder={placeholder} />
    </label>
  )
}

function AssetControls() {
  return (
    <div className="library-controls">
      <SearchField placeholder="Search assets" compact />
      <button className="library-icon-button" type="button" aria-label="Import assets" title="Import assets">
        <Upload aria-hidden="true" size={16} strokeWidth={1.7} />
      </button>
      <button className="library-icon-button" type="button" aria-label="Filter assets" title="Filter assets">
        <Filter aria-hidden="true" size={16} strokeWidth={1.7} />
      </button>
    </div>
  )
}

function Preview({ item }: { item: TileItem }) {
  return (
    <span className={`library-preview library-preview--${item.preview}`}>
      {item.accent && <span className={`library-preview-accent library-preview-accent--${item.accent}`} />}
      {item.status && <span className="library-preview-badge library-preview-status">{item.status}</span>}
      {item.duration && <span className="library-preview-badge library-preview-duration">{item.duration}</span>}
      {item.previewText && <span className="library-preview-copy">{item.previewText}</span>}
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
  return (
    <div className={assetSize ? 'library-grid library-grid--assets' : 'library-grid'}>
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

function EmptyAssets() {
  return (
    <div className="asset-dropzone">
      <button className="asset-import-action" type="button">
        <span className="asset-import-icon"><Plus aria-hidden="true" size={20} /></span>
        <span>Import media</span>
      </button>
      <p>Drag and drop videos, photos, and audio files here</p>
      <small>MP4, MOV, WebM, MP3, WAV, JPG, PNG</small>
    </div>
  )
}

function AssetsPanel({ store }: LibraryPanelProps) {
  const project = useStore(store, (state) => state.project)
  const selection = useStore(store, (state) => state.selection)
  const select = useStore(store, (state) => state.select)
  const assetTiles = project?.assets.map(tileForAsset) ?? []

  return (
    <>
      <AssetControls />
      {assetTiles.length ? (
        <TileGrid items={assetTiles} kind="asset" selectedId={selection?.id} onSelect={select} assetSize />
      ) : (
        <EmptyAssets />
      )}
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
  const selection = useStore(store, (state) => state.selection)
  const select = useStore(store, (state) => state.select)
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

function CardsPanel({ store }: LibraryPanelProps) {
  const selection = useStore(store, (state) => state.selection)
  const select = useStore(store, (state) => state.select)
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
  const selection = useStore(store, (state) => state.selection)
  const select = useStore(store, (state) => state.select)
  const [query, setQuery] = useState('')
  const results = motionRecipes.filter((recipe) => recipe.label.toLowerCase().includes(query.trim().toLowerCase()))

  return (
    <>
      <label className="library-search">
        <Search aria-hidden="true" size={16} strokeWidth={1.7} />
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

function PanelContent({ activeTab, store }: { activeTab: LibraryTab; store: StoreApi<EditorState> }): ReactNode {
  if (activeTab === 'assets') return <AssetsPanel store={store} />
  if (activeTab === 'captions') return <CaptionsPanel store={store} />
  if (activeTab === 'cards') return <CardsPanel store={store} />
  return <MotionPanel store={store} />
}

export function LibraryPanel({ store }: LibraryPanelProps) {
  const activeTab = useStore(store, (state) => state.activeTab)
  const setActiveTab = useStore(store, (state) => state.setActiveTab)
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])

  useEffect(() => {
    tabRefs.current[tabs.findIndex((tab) => tab.id === activeTab)]?.scrollIntoView({
      block: 'nearest',
      inline: 'nearest',
    })
  }, [activeTab])

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
            const selected = activeTab === tab.id
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
        aria-labelledby={`library-tab-${activeTab}`}
      >
        <PanelContent activeTab={activeTab} store={store} />
      </div>
    </section>
  )
}
