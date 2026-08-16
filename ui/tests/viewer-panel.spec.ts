import { expect, test } from '@playwright/test'
import {
  createPlaybackController,
  graphicMotionFrameNumber,
  isLayerActive,
  lastPresentedSourceTime,
  nativeBoundaryDelayMs,
  nativeBoundaryWakeup,
} from '../src/editor/ViewerPanel'
import type { ClipView, EditorLayerView } from '../src/editor/editor-model'

const runtimeSnapshot = (overrides: Record<string, unknown> = {}) => ({
  read_only: false,
  errors: [],
  view: {
    project_id: 'viewer-project',
    project_revision: 1,
    active_sequence: 'main',
    source_media_id: 'asset_source',
    sequence_geometry: { width: 1280, height: 720 },
    source_media: {
      name: 'landscape.mp4', duration_s: 10, width: 1280, height: 720,
      has_video: true, has_audio: true,
    },
    operations: [],
    reviews: [],
    timeline: {
      duration_s: 10,
      fps: { num: 30, den: 1 },
      clips: [{
        id: 'clip-1',
        source_range: { start_s: 0, end_s: 10 },
        program_range: { start_s: 0, end_s: 10 },
      }],
    },
  },
  resources: [],
  media: [{
    id: 'asset_source', name: 'landscape.mp4', size: 1024,
    media_type: 'video/mp4', url: '/fixtures/landscape.mp4',
  }],
  artifacts: [],
  ...overrides,
})

test('production runtime shows explicit loading and error surfaces without fixture fallback', async ({ page }) => {
  let releaseSnapshot: (() => void) | undefined
  await page.route('**/v1/projects/project_loading/snapshot', async (route) => {
    await new Promise<void>((resolve) => { releaseSnapshot = resolve })
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, snapshot: runtimeSnapshot() }) })
  })

  await page.goto('/?project=project_loading')
  await expect(page.getByRole('status', { name: 'Loading project' })).toBeVisible()
  await expect(page.locator('[data-editor-shell]')).toHaveCount(0)
  await expect(page.getByText('City Walk', { exact: true })).toHaveCount(0)
  await expect.poll(() => Boolean(releaseSnapshot)).toBe(true)
  releaseSnapshot?.()
  await expect(page.locator('[data-editor-shell]')).toBeVisible()

  await page.route('**/v1/projects/project_error/snapshot', (route) => route.abort('failed'))
  await page.goto('/?project=project_error')
  await expect(page.getByRole('alert', { name: 'Project unavailable' })).toBeVisible()
  await expect(page.locator('[data-editor-shell]')).toHaveCount(0)
  await expect(page.getByText('City Walk', { exact: true })).toHaveCount(0)
})

test('runtime workspace exactly fills common desktop viewports without document scrolling', async ({ page }) => {
  await page.route('**/v1/projects/project_viewport/snapshot', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, snapshot: runtimeSnapshot() }),
  }))

  for (const viewport of [
    { width: 1366, height: 768 },
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
    { width: 2560, height: 1440 },
  ]) {
    await page.setViewportSize(viewport)
    await page.goto('/?project=project_viewport')
    await expect(page.locator('[data-editor-shell]')).toBeVisible()
    const geometry = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
      bodyScrollWidth: document.body.scrollWidth,
      bodyScrollHeight: document.body.scrollHeight,
      shell: (() => {
        const rect = document.querySelector('[data-editor-shell]')!.getBoundingClientRect()
        return { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
      })(),
    }))
    expect(geometry.scrollWidth).toBe(viewport.width)
    expect(geometry.scrollHeight).toBe(viewport.height)
    expect(geometry.bodyScrollWidth).toBe(viewport.width)
    expect(geometry.bodyScrollHeight).toBe(viewport.height)
    expect(geometry.shell).toEqual({ x: 0, y: 0, width: viewport.width, height: viewport.height })
  }
})

test('Export Video is the only UI action that starts rendering and reports completion', async ({ page }) => {
  let starts = 0
  let polls = 0
  await page.route('**/v1/projects/project_export/snapshot', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, snapshot: runtimeSnapshot() }),
  }))
  await page.route('**/v1/projects/project_export/exports', async (route) => {
    starts += 1
    expect(route.request().method()).toBe('POST')
    expect(route.request().postDataJSON()).toEqual({})
    await route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, job: { id: 'export_abc', status: 'running' } }),
    })
  })
  await page.route('**/v1/projects/project_export/exports/status', async (route) => {
    polls += 1
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        job: polls < 2
          ? { id: 'export_abc', status: 'running' }
          : { id: 'export_abc', status: 'succeeded', output: 'final/final.mp4' },
      }),
    })
  })

  await page.goto('/?project=project_export')

  expect(starts).toBe(0)
  await page.getByRole('button', { name: 'Export Video' }).click()
  await expect(page.getByRole('button', { name: 'Rendering video' })).toBeDisabled()
  await expect(page.getByRole('status', { name: 'Export status' })).toContainText('Export complete')
  expect(starts).toBe(1)
  expect(polls).toBeGreaterThanOrEqual(2)
})

test('runtime Viewer uses real sequence geometry, contain fit, read-only aspect, and fullscreen', async ({ page }) => {
  await page.route('**/v1/projects/project_geometry/snapshot', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, snapshot: runtimeSnapshot() }),
  }))
  await page.addInitScript(() => {
    Object.defineProperty(HTMLElement.prototype, 'requestFullscreen', {
      configurable: true,
      value() {
        document.documentElement.dataset.fullscreenTarget = (this as HTMLElement).className
        return Promise.resolve()
      },
    })
  })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/?project=project_geometry')

  const canvas = page.locator('.viewer-canvas')
  await expect(canvas).toHaveAttribute('data-sequence-width', '1280')
  await expect(canvas).toHaveAttribute('data-sequence-height', '720')
  const canvasBox = await canvas.boundingBox()
  const stageBox = await page.locator('.viewer-stage').boundingBox()
  expect(canvasBox).not.toBeNull()
  expect(stageBox).not.toBeNull()
  expect(canvasBox!.width / canvasBox!.height).toBeCloseTo(16 / 9, 2)
  expect(canvasBox!.width).toBeLessThanOrEqual(stageBox!.width)
  expect(canvasBox!.height).toBeLessThanOrEqual(stageBox!.height)
  await expect(canvas.locator('video')).toHaveCSS('object-fit', 'contain')

  await page.getByRole('button', { name: 'Aspect ratio' }).click()
  await expect(page.getByRole('menuitemradio', { name: /16:9/ })).toBeChecked()
  await expect(page.getByRole('menuitemradio', { name: /9:16/ })).not.toBeChecked()
  await expect(page.getByRole('menuitemradio', { name: /16:9/ })).toBeDisabled()

  await page.getByRole('button', { name: 'Fit preview' }).click()
  await expect(canvas).toHaveAttribute('data-fit-mode', 'fit')
  await page.getByRole('button', { name: 'Fullscreen' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-fullscreen-target', /viewer-stage/)
})

test('runtime Viewer composites source video, evidence, captions, cards, and Graphic Motion', async ({ page }) => {
  const base = runtimeSnapshot()
  const snapshot = runtimeSnapshot({
    view: {
      ...base.view,
      operations: [{ id: 'graphic-motion', revision: 1, status: 'verified', etag: 'gm-r1' }],
      reviews: [{
        id: 'review-gm-r1', revision: 1, status: 'draft', based_on: { 'graphic-motion': 1 },
        snapshot_etag: 'snapshot-layered', evidence_hashes: [`sha256:${'a'.repeat(64)}`],
      }],
      layers: [
        {
          id: 'layer_caption', operation_id: 'captions', cue_id: 'caption-001',
          kind: 'caption', media_type: 'dom', z_index: 100,
          program_range: { start_s: 0, end_s: 3 },
          transform: { x: 0.5, y: 0.82, scale: 1 },
          content: { text: 'Caption layer', style: { preset: 'clean' } },
        },
        {
          id: 'layer_card', operation_id: 'content-cards', cue_id: 'card-001',
          kind: 'card', media_type: 'dom', z_index: 200,
          program_range: { start_s: 0, end_s: 3 },
          transform: { x: 0.22, y: 0.2, scale: 0.9 },
          content: { text: 'Card layer', layout: 'lower-third', placement: 'top-left' },
        },
        {
          id: 'layer_motion', operation_id: 'graphic-motion', cue_id: 'gm-001',
          kind: 'graphic-motion', media_type: 'image-sequence', z_index: 300,
          program_range: { start_s: 0, end_s: 3 },
          transform: { x: 0.5, y: 0.5, scale: 1 },
          content: { text: 'THE REAL TONY STARK?' },
          image_sequence: {
            pattern: 'frame_%06d.png', start_number: 1, fps: { num: 30, den: 1 }, frame_count: 90,
            frame_url_template: '/v1/projects/viewer-project/layers/layer_motion/frames/%d',
          },
        },
      ],
    },
    snapshot_etag: 'snapshot-layered',
    resources: [
      { id: 'res_project', kind: 'project', etag: 'project-r1', size: 1 },
      { id: 'res_gm', kind: 'plan', etag: 'gm-plan-r1', size: 1, operation_id: 'graphic-motion' },
    ],
    artifacts: [{
      id: 'artifact_gm', name: 'gm-review.png', size: 1, sha256: 'a'.repeat(64),
      media_type: 'image/png', url: '/fixtures/gm-review.png',
    }],
  })
  await page.route('**/v1/projects/project_layers/snapshot', (route) => route.fulfill({
    contentType: 'application/json', body: JSON.stringify({ ok: true, snapshot }),
  }))

  await page.goto('/?project=project_layers')

  const canvas = page.locator('.viewer-canvas')
  await expect(canvas.locator('video[data-project-media]')).toHaveCount(1)
  await expect(canvas.locator('[data-viewer-layer]')).toHaveCount(3)
  await expect(canvas.getByText('Caption layer', { exact: true })).toBeVisible()
  await expect(canvas.getByText('Card layer', { exact: true })).toBeVisible()
  await expect(canvas.locator('[data-viewer-layer="graphic-motion"] img')).toHaveAttribute(
    'src', /\/layers\/layer_motion\/frames\/1$/,
  )
  await expect(page.getByRole('region', { name: 'Current review artifacts' })).toBeVisible()
  await expect(canvas.locator('img[alt="gm-review.png"]')).toHaveCount(0)
})

test('layer timing is half-open and Graphic Motion frame selection follows the program clock', () => {
  const layer: EditorLayerView = {
    id: 'layer_motion', operationId: 'graphic-motion', cueId: 'gm-001',
    kind: 'graphic-motion', mediaType: 'image-sequence', zIndex: 300,
    programRange: { startS: 2, endS: 5 },
    transform: { x: 0.5, y: 0.5, scale: 1 },
    content: { text: 'Motion' },
    imageSequence: {
      pattern: 'frame_%06d.png', startNumber: 1,
      fps: { numerator: 30000, denominator: 1001 }, frameCount: 90,
      frameUrlTemplate: '/frames/%d',
    },
  }

  expect(isLayerActive(layer, 1.999)).toBe(false)
  expect(isLayerActive(layer, 2)).toBe(true)
  expect(isLayerActive(layer, 4.999)).toBe(true)
  expect(isLayerActive(layer, 5)).toBe(false)
  expect(graphicMotionFrameNumber(layer, 2)).toBe(1)
  expect(graphicMotionFrameNumber(layer, 3.001)).toBe(31)
  expect(graphicMotionFrameNumber(layer, 20)).toBe(90)
})

test('dragging and scaling a Viewer layer stays local until Save Changes and never exports', async ({ page }) => {
  const transform = { x: 0.25, y: 0.25, scale: 1 }
  const snapshotFor = (revision: number, nextTransform = transform) => {
    const base = runtimeSnapshot()
    return runtimeSnapshot({
      snapshot_etag: `snapshot-${revision}`,
      view: {
        ...base.view,
        project_revision: revision,
        operations: [{
          id: 'content-cards', revision, status: 'draft', etag: `cards-operation-${revision}`,
        }],
        reviews: [],
        content_cards_edit: {
          fields: {},
          review_template: {
            schema_version: 1,
            cards: [{
              id: 'card-001', selected: true, copy: 'Editable card',
              placement: 'top-left', visual_treatment: 'lower-third',
            }],
          },
          cues: [{
            id: 'card-001', card_type: 'lower-third', copy: 'Editable card',
            layout: 'lower-third', placement: 'top-left', enabled: true,
            program_range: { start_s: 0, end_s: 5 }, transform: nextTransform,
          }],
        },
        layers: [{
          id: 'layer_card', operation_id: 'content-cards', cue_id: 'card-001',
          kind: 'card', media_type: 'dom', z_index: 200,
          program_range: { start_s: 0, end_s: 5 }, transform: nextTransform,
          content: { text: 'Editable card', layout: 'lower-third', placement: 'top-left' },
        }],
      },
      resources: [
        { id: 'res_project', kind: 'project', etag: `project-${revision}`, size: 1 },
        { id: 'res_cards', kind: 'plan', etag: `cards-plan-${revision}`, size: 1, operation_id: 'content-cards' },
      ],
    })
  }
  let snapshot = snapshotFor(1)
  let transactionBody: Record<string, unknown> | undefined
  let exportRequests = 0
  page.on('request', (request) => {
    if (/\/exports?(?:\/|$)/.test(new URL(request.url()).pathname)) exportRequests += 1
  })
  await page.route('**/v1/projects/project_transform/snapshot', (route) => route.fulfill({
    contentType: 'application/json', body: JSON.stringify({ ok: true, snapshot }),
  }))
  await page.route('**/v1/projects/project_transform/transactions', async (route) => {
    transactionBody = route.request().postDataJSON() as Record<string, unknown>
    const review = transactionBody.review as { editor_transform?: { x: number; y: number; scale: number } }
    snapshot = snapshotFor(2, review.editor_transform)
    await route.fulfill({
      contentType: 'application/json', body: JSON.stringify({ ok: true, result: 'committed', snapshot }),
    })
  })

  await page.goto('/?project=project_transform')

  const layer = page.locator('[data-layer-id="layer_card"]')
  const initial = await layer.boundingBox()
  expect(initial).not.toBeNull()
  await page.mouse.move(initial!.x + initial!.width / 2, initial!.y + initial!.height / 2)
  await page.mouse.down()
  await page.mouse.move(initial!.x + initial!.width / 2 + 80, initial!.y + initial!.height / 2 + 45)
  await page.mouse.up()
  await expect(layer).toHaveAttribute('data-layer-selected', 'true')
  await expect(layer).not.toHaveAttribute('data-layer-x', '0.25')

  const scaleHandle = page.getByRole('button', { name: 'Scale layer' })
  const scaleBox = await scaleHandle.boundingBox()
  expect(scaleBox).not.toBeNull()
  await page.mouse.move(scaleBox!.x + scaleBox!.width / 2, scaleBox!.y + scaleBox!.height / 2)
  await page.mouse.down()
  await page.mouse.move(scaleBox!.x + scaleBox!.width / 2 + 40, scaleBox!.y + scaleBox!.height / 2 + 20)
  await page.mouse.up()
  await expect(layer).not.toHaveAttribute('data-layer-scale', '1')
  expect(transactionBody).toBeUndefined()
  expect(exportRequests).toBe(0)

  await page.getByRole('button', { name: 'Save Changes' }).click()
  await expect.poll(() => transactionBody).toBeTruthy()

  expect(transactionBody).toMatchObject({
    operation: 'content-cards',
    review: {
      schema_version: 1,
      editor_transform: {
        cue_id: 'card-001',
        x: expect.any(Number), y: expect.any(Number), scale: expect.any(Number),
      },
    },
  })
  expect(exportRequests).toBe(0)
})

test('Viewer playback is unavailable without an authoritative project video', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 688 })
  await page.goto('/?scenario=1-282')

  const play = page.getByRole('button', { name: 'Play' })
  await expect(play).toBeVisible()
  await expect(play).toBeDisabled()
})

test('playback controller seeks the assigned media element', async () => {
  const media = {
    currentTime: 3,
    duration: 127,
    paused: true,
    play: async () => undefined,
    pause: () => undefined,
  } as unknown as HTMLVideoElement
  const playback = createPlaybackController(media)

  playback.seek(42.25)

  expect(playback.getTime()).toBe(42.25)
  expect(playback.getDuration()).toBe(127)
  expect(playback.isPlaying()).toBe(false)
})

test('native playback boundary uses one source frame and rate only for wall-clock delay', async () => {
  const clip: ClipView = {
    id: 'clip-fast-a',
    sourceRange: { startS: 0.2, endS: 0.4 },
    programRange: { startS: 0, endS: 0.1 },
  }

  expect(lastPresentedSourceTime(clip, 1 / 30)).toBeCloseTo(0.366667, 5)
  expect(nativeBoundaryDelayMs(0.2, clip, 1 / 30, 2)).toBeCloseTo(100, 5)
})

test('boundary wakeup reschedules when the native media clock has not advanced', async () => {
  const clip: ClipView = {
    id: 'clip-fast-a',
    sourceRange: { startS: 0.2, endS: 0.4 },
    programRange: { startS: 0, endS: 0.1 },
  }

  const decision = nativeBoundaryWakeup(0.2, clip, 1 / 30, 2)

  expect(decision.action).toBe('reschedule')
  if (decision.action === 'reschedule') {
    expect(decision.delayMs).toBeCloseTo(100, 5)
  }
})

test('boundary wakeup waits through the final source frame presentation interval', async () => {
  const clip: ClipView = {
    id: 'clip-fast-a',
    sourceRange: { startS: 0.2, endS: 0.4 },
    programRange: { startS: 0, endS: 0.1 },
  }

  const decision = nativeBoundaryWakeup(0.37, clip, 1 / 30, 2)

  expect(decision.action).toBe('reschedule')
  if (decision.action === 'reschedule') {
    expect(decision.delayMs).toBeCloseTo(15, 5)
  }
})

test('the last legal source frame keeps its full presentation interval before the boundary', async () => {
  const clip: ClipView = {
    id: 'clip-fast-a',
    sourceRange: { startS: 0.2, endS: 0.4 },
    programRange: { startS: 0, endS: 0.1 },
  }
  const frameDurationS = 1 / 30

  const duringFinalFrame = nativeBoundaryWakeup(0.4 - frameDurationS, clip, frameDurationS, 2)
  const afterFinalFrame = nativeBoundaryWakeup(0.4, clip, frameDurationS, 2)

  expect(duringFinalFrame.action).toBe('reschedule')
  if (duringFinalFrame.action === 'reschedule') {
    expect(duringFinalFrame.delayMs).toBeCloseTo(frameDurationS / 2 * 1000, 5)
  }
  expect(afterFinalFrame).toEqual({ action: 'boundary', sourceTimeS: 0.4 })
})

test('opening one Viewer menu closes the other and Escape closes the open menu', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 688 })
  await page.goto('/?scenario=1-282')

  await page.getByRole('button', { name: 'More viewer actions' }).click()
  await expect(page.getByRole('menu', { name: 'More viewer actions' })).toBeVisible()

  await page.getByRole('button', { name: 'Aspect ratio' }).click()
  await expect(page.getByRole('menu', { name: 'More viewer actions' })).toHaveCount(0)
  await expect(page.getByRole('menu', { name: 'Aspect ratio' })).toBeVisible()

  await page.keyboard.press('Escape')
  await expect(page.getByRole('menu', { name: 'Aspect ratio' })).toHaveCount(0)
})

test('the More menu and Reset Transform stay within the compact Viewer viewport', async ({ page }) => {
  await page.setViewportSize({ width: 216, height: 462 })
  await page.goto('/?scenario=57-152')

  const [menuBox, resetTransformBox] = await Promise.all([
    page.getByRole('menu', { name: 'More viewer actions' }).boundingBox(),
    page.getByRole('menuitem', { name: 'Reset Transform' }).boundingBox(),
  ])
  expect(menuBox).not.toBeNull()
  expect(resetTransformBox).not.toBeNull()
  for (const box of [menuBox!, resetTransformBox!]) {
    expect(box.x).toBeGreaterThanOrEqual(-1)
    expect(box.y).toBeGreaterThanOrEqual(-1)
    expect(box.x + box.width).toBeLessThanOrEqual(217)
    expect(box.y + box.height).toBeLessThanOrEqual(463)
  }
})

test('the More menu preserves the official continuous row flow and inset dividers', async ({ page }) => {
  await page.setViewportSize({ width: 216, height: 462 })
  await page.goto('/?scenario=57-152')

  const geometry = await page.locator('.viewer-more-menu').evaluate((menu) => {
    const box = (element: Element) => {
      const rect = element.getBoundingClientRect()
      return { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
    }
    const sections = [...menu.querySelectorAll('.viewer-menu-section')]
    const section = (label: string) => sections.find((element) => element.querySelector('h3')?.textContent === label)!
    const item = (name: string) => menu.querySelector(`[aria-label="${name}"]`)
      ?? [...menu.querySelectorAll('button')].find((element) => element.textContent?.trim() === name)!
    const divider = (label: string) => {
      const element = section(label)
      const rect = element.getBoundingClientRect()
      const style = getComputedStyle(element, '::before')
      return {
        x: rect.x + Number.parseFloat(style.left),
        y: rect.y + Number.parseFloat(style.top),
        width: Number.parseFloat(style.width),
        height: Number.parseFloat(style.height),
      }
    }

    return {
      menu: box(menu),
      sections: Object.fromEntries(['TRANSFORM', 'ALIGNMENT', 'ARRANGE', 'MEDIA'].map((label) => [label, box(section(label))])),
      items: Object.fromEntries([
        'Flip Horizontal', 'Flip Vertical', 'Opacity', 'Align left',
        'Bring to Front', 'Send to Back', 'Lock Media', 'Replace Media', 'Reset Transform',
      ].map((name) => [name, box(item(name))])),
      dividers: [divider('ARRANGE'), divider('MEDIA')],
    }
  })

  expect(geometry.menu).toEqual({ x: 0, y: 0, width: 216, height: 462 })
  expect(geometry.sections).toEqual({
    TRANSFORM: { x: 9, y: 9, width: 200, height: 156 },
    ALIGNMENT: { x: 9, y: 165, width: 200, height: 60 },
    ARRANGE: { x: 9, y: 225, width: 200, height: 132 },
    MEDIA: { x: 9, y: 357, width: 200, height: 96 },
  })
  expect(geometry.items).toEqual({
    'Flip Horizontal': { x: 9, y: 33, width: 200, height: 36 },
    'Flip Vertical': { x: 9, y: 69, width: 200, height: 36 },
    Opacity: { x: 9, y: 105, width: 200, height: 60 },
    'Align left': { x: 17, y: 189, width: 31, height: 36 },
    'Bring to Front': { x: 9, y: 249, width: 200, height: 36 },
    'Send to Back': { x: 9, y: 285, width: 200, height: 36 },
    'Lock Media': { x: 9, y: 321, width: 200, height: 36 },
    'Replace Media': { x: 9, y: 381, width: 200, height: 36 },
    'Reset Transform': { x: 9, y: 417, width: 200, height: 36 },
  })
  expect(geometry.dividers).toEqual([
    { x: 17, y: 224, width: 184, height: 1 },
    { x: 17, y: 356, width: 184, height: 1 },
  ])
})

test('the More menu exposes six disabled alignment controls in the official row', async ({ page }) => {
  await page.setViewportSize({ width: 216, height: 462 })
  await page.goto('/?scenario=57-152')

  const menu = page.getByRole('menu', { name: 'More viewer actions' })
  const names = ['Align left', 'Align center', 'Align right', 'Align top', 'Align middle', 'Align bottom']
  const rowBox = await page.locator('.viewer-alignment-row').boundingBox()
  const boxes = []
  for (const name of names) {
    const command = menu.getByRole('menuitem', { name })
    await expect(command).toBeDisabled()
    boxes.push(await command.boundingBox())
  }

  expect(rowBox).toEqual({ x: 17, y: 189, width: 184, height: 36 })
  expect(boxes).toHaveLength(6)
  expect(boxes.every((box) => box?.y === 189 && box.height === 36)).toBe(true)
  expect(boxes.reduce((width, box) => width + (box?.width ?? 0), 0)).toBeCloseTo(184, 4)
})

test('protocol-incompatible Viewer commands stay disabled with accessible explanations', async ({ page }) => {
  await page.goto('/?scenario=1-282')

  for (const name of ['Crop', 'Rotate', 'Duplicate', 'Delete', 'Bring forward', 'Send backward']) {
    const command = page.getByRole('button', { name })
    await expect(command).toBeDisabled()
    const descriptionId = await command.getAttribute('aria-describedby')
    expect(descriptionId).toBeTruthy()
    await expect(page.locator(`#${descriptionId}`)).toContainText('not available in project protocol V1')
  }

  await page.getByRole('button', { name: 'More viewer actions' }).click()
  const menu = page.getByRole('menu', { name: 'More viewer actions' })
  for (const name of ['Bring to Front', 'Send to Back']) {
    const command = menu.getByRole('menuitem', { name })
    await expect(command).toBeDisabled()
    const descriptionId = await command.getAttribute('aria-describedby')
    expect(descriptionId).toBeTruthy()
    await expect(page.locator(`#${descriptionId}`)).toContainText('not available in project protocol V1')
  }
})

test('the populated fixture explicitly reports unavailable project video', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 688 })
  await page.goto('/?scenario=1-282')

  const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
  await expect(viewer.getByText('Project video unavailable', { exact: true })).toBeVisible()
  await expect(viewer.locator('img[src="/assets/editor/viewer-poster.png"]')).toHaveCount(0)
  await page.getByRole('button', { name: 'Aspect ratio' }).click()
  await expect(page.getByRole('menuitemradio', { name: /Original/ })).toBeChecked()
  await expect(page.getByRole('menuitemradio', { name: /9:16/ })).not.toBeChecked()
})

test('the standalone Viewer frame uses its canonical five-second project clock', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 688 })
  await page.goto('/?scenario=1-282')

  await expect(page.getByLabel('Playhead time')).toHaveText('00:00:00:00 / 00:00:05:00')
})

test('the caption Viewer frame uses its canonical twenty-second project clock', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 688 })
  await page.goto('/?scenario=123-79')

  await expect(page.getByLabel('Playhead time')).toHaveText('00:00:06:26 / 00:00:20:00')
})

test('the Viewer renders 30000/1001 timecode with an integer two-digit frame field', async ({ page }) => {
  await page.route('**/v1/projects/project_fractional/snapshot', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        snapshot: {
          read_only: true,
          errors: [],
          view: {
            project_revision: 1,
            active_sequence: 'main',
            timeline: {
              duration_s: 1.999,
              fps: { num: 30000, den: 1001 },
              clips: [{
                id: 'clip-1',
                source_range: { start_s: 0, end_s: 1.999 },
                program_range: { start_s: 0, end_s: 1.999 },
              }],
            },
          },
          resources: [],
          media: [],
          artifacts: [],
        },
      }),
    })
  })

  await page.goto('/?project=project_fractional')

  await expect(page.getByLabel('Playhead time')).toHaveText('00:00:00:00 / 00:00:01:29')
})

test('the caption selection and toolbar occupy their transcript-safe stage positions', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 688 })
  await page.goto('/?scenario=123-79')

  const [selectionBox, toolbarBox] = await Promise.all([
    page.locator('.viewer-selection-bounds--caption').boundingBox(),
    page.locator('.viewer-selection-toolbar').boundingBox(),
  ])
  expect(selectionBox).not.toBeNull()
  expect(toolbarBox).not.toBeNull()
  expect(selectionBox!.y).toBe(378)
  expect(toolbarBox!.y).toBe(324)
})
