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
  'motion-graphics',
  'review-content-cards',
  'review-content-cards-conflict',
  'timeline-editing',
  'cue-context-actions',
  'audio-context-actions',
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

const cueContextProject: EditorProjectView = {
  ...populatedProject,
  runtime: true,
  durationS: 20,
  sourceDurationS: 20,
  tracks: [
    { id: 'track-video', name: 'Video', kind: 'video', clips: [{
      id: 'cue-video', displayName: 'Interview.mp4', sourceRange: { startS: 0, endS: 20 }, programRange: { startS: 0, endS: 20 },
    }] },
    { id: 'track-captions', name: 'Captions', kind: 'caption', clips: [{
      id: 'cue-caption', displayName: 'Caption 1', summary: 'Ship the smallest useful cut.',
      sourceText: 'Ship the smallest useful cut.', decisionRationale: 'Keep the statement on the stable lower baseline.',
      reviewStatus: 'approved', reviewEvidence: ['review/captions/frame-001.png'],
      sourceRange: { startS: 2, endS: 4 }, programRange: { startS: 2, endS: 4 },
    }] },
    { id: 'track-content-cards', name: 'Cards', kind: 'card', clips: [{
      id: 'cue-card', displayName: 'Card: lower-third', summary: 'Build once, deploy everywhere', enabled: true,
      sourceText: 'Build once and deploy everywhere.', decisionRationale: 'The phrase is the section thesis and has clear lower-left space.',
      evidenceRefs: ['segment:12'], reviewStatus: 'clear', reviewMode: 'agent', reviewEvidence: ['review/cards/card-001.png'],
      metadata: { layout: 'lower-third', placement: 'bottom-left' },
      sourceRange: { startS: 7, endS: 10 }, programRange: { startS: 7, endS: 10 },
    }] },
    { id: 'track-motion-graphics', name: 'Motion Graphics', kind: 'motion-graphics', clips: [{
      id: 'cue-motion', displayName: 'Motion: xyz-fade-up', summary: 'A system comes online', enabled: true,
      sourceText: 'The system comes online.', decisionRationale: 'The restrained rise makes the state change legible.',
      reviewStatus: 'verified', reviewMode: 'agent', reviewEvidence: ['review/motion/gm-001.png'],
      metadata: { recipe: 'xyz-fade-up', source: 'bound', license: 'verified' },
      sourceRange: { startS: 13, endS: 15 }, programRange: { startS: 13, endS: 15 },
    }] },
  ],
  operations: [
    {
      id: 'captions', kind: 'captions', revision: 1, editable: true,
      fields: { cues: [{ id: 'cue-caption', text: 'Ship the smallest useful cut.', program_range: { start_s: 2, end_s: 4 } }] },
      preview: { status: 'current', revision: 1, reviewId: 'caption-review', snapshotEtag: 'caption-snapshot', evidenceHashes: ['sha256:caption-preview'] },
      approval: { status: 'none' },
    },
    {
      id: 'content-cards', kind: 'content-cards', revision: 1, editable: true,
      fields: { cues: [{ id: 'cue-card', copy: 'Build once, deploy everywhere', layout: 'lower-third', placement: 'bottom-left', enabled: true, program_range: { start_s: 7, end_s: 10 } }] },
      preview: { status: 'current', revision: 1, reviewId: 'card-review', snapshotEtag: 'card-snapshot', evidenceHashes: ['sha256:card-preview'] },
      approval: { status: 'none' },
    },
    {
      id: 'motion-graphics', kind: 'motion-graphics', revision: 1, editable: true,
      fields: { cues: [{ id: 'cue-motion', enabled: true, content: 'A system comes online', program_range: { start_s: 13, end_s: 15 } }] },
      preview: { status: 'current', revision: 1, reviewId: 'motion-review', snapshotEtag: 'motion-snapshot', evidenceHashes: ['sha256:motion-preview'] },
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

const editableTimelineProject: EditorProjectView = {
  ...populatedProject,
  durationS: 20,
  sourceDurationS: 30,
  timelineEditable: true,
  tracks: [
    {
      ...populatedProject.tracks[0],
      clips: [
        {
          id: 'edit-video-1',
          sourceRange: { startS: 0, endS: 8 },
          programRange: { startS: 0, endS: 8 },
          speed: 1,
        },
        {
          id: 'edit-video-2',
          sourceRange: { startS: 12, endS: 24 },
          programRange: { startS: 8, endS: 20 },
          speed: 1,
        },
      ],
    },
    {
      ...populatedProject.tracks[1],
      clips: [{
        id: 'edit-audio',
        sourceRange: { startS: 0, endS: 20 },
        programRange: { startS: 0, endS: 20 },
        speed: 1,
      }],
    },
    {
      id: 'edit-cards',
      name: 'Cards',
      kind: 'card',
      clips: [{
        id: 'edit-card-1',
        trackId: 'edit-cards',
        displayName: 'Later card',
        summary: 'Right-side ripple marker',
        sourceRange: { startS: 16, endS: 18 },
        programRange: { startS: 16, endS: 18 },
      }],
    },
  ],
  layers: [{
    id: 'edit-layer-1',
    operationId: 'content-cards',
    cueId: 'edit-card-1',
    kind: 'card',
    mediaType: 'dom',
    zIndex: 200,
    programRange: { startS: 16, endS: 18 },
    transform: { x: 0.5, y: 0.5, scale: 1 },
    content: { text: 'Right-side ripple marker' },
  }],
}

const audioContextProject: EditorProjectView = {
  ...editableTimelineProject,
  durationS: 24,
  tracks: editableTimelineProject.tracks.map((track) => {
    if (track.kind === 'video') return {
      ...track,
      clips: track.clips?.map((clip, index) => ({
        ...clip,
        displayName: 'Interview.mp4',
        audioMode: 'embedded' as const,
        ...(index === 1 ? { programRange: { startS: 12, endS: 24 } } : {}),
      })),
    }
    if (track.kind === 'audio') return {
      ...track,
      clips: editableTimelineProject.tracks.find((candidate) => candidate.kind === 'video')!.clips!.map((clip, index) => ({
        ...clip,
        id: `${clip.id}:embedded-audio`,
        trackId: track.id,
        displayName: 'Interview audio',
        linkedClipId: clip.id,
        linked: true,
        muted: false,
        implicit: true,
        ...(index === 1 ? { programRange: { startS: 12, endS: 24 } } : {}),
      })),
    }
    return track
  }),
}

function state(overrides: Partial<EditorInitialState> = {}): EditorInitialState {
  return {
    project: populatedProject,
    activeTab: 'assets',
    selection: null,
    currentTimeS: 0,
    isPlaying: false,
    playbackRange: null,
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
  { id: 'motion-graphics', initialState: state({ activeTab: 'motion-graphics' }) },
  { id: 'review-content-cards', initialState: state({ project: reviewProject, activeTab: 'cards' }) },
  {
    id: 'review-content-cards-conflict',
    initialState: state({
      project: reviewProject,
      activeTab: 'cards',
    }),
  },
  {
    id: 'timeline-editing',
    initialState: state({ project: editableTimelineProject, currentTimeS: 4 }),
  },
  {
    id: 'cue-context-actions',
    initialState: state({ project: cueContextProject, currentTimeS: 0 }),
  },
  {
    id: 'audio-context-actions',
    initialState: state({ project: audioContextProject, currentTimeS: 0 }),
  },
]

export function getScenario(id: string): EditorScenario | undefined {
  return scenarios.find((scenario) => scenario.id === id)
}
