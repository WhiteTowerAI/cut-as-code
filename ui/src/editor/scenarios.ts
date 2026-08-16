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
  'review-content-cards',
  'review-content-cards-conflict',
] as const

export type ScenarioId = (typeof scenarioIds)[number]

export type EditorScenario = Readonly<{
  id: ScenarioId
  initialState: EditorInitialState
}>

const FIGMA_TIMELINE_PX_PER_SECOND = 876 / 20
const timeAtFigmaPx = (pixelX: number) => pixelX / FIGMA_TIMELINE_PX_PER_SECOND

const timelineClips = [
  {
    id: 'video-1',
    sourceRange: { startS: 0, endS: timeAtFigmaPx(279 - 16) },
    programRange: { startS: 0, endS: timeAtFigmaPx(279 - 16) },
  },
  {
    id: 'video-2',
    sourceRange: { startS: timeAtFigmaPx(283 - 16), endS: timeAtFigmaPx(796 - 16) },
    programRange: { startS: timeAtFigmaPx(283 - 16), endS: timeAtFigmaPx(796 - 16) },
  },
] as const

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
    {
      id: 'track-audio',
      name: 'Audio',
      kind: 'audio',
    },
    {
      id: 'track-captions',
      name: 'Captions',
      kind: 'caption',
    },
  ],
}

const emptyProject: EditorProjectView = {
  revision: 1,
  durationS: 0,
  fps: { numerator: 30, denominator: 1 },
  assets: [],
  tracks: [],
}

const reviewProject: EditorProjectView = {
  ...populatedProject,
  runtime: true,
  tracks: [
    ...populatedProject.tracks,
    {
      id: 'track-content-cards',
      name: 'Cards',
      kind: 'card',
      clips: [{
        id: 'card-review-1',
        trackId: 'track-content-cards',
        displayName: 'Card: lower-third',
        summary: 'Meet the product team',
        enabled: true,
        sourceRange: { startS: 4, endS: 8 },
        programRange: { startS: 4, endS: 8 },
      }],
    },
  ],
  operations: [
    {
      id: 'content-cards',
      kind: 'content-cards',
      revision: 3,
      editable: true,
      fields: {
        cues: [{
          id: 'card-review-1',
          card_type: 'lower-third',
          copy: 'Meet the product team',
          layout: 'lower-third',
          placement: 'bottom-left',
          enabled: true,
          program_range: { start_s: 4, end_s: 8 },
        }],
      },
      preview: {
        status: 'current',
        revision: 3,
        reviewId: 'review-content-cards-r3',
        snapshotEtag: 'snapshot-r3',
        evidenceHashes: ['sha256:content-cards-preview-r3'],
      },
      approval: { status: 'none' },
    },
    {
      id: 'captions',
      kind: 'captions',
      revision: 3,
      editable: false,
      fields: {},
      preview: {
        status: 'current',
        revision: 3,
        reviewId: 'review-captions-r3',
        snapshotEtag: 'snapshot-captions-r3',
        evidenceHashes: ['sha256:captions-preview-r3'],
      },
      approval: { status: 'none' },
    },
  ],
}

const fiveSecondProject: EditorProjectView = { ...populatedProject, durationS: 5 }
const twentySecondProject: EditorProjectView = {
  ...populatedProject,
  durationS: 20,
  tracks: [
    { ...populatedProject.tracks[0], clips: timelineClips },
    {
      ...populatedProject.tracks[1],
      clips: [{ id: 'audio-1', sourceRange: { startS: 0, endS: timeAtFigmaPx(796 - 16) }, programRange: { startS: 0, endS: timeAtFigmaPx(796 - 16) } }],
    },
    {
      ...populatedProject.tracks[2],
      clips: [
        { id: 'caption-1', sourceRange: { startS: 0, endS: timeAtFigmaPx(126) }, programRange: { startS: 0, endS: timeAtFigmaPx(126) } },
        { id: 'caption-2', sourceRange: { startS: timeAtFigmaPx(132), endS: timeAtFigmaPx(274) }, programRange: { startS: timeAtFigmaPx(132), endS: timeAtFigmaPx(274) } },
        { id: 'caption-3', sourceRange: { startS: timeAtFigmaPx(286), endS: timeAtFigmaPx(444) }, programRange: { startS: timeAtFigmaPx(286), endS: timeAtFigmaPx(444) } },
        { id: 'caption-4', sourceRange: { startS: timeAtFigmaPx(456), endS: timeAtFigmaPx(584) }, programRange: { startS: timeAtFigmaPx(456), endS: timeAtFigmaPx(584) } },
        { id: 'caption-5', sourceRange: { startS: timeAtFigmaPx(596), endS: timeAtFigmaPx(776) }, programRange: { startS: timeAtFigmaPx(596), endS: timeAtFigmaPx(776) } },
      ],
    },
  ],
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
  {
    id: '1-60',
    initialState: state({
      project: twentySecondProject,
      selection: { kind: 'video', id: 'video-2' },
      currentTimeS: timeAtFigmaPx(280),
    }),
  },
  { id: '1-1373', initialState: state({ project: emptyProject }) },
  { id: '1-84', initialState: state() },
  {
    id: '1-282',
    initialState: state({ project: fiveSecondProject, selection: { kind: 'video', id: 'track-video' } }),
  },
  { id: '57-152', initialState: state({ openMenu: 'viewer-more' }) },
  { id: '1-1026', initialState: state({ project: emptyProject }) },
  { id: '1-324', initialState: state({ project: twentySecondProject, currentTimeS: timeAtFigmaPx(280) }) },
  { id: '1-1115', initialState: state({ project: emptyProject }) },
  { id: '1-754', initialState: state({ project: twentySecondProject, selection: { kind: 'video', id: 'video-2' }, currentTimeS: timeAtFigmaPx(280) }) },
  { id: '1-528', initialState: state({ openMenu: 'aspect-ratio' }) },
  { id: '18-3', initialState: state({ project: emptyProject }) },
  { id: '76-2', initialState: state() },
  { id: '123-2', initialState: state({ activeTab: 'captions' }) },
  {
    id: '123-79',
    initialState: state({
      project: twentySecondProject,
      activeTab: 'captions',
      selection: { kind: 'caption', id: 'caption-1' },
      currentTimeS: 6.87,
    }),
  },
  {
    id: '123-167',
    initialState: state({
      project: twentySecondProject,
      activeTab: 'captions',
      selection: { kind: 'caption', id: 'caption-3' },
      currentTimeS: timeAtFigmaPx(280),
    }),
  },
  { id: '126-2', initialState: state({ activeTab: 'cards' }) },
  { id: 'graphic-motion', initialState: state({ activeTab: 'graphic-motion' }) },
  { id: 'review-content-cards', initialState: state({ project: reviewProject, activeTab: 'cards' }) },
  {
    id: 'review-content-cards-conflict',
    initialState: state({
      project: reviewProject,
      activeTab: 'cards',
    }),
  },
]

export function getScenario(id: string): EditorScenario | undefined {
  return scenarios.find((scenario) => scenario.id === id)
}
