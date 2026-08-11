import type { EditorProjectView } from './editor-model'
import type { EditorInitialState } from './editor-store'

export const scenarioIds = [
  '1-60',
  '1-1373',
  '1-84',
  '1-282',
  '57-152',
  '1-1026',
  '1-324',
  '1-1115',
  '1-754',
  '1-528',
  '18-3',
  '76-2',
  '123-2',
  '123-79',
  '123-167',
  '126-2',
  'graphic-motion',
] as const

export type ScenarioId = (typeof scenarioIds)[number]

export type EditorScenario = Readonly<{
  id: ScenarioId
  initialState: EditorInitialState
}>

const populatedProject: EditorProjectView = {
  revision: 3,
  durationS: 127,
  fps: { numerator: 30, denominator: 1 },
  assets: [
    { id: 'asset-product', name: 'Product teaser.mov', kind: 'video' },
    { id: 'asset-interview', name: 'Founder interview.mp4', kind: 'video' },
    { id: 'asset-brand', name: 'Brand loop 04.mp4', kind: 'video' },
    { id: 'asset-city', name: 'City b-roll.mp4', kind: 'video' },
  ],
  tracks: [
    { id: 'track-video', name: 'Video', kind: 'video' },
    { id: 'track-audio', name: 'Audio', kind: 'audio' },
    { id: 'track-captions', name: 'Captions', kind: 'caption' },
  ],
}

const emptyProject: EditorProjectView = {
  revision: 1,
  durationS: 0,
  fps: { numerator: 30, denominator: 1 },
  assets: [],
  tracks: [],
}

function state(overrides: Partial<EditorInitialState> = {}): EditorInitialState {
  return {
    project: populatedProject,
    activeTab: 'assets',
    selection: null,
    currentTimeS: 0,
    isPlaying: false,
    timelineZoom: 1,
    snapEnabled: true,
    openMenu: null,
    ...overrides,
  }
}

const scenarios: readonly EditorScenario[] = [
  { id: '1-60', initialState: state() },
  { id: '1-1373', initialState: state({ project: emptyProject }) },
  { id: '1-84', initialState: state() },
  {
    id: '1-282',
    initialState: state({ selection: { kind: 'video', id: 'track-video' }, currentTimeS: 32 }),
  },
  { id: '57-152', initialState: state({ openMenu: 'viewer-more' }) },
  { id: '1-1026', initialState: state({ project: emptyProject }) },
  { id: '1-324', initialState: state() },
  { id: '1-1115', initialState: state({ project: emptyProject }) },
  { id: '1-754', initialState: state({ selection: { kind: 'video', id: 'track-video' } }) },
  { id: '1-528', initialState: state({ openMenu: 'aspect-ratio' }) },
  { id: '18-3', initialState: state({ project: emptyProject }) },
  { id: '76-2', initialState: state() },
  { id: '123-2', initialState: state({ activeTab: 'captions' }) },
  {
    id: '123-79',
    initialState: state({
      activeTab: 'captions',
      selection: { kind: 'caption', id: 'caption-1' },
      currentTimeS: 32,
    }),
  },
  {
    id: '123-167',
    initialState: state({ activeTab: 'captions', selection: { kind: 'caption', id: 'caption-1' } }),
  },
  { id: '126-2', initialState: state({ activeTab: 'cards' }) },
  { id: 'graphic-motion', initialState: state({ activeTab: 'graphic-motion' }) },
]

export function getScenario(id: string): EditorScenario | undefined {
  return scenarios.find((scenario) => scenario.id === id)
}
