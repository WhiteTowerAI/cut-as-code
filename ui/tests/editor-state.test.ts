import { expect, test } from '@playwright/test'
import type { EditorProjectView } from '../src/editor/editor-model'
import { createEditorStore } from '../src/editor/editor-store'
import { getScenario } from '../src/editor/scenarios'

const project: EditorProjectView = {
  revision: 7,
  durationS: 120,
  fps: { numerator: 30, denominator: 1 },
  assets: [],
  tracks: [],
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
