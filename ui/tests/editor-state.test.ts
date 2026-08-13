import { expect, test } from '@playwright/test'
import type { EditorProjectView } from '../src/editor/editor-model'
import {
  createEditorStore,
  type ContentCardsDraftChange,
} from '../src/editor/editor-store'
import { getScenario } from '../src/editor/scenarios'

const project: EditorProjectView = {
  revision: 7,
  durationS: 120,
  fps: { numerator: 30, denominator: 1 },
  assets: [],
  tracks: [],
  operations: [
    {
      id: 'content-cards',
      kind: 'content-cards',
      revision: 3,
      editable: true,
      fields: {
        copy: 'Original copy',
        layout: 'lower-third',
        placement: 'bottom-left',
        enabled: true,
      },
      preview: {
        status: 'current',
        revision: 3,
        reviewId: 'review-content-cards-r3',
        snapshotEtag: 'snapshot-r3',
        evidenceHashes: ['sha256:content-cards-preview-r3'],
      },
      approval: { status: 'approved', revision: 3 },
    },
    {
      id: 'captions',
      kind: 'captions',
      revision: 2,
      editable: false,
      fields: {},
      preview: {
        status: 'current',
        revision: 2,
        reviewId: 'review-captions-r2',
        snapshotEtag: 'snapshot-captions-r2',
        evidenceHashes: ['sha256:captions-preview-r2'],
      },
      approval: { status: 'none' },
    },
  ],
}

function createStateStore() {
  return createEditorStore({
    project,
    activeTab: 'assets',
    selection: null,
    currentTimeS: 0,
    isPlaying: false,
    timelineZoom: 1,
    snapEnabled: true,
    openMenu: null,
  })
}

test('seek clamps time below zero and after the project duration', () => {
  const store = createStateStore()

  store.getState().seek(-5)
  expect(store.getState().currentTimeS).toBe(0)

  store.getState().seek(125)
  expect(store.getState().currentTimeS).toBe(120)
})

test('seek normalizes a non-finite time to zero', () => {
  const store = createStateStore()

  store.getState().seek(Number.NaN)

  expect(store.getState().currentTimeS).toBe(0)
})

test('select replaces the existing editor selection', () => {
  const store = createStateStore()

  store.getState().select({ kind: 'asset', id: 'asset-intro' })
  store.getState().select({ kind: 'caption', id: 'caption-3' })

  expect(store.getState().selection).toEqual({ kind: 'caption', id: 'caption-3' })
})

test('setOpenMenu keeps only the assigned menu open', () => {
  const store = createStateStore()

  store.getState().setOpenMenu('viewer-more')
  store.getState().setOpenMenu('aspect-ratio')

  expect(store.getState().openMenu).toBe('aspect-ratio')
})

test('setActiveTab changes the active library tab', () => {
  const store = createStateStore()

  store.getState().setActiveTab('graphic-motion')

  expect(store.getState().activeTab).toBe('graphic-motion')
})

test('setProject replaces the project snapshot with the next revision', () => {
  const store = createStateStore()
  const nextProject: EditorProjectView = {
    ...project,
    revision: 8,
    durationS: 90,
    assets: [{ id: 'asset-outro', name: 'Outro', kind: 'video' }],
  }

  store.getState().setProject(nextProject)

  expect(store.getState().project).toBe(nextProject)
  expect(store.getState().project).toMatchObject({ revision: 8, durationS: 90 })
  expect(store.getState().project?.assets).toEqual([
    { id: 'asset-outro', name: 'Outro', kind: 'video' },
  ])
})

test('content-card draft changes stay local until an explicit semantic save', () => {
  const store = createStateStore()

  store.getState().editOperationDraft('content-cards', { copy: 'Revised copy' })

  expect(store.getState().project?.operations?.[0]?.fields.copy).toBe('Original copy')
  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({
    fields: { copy: 'Revised copy' },
    dirty: true,
  })
  expect(store.getState().canApproveOperation('content-cards')).toBe(false)

  store.getState().saveOperationDraft('content-cards')

  expect(store.getState().project?.operations?.[0]).toMatchObject({
    revision: 4,
    fields: { copy: 'Revised copy' },
    preview: { status: 'stale', revision: 3 },
    approval: { status: 'invalidated', revision: 3 },
  })
  expect(store.getState().getOperationDraft('content-cards')).toBeNull()
})

test('saving a no-op operation draft does not increment its revision', () => {
  const store = createStateStore()

  store.getState().editOperationDraft('content-cards', { copy: 'Original copy' })
  store.getState().saveOperationDraft('content-cards')

  expect(store.getState().project?.operations?.[0]?.revision).toBe(3)
  expect(store.getState().project?.operations?.[0]?.preview.status).toBe('current')
})

test('approval requires a current preview bound to the same operation revision', () => {
  const store = createStateStore()

  store.getState().setProject({
    ...project,
    operations: project.operations?.map((operation) =>
      operation.id === 'content-cards'
        ? { ...operation, preview: { status: 'current', revision: 2 } }
        : operation,
    ),
  })

  expect(store.getState().canApproveOperation('content-cards')).toBe(false)
})

test('invalid content-card draft values and unknown fields are rejected at runtime', () => {
  const store = createStateStore()

  store.getState().editOperationDraft('content-cards', { enabled: 'yes' } as never)
  store.getState().editOperationDraft('content-cards', { layout: 'floating-card' } as never)
  store.getState().editOperationDraft('content-cards', { placement: 'middle' } as never)
  store
    .getState()
    .editOperationDraft('content-cards', { revision: 99 } as unknown as ContentCardsDraftChange)

  expect(store.getState().getOperationDraft('content-cards')).toBeNull()
})

test('saving invalidates a rejected approval bound to the old revision', () => {
  const store = createStateStore()
  store.getState().setProject({
    ...project,
    operations: project.operations?.map((operation) =>
      operation.id === 'content-cards'
        ? { ...operation, approval: { status: 'rejected', revision: 3 } }
        : operation,
    ),
  })

  store.getState().editOperationDraft('content-cards', { copy: 'Revised copy' })
  store.getState().saveOperationDraft('content-cards')

  expect(store.getState().project?.operations?.[0]?.approval).toEqual({
    status: 'invalidated',
    revision: 3,
  })
})

test('saving preserves an approval with no revision binding', () => {
  const store = createStateStore()
  store.getState().setProject({
    ...project,
    operations: project.operations?.map((operation) =>
      operation.id === 'content-cards' ? { ...operation, approval: { status: 'none' } } : operation,
    ),
  })

  store.getState().editOperationDraft('content-cards', { copy: 'Revised copy' })
  store.getState().saveOperationDraft('content-cards')

  expect(store.getState().project?.operations?.[0]?.approval).toEqual({ status: 'none' })
})

test('a rejection records its non-empty rationale against the current preview revision', () => {
  const store = createStateStore()

  store.getState().recordReviewDecision('content-cards', 'rejected', 'Title obscures the speaker')

  expect(store.getState().project?.operations?.[0]?.approval).toEqual({
    status: 'rejected',
    revision: 3,
    rationale: 'Title obscures the speaker',
    reviewId: 'review-content-cards-r3',
    snapshotEtag: 'snapshot-r3',
    evidenceHashes: ['sha256:content-cards-preview-r3'],
  })
})

test('a decision cannot be recorded without complete immutable preview evidence', () => {
  const store = createStateStore()
  store.getState().setProject({
    ...project,
    operations: project.operations?.map((operation) => operation.id === 'content-cards'
      ? { ...operation, preview: { status: 'current', revision: 3 }, approval: { status: 'none' } }
      : operation),
  })

  store.getState().recordReviewDecision('content-cards', 'approved')
  expect(store.getState().project?.operations?.[0]?.approval).toEqual({ status: 'none' })
})

test('an approved preview cannot be replaced by a rejection without a new review', () => {
  const store = createStateStore()

  store.getState().recordReviewDecision('content-cards', 'approved')
  store.getState().recordReviewDecision('content-cards', 'rejected', 'Too late to reject this review')

  expect(store.getState().project?.operations?.[0]?.approval).toMatchObject({ status: 'approved' })
  expect(store.getState().canApproveOperation('content-cards')).toBe(false)
})

test('a rejected preview cannot be replaced by an approval without a new review', () => {
  const store = createStateStore()

  store.getState().recordReviewDecision('content-cards', 'rejected', 'Title obscures the speaker')
  store.getState().recordReviewDecision('content-cards', 'approved')

  expect(store.getState().project?.operations?.[0]?.approval).toMatchObject({ status: 'rejected' })
  expect(store.getState().canApproveOperation('content-cards')).toBe(false)
})

test('read-only captions cannot record an approval or rejection despite a current preview', () => {
  const store = createStateStore()
  const before = store.getState().project?.operations?.[1]?.approval

  store.getState().recordReviewDecision('captions', 'approved')
  store.getState().recordReviewDecision('captions', 'rejected', 'No rationale should be stored')

  expect(store.getState().project?.operations?.[1]?.approval).toEqual(before)
})

test('discard restores the authoritative operation values', () => {
  const store = createStateStore()

  store.getState().editOperationDraft('content-cards', { placement: 'top-right' })
  store.getState().discardOperationDraft('content-cards')

  expect(store.getState().getOperationDraft('content-cards')).toBeNull()
  expect(store.getState().project?.operations?.[0]?.fields.placement).toBe('bottom-left')
})

test('an external update to the drafted operation creates a conflict and blocks save', () => {
  const store = createStateStore()
  store.getState().editOperationDraft('content-cards', { copy: 'Local copy' })

  store.getState().setProject({
    ...project,
    revision: 8,
    operations: project.operations?.map((operation) =>
      operation.id === 'content-cards'
        ? { ...operation, revision: 4, fields: { ...operation.fields, copy: 'Agent copy' } }
        : operation,
    ),
  })

  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({ conflict: true })
  expect(store.getState().canSaveOperation('content-cards')).toBe(false)
  expect(store.getState().canApproveOperation('content-cards')).toBe(false)
})

test('an external update discards a clean same-operation draft without blocking approval', () => {
  const store = createStateStore()
  store.getState().editOperationDraft('content-cards', { copy: 'Original copy' })

  store.getState().setProject({
    ...project,
    revision: 8,
    operations: project.operations?.map((operation) =>
      operation.id === 'content-cards'
        ? {
            ...operation,
            revision: 4,
            preview: {
              status: 'current',
              revision: 4,
              reviewId: 'review-content-cards-r4',
              snapshotEtag: 'snapshot-r4',
              evidenceHashes: ['sha256:content-cards-preview-r4'],
            },
          }
        : operation,
    ),
  })

  expect(store.getState().getOperationDraft('content-cards')).toBeNull()
  expect(store.getState().canApproveOperation('content-cards')).toBe(true)
})

test('an external update to a different operation does not conflict with this draft', () => {
  const store = createStateStore()
  store.getState().editOperationDraft('content-cards', { copy: 'Local copy' })

  store.getState().setProject({
    ...project,
    revision: 8,
    operations: project.operations?.map((operation) =>
      operation.id === 'captions' ? { ...operation, revision: 3 } : operation,
    ),
  })

  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({ conflict: false })
  expect(store.getState().canSaveOperation('content-cards')).toBe(true)
})

test('unsupported operations and fields cannot create editable drafts', () => {
  const store = createStateStore()

  store.getState().editOperationDraft('captions', { copy: 'Cannot write captions' })
  store
    .getState()
    .editOperationDraft('content-cards', { revision: 99 } as unknown as ContentCardsDraftChange)

  expect(store.getState().getOperationDraft('captions')).toBeNull()
  expect(store.getState().getOperationDraft('content-cards')).toBeNull()
})

test('getScenario resolves every dash-form Figma node and graphic motion', () => {
  const ids = [
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

  expect(ids.map((id) => getScenario(id)?.id)).toEqual(ids)
})

test('getScenario resolves the dedicated content cards review fixtures', () => {
  expect(getScenario('review-content-cards')?.initialState.project?.operations?.[0]?.kind).toBe('content-cards')
  expect(getScenario('review-content-cards-conflict')?.id).toBe('review-content-cards-conflict')
})
