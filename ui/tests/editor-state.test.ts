import { expect, test } from '@playwright/test'
import type { EditorProjectView } from '../src/editor/editor-model'
import { projectFromSnapshot } from '../src/editor/EditorShell'
import {
  createEditorStore,
  type ContentCardsDraftChange,
} from '../src/editor/editor-store'
import { getScenario } from '../src/editor/scenarios'
import type { RuntimeSnapshot } from '../src/runtime/types'
import { RuntimeApiClient, RuntimeConflictError } from '../src/runtime/api-client'
import { reviewStatusText } from '../src/editor/ReviewStatusBar'

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
      approval: { status: 'none' },
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
  store.getState().setProject({
    ...project,
    operations: project.operations?.map((operation) => operation.id === 'content-cards'
      ? { ...operation, approval: { status: 'approved', revision: 3 } }
      : operation),
  })

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
  store.getState().setProject({
    ...project,
    operations: project.operations?.map((operation) => operation.id === 'content-cards'
      ? { ...operation, approval: { status: 'approved', revision: 3 } }
      : operation),
  })

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

test('runtime save delegates the draft and applies only the authoritative project', async () => {
  const authoritative: EditorProjectView = {
    ...project,
    revision: 8,
    operations: project.operations?.map((operation) => operation.id === 'content-cards'
      ? { ...operation, revision: 4, fields: { ...operation.fields, copy: 'Server copy' } }
      : operation),
  }
  const calls: unknown[] = []
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async (operationId, draft) => { calls.push({ operationId, draft }); return authoritative },
    review: async () => authoritative,
  })
  store.getState().editOperationDraft('content-cards', { copy: 'Client copy' })

  await store.getState().saveOperationDraft('content-cards')

  expect(calls).toEqual([{ operationId: 'content-cards', draft: { copy: 'Client copy' } }])
  expect(store.getState().project).toBe(authoritative)
  expect(store.getState().getOperationDraft('content-cards')).toBeNull()
})

test('a conflict-shaped failure without an authoritative project remains retryable', async () => {
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async () => { throw Object.assign(new Error('conflict'), { conflict: true }) },
    review: async () => project,
  })
  store.getState().editOperationDraft('content-cards', { copy: 'Client copy' })

  await store.getState().saveOperationDraft('content-cards')

  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({
    dirty: true, conflict: false, pending: false, fields: { copy: 'Client copy' },
  })
  expect(store.getState().canSaveOperation('content-cards')).toBe(true)
})

test('an in-flight save preserves newer edits and blocks overlapping save requests', async () => {
  let resolveSave!: (project: EditorProjectView) => void
  let calls = 0
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async () => { calls += 1; return new Promise((resolve) => { resolveSave = resolve }) },
    review: async () => project,
  })
  store.getState().editOperationDraft('content-cards', { copy: 'Submitted copy' })
  const first = store.getState().saveOperationDraft('content-cards')
  store.getState().editOperationDraft('content-cards', { copy: 'Newer copy' })
  const second = store.getState().saveOperationDraft('content-cards')
  await Promise.resolve()
  expect(calls).toBe(1)
  resolveSave({ ...project, operations: project.operations?.map((operation) => operation.id === 'content-cards'
    ? { ...operation, revision: 4, fields: { ...operation.fields, copy: 'Submitted copy' } } : operation) })
  await first
  await second

  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({
    dirty: true, pending: false, fields: { copy: 'Newer copy' },
  })
})

test('runtime conflict applies authoritative project and preserves the local draft', async () => {
  const authoritative = { ...project, revision: 8, operations: project.operations?.map((operation) => operation.id === 'content-cards'
    ? { ...operation, revision: 4, fields: { ...operation.fields, copy: 'Agent copy' } } : operation) }
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async () => { throw Object.assign(new Error('conflict'), { conflict: true, project: authoritative }) },
    review: async () => project,
  })
  store.getState().editOperationDraft('content-cards', { copy: 'Local copy' })

  await store.getState().saveOperationDraft('content-cards')

  expect(store.getState().project).toBe(authoritative)
  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({ conflict: true, fields: { copy: 'Local copy' } })
})

test('runtime non-conflict failure remains visible and retryable', async () => {
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async () => { throw new Error('Protocol unavailable') }, review: async () => project,
  })
  store.getState().editOperationDraft('content-cards', { copy: 'Local copy' })

  await store.getState().saveOperationDraft('content-cards')

  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({
    dirty: true, pending: false, error: 'Protocol unavailable',
  })
  expect(store.getState().canSaveOperation('content-cards')).toBe(true)
})

test('project mutation busy remains retryable and is not classified as semantic conflict', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({
    ok: false, error: 'project mutation is busy',
  }), { status: 409, headers: { 'Content-Type': 'application/json' } })
  try {
    const client = new RuntimeApiClient('project-1')
    const error = await client.updateContentCards(
      { project: 'project-etag', operation: 'operation-etag', plan: 'plan-etag' },
      { schema_version: 1, cards: [] },
    ).then(() => null, (caught: unknown) => caught)

    expect(error).toBeInstanceOf(Error)
    expect(error).not.toBeInstanceOf(RuntimeConflictError)
    expect((error as Error).message).toBe('project mutation is busy')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('runtime review requires explicit rationale and surfaces backend failure', async () => {
  let calls = 0
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async () => project,
    review: async () => { calls += 1; throw new Error('Review service unavailable') },
  })

  await store.getState().recordReviewDecision('content-cards', 'approved')
  expect(calls).toBe(0)
  await store.getState().recordReviewDecision('content-cards', 'approved', 'Evidence looks correct')

  expect(calls).toBe(1)
  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({ error: 'Review service unavailable' })
})

test('review request identity blocks double submit and ignores an obsolete failure', async () => {
  let resolveReview!: (project: EditorProjectView) => void
  let calls = 0
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async () => project,
    review: async () => { calls += 1; return new Promise((resolve) => { resolveReview = resolve }) },
  })

  const first = store.getState().recordReviewDecision('content-cards', 'approved', 'Current evidence')
  const second = store.getState().recordReviewDecision('content-cards', 'rejected', 'Duplicate request')
  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({ pending: true, requestId: 1 })
  expect(store.getState().canApproveOperation('content-cards')).toBe(false)
  await Promise.resolve()
  expect(calls).toBe(1)
  resolveReview({ ...project, revision: 8 })
  await first
  await second

  expect(store.getState().project?.revision).toBe(8)
  expect(store.getState().getOperationDraft('content-cards')).toBeNull()
})

test('review conflict applies authoritative project and preserves local draft state', async () => {
  const authoritative = { ...project, revision: 8 }
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async () => project,
    review: async () => { throw Object.assign(new Error('conflict'), { conflict: true, project: authoritative }) },
  })

  await store.getState().recordReviewDecision('content-cards', 'approved', 'Current evidence')

  expect(store.getState().project).toBe(authoritative)
  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({
    dirty: false, conflict: true, pending: false, requestId: 1,
  })
})

test('review conflict-shaped failure without an authoritative project remains retryable', async () => {
  const store = createEditorStore({
    project, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  }, {
    save: async () => project,
    review: async () => { throw Object.assign(new Error('project mutation is busy'), { conflict: true }) },
  })

  await store.getState().recordReviewDecision('content-cards', 'approved', 'Current evidence')

  expect(store.getState().getOperationDraft('content-cards')).toMatchObject({
    dirty: false, conflict: false, pending: false, error: 'project mutation is busy',
  })
  expect(store.getState().canApproveOperation('content-cards')).toBe(true)
})

test('runtime snapshot displays a terminal decision without losing the unique current preview', () => {
  const snapshot: RuntimeSnapshot = {
    snapshot_etag: 'snapshot-r3',
    read_only: false,
    errors: [],
    resources: [],
    artifacts: [{
      id: 'artifact_current', name: 'current.png', size: 1, media_type: 'image/png',
      sha256: 'current-preview', url: '/v1/projects/p/artifacts/artifact_current',
    }],
    media: [],
    view: {
      operations: [{ id: 'content-cards', revision: 3, status: 'approved', etag: 'operation-r3' }],
      reviews: [
        {
          id: 'review-content-cards-current', revision: 1, status: 'draft',
          based_on: { 'content-cards': 3 }, snapshot_etag: 'snapshot-r3',
          evidence_hashes: ['sha256:current-preview'],
        },
        {
          id: 'review-content-cards-approved', revision: 1, status: 'approved', rationale: 'Evidence is correct',
          based_on: { 'content-cards': 3 }, snapshot_etag: 'snapshot-r3',
          evidence_hashes: ['sha256:approved-preview'],
        },
      ],
      content_cards_edit: {
        fields: project.operations?.[0]?.fields ?? {},
        review_template: { schema_version: 1, cards: [] },
      },
    },
  }

  const operation = projectFromSnapshot(project, snapshot)?.operations?.[0]

  expect(operation?.preview).toMatchObject({ status: 'current', reviewId: 'review-content-cards-current' })
  expect(operation?.approval).toEqual({ status: 'none' })
  const mapped = projectFromSnapshot(project, snapshot)
  const store = createEditorStore({
    project: mapped, activeTab: 'assets', selection: null, currentTimeS: 0,
    isPlaying: false, timelineZoom: 1, snapEnabled: true, openMenu: null,
  })
  expect(store.getState().canApproveOperation('content-cards')).toBe(true)
})

test('runtime snapshot maps terminal status only when it binds the exact preview', () => {
  const snapshot: RuntimeSnapshot = {
    snapshot_etag: 'snapshot-r3',
    read_only: false, errors: [], resources: [], artifacts: [{
      id: 'artifact_current', name: 'current.png', size: 1, media_type: 'image/png',
      sha256: 'current-preview', url: '/v1/projects/p/artifacts/artifact_current',
    }], media: [],
    view: {
      operations: [{ id: 'content-cards', revision: 3, status: 'approved', etag: 'operation-r3' }],
      reviews: [{
        id: 'review-content-cards-current', revision: 1, status: 'approved', rationale: 'Evidence is correct',
        based_on: { 'content-cards': 3 }, snapshot_etag: 'snapshot-r3', evidence_hashes: ['sha256:current-preview'],
      }],
      content_cards_edit: { fields: project.operations?.[0]?.fields ?? {}, review_template: { schema_version: 1, cards: [] } },
    },
  }

  const operation = projectFromSnapshot(project, snapshot)?.operations?.[0]
  expect(operation?.approval).toMatchObject({
    status: 'approved', revision: 3,
  })
  expect(operation?.preview).toEqual({
    status: 'current', revision: 3, reviewId: 'review-content-cards-current',
    snapshotEtag: 'snapshot-r3', evidenceHashes: ['sha256:current-preview'], artifacts: [{
      id: 'artifact_current', name: 'current.png', size: 1, sha256: 'current-preview',
      mediaType: 'image/png', url: '/v1/projects/p/artifacts/artifact_current',
    }],
  })
  expect(reviewStatusText(operation!, false)).toBe('Preview approved')
  const rejected = {
    ...operation!,
    approval: { ...operation!.approval!, status: 'rejected' as const },
  }
  expect(reviewStatusText(rejected, false)).toBe('Preview rejected')
})

test('captions-only runtime project is projected solely from the authoritative snapshot', () => {
  const snapshot: RuntimeSnapshot = {
    read_only: false,
    errors: [],
    resources: [
      { id: 'res_project', kind: 'project', etag: 'project-etag', size: 10 },
      { id: 'res_timeline', kind: 'timeline', etag: 'timeline-etag', size: 20 },
      { id: 'res_captions', kind: 'plan', etag: 'captions-plan', size: 30, operation_id: 'captions' },
    ],
    media: [{ id: 'asset_source', name: 'actual-source.mp4', size: 1234, media_type: 'video/mp4', url: '/v1/projects/p/media/asset_source' }],
    artifacts: [],
    snapshot_etag: 'snapshot-etag',
    view: {
      project_revision: 41,
      active_sequence: 'main',
      timeline: {
        duration_s: 9,
        fps: { num: 24, den: 1 },
        clips: [{ id: 'clip-real', source_range: { start_s: 2, end_s: 11 }, program_range: { start_s: 0, end_s: 9 } }],
      },
      operations: [{ id: 'captions', revision: 7, status: 'approved', etag: 'caption-operation' }],
      reviews: [],
    },
  }

  const mapped = projectFromSnapshot(getScenario('1-84')!.initialState.project, snapshot)

  expect(mapped).toMatchObject({
    revision: 41,
    durationS: 9,
    fps: { numerator: 24, denominator: 1 },
    assets: [{ id: 'asset_source', name: 'actual-source.mp4', kind: 'video' }],
    operations: [{ id: 'captions', kind: 'captions', revision: 7, editable: false }],
  })
  expect(mapped?.tracks.map((track) => [track.id, track.kind])).toEqual([
    ['track-video', 'video'], ['track-audio', 'audio'], ['track-captions', 'caption'],
  ])
  expect(mapped?.tracks[0].clips).toEqual([{
    id: 'clip-real', sourceRange: { startS: 2, endS: 11 }, programRange: { startS: 0, endS: 9 },
  }])
  expect(mapped?.assets.map((asset) => asset.name)).not.toContain('Product teaser.mov')
  expect(mapped?.durationS).not.toBe(127)
})

test('graphic-motion runtime projection preserves every authoritative operation and resource', () => {
  const snapshot: RuntimeSnapshot = {
    read_only: false, errors: [], snapshot_etag: 'snapshot-etag',
    resources: [
      { id: 'res_project', kind: 'project', etag: 'p', size: 1 },
      { id: 'res_timeline', kind: 'timeline', etag: 't', size: 1 },
      { id: 'res_cut', kind: 'plan', etag: 'cut', size: 1, operation_id: 'cut' },
      { id: 'res_gm', kind: 'plan', etag: 'gm', size: 1, operation_id: 'graphic-motion' },
    ],
    media: [], artifacts: [],
    view: {
      project_revision: 8, active_sequence: 'main',
      timeline: { duration_s: 4, fps: { num: 30000, den: 1001 }, clips: [] },
      operations: [
        { id: 'cut', revision: 2, status: 'approved', etag: 'cut-op' },
        { id: 'graphic-motion', revision: 5, status: 'draft', etag: 'gm-op' },
      ],
      reviews: [],
    },
  }

  const mapped = projectFromSnapshot(getScenario('1-84')!.initialState.project, snapshot)!

  expect(mapped.operations?.map((operation) => operation.id)).toEqual(['cut', 'graphic-motion'])
  expect(mapped.resources?.map((resource) => resource.id)).toEqual(['res_project', 'res_timeline', 'res_cut', 'res_gm'])
  expect(mapped.tracks).toEqual([])
  expect(mapped.assets).toEqual([])
})

test('content-cards runtime projection retains peer operations and binds exact current artifacts', () => {
  const evidence = `sha256:${'a'.repeat(64)}`
  const snapshot: RuntimeSnapshot = {
    read_only: false, errors: [], snapshot_etag: 'snapshot-current',
    resources: [{ id: 'res_project', kind: 'project', etag: 'p', size: 1 }],
    media: [],
    artifacts: [{
      id: 'artifact_still', name: 'current.png', size: 12, media_type: 'image/png',
      sha256: 'a'.repeat(64), url: '/v1/projects/p/artifacts/artifact_still',
    }],
    view: {
      project_revision: 3, active_sequence: 'main',
      timeline: { duration_s: 2, fps: { num: 30, den: 1 }, clips: [] },
      operations: [
        { id: 'captions', revision: 2, status: 'approved', etag: 'captions-op' },
        { id: 'content-cards', revision: 3, status: 'approved', etag: 'cards-op' },
      ],
      reviews: [{
        id: 'cards-review', revision: 1, status: 'draft', based_on: { 'content-cards': 3 },
        snapshot_etag: 'snapshot-current', evidence_hashes: [evidence],
      }],
      content_cards_edit: { fields: { copy: 'Actual copy' }, review_template: { schema_version: 1, cards: [] } },
    },
  }

  const mapped = projectFromSnapshot(getScenario('1-84')!.initialState.project, snapshot)!

  expect(mapped.operations?.map((operation) => operation.id)).toEqual(['captions', 'content-cards'])
  expect(mapped.operations?.find((operation) => operation.id === 'content-cards')?.preview?.artifacts).toEqual([
    expect.objectContaining({ id: 'artifact_still', url: '/v1/projects/p/artifacts/artifact_still' }),
  ])
})

test('runtime projection invalidates a terminal receipt when any bound artifact is absent', () => {
  const currentHash = 'a'.repeat(64)
  const missingHash = 'b'.repeat(64)
  const snapshot: RuntimeSnapshot = {
    read_only: false, errors: [], snapshot_etag: 'snapshot-current',
    resources: [{ id: 'res_project', kind: 'project', etag: 'p', size: 1 }],
    media: [],
    artifacts: [{
      id: 'artifact_current', name: 'current.png', size: 12, media_type: 'image/png',
      sha256: currentHash, url: '/v1/projects/p/artifacts/artifact_current',
    }],
    view: {
      project_revision: 3, active_sequence: 'main',
      timeline: { duration_s: 2, fps: { num: 30, den: 1 }, clips: [] },
      operations: [{ id: 'content-cards', revision: 3, status: 'approved', etag: 'cards-op' }],
      reviews: [{
        id: 'cards-decision', revision: 1, status: 'approved', based_on: { 'content-cards': 3 },
        snapshot_etag: 'snapshot-current', evidence_hashes: [`sha256:${currentHash}`, `sha256:${missingHash}`],
      }],
      content_cards_edit: { fields: { copy: 'Actual copy' }, review_template: { schema_version: 1, cards: [] } },
    },
  }

  const operation = projectFromSnapshot(null, snapshot)!.operations![0]

  expect(operation.preview).toMatchObject({ status: 'stale', reviewId: 'cards-decision' })
  expect(operation.approval).toMatchObject({ status: 'invalidated', reviewId: 'cards-decision' })
  expect(operation.approval?.evidenceHashes).toEqual([`sha256:${currentHash}`, `sha256:${missingHash}`])
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
