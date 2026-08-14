import { expect, test } from '@playwright/test'
import {
  createPlaybackController,
  lastPresentedSourceTime,
  nativeBoundaryDelayMs,
  nativeBoundaryWakeup,
} from '../src/editor/ViewerPanel'
import type { ClipView } from '../src/editor/editor-model'

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
