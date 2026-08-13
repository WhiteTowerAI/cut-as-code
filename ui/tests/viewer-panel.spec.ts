import { expect, test } from '@playwright/test'
import { createPlaybackController } from '../src/editor/ViewerPanel'

test('play and pause use the single Viewer playback control', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 688 })
  await page.goto('/?scenario=1-282')

  const play = page.getByRole('button', { name: 'Play' })
  await expect(play).toBeVisible()
  await play.click()

  const pause = page.getByRole('button', { name: 'Pause' })
  await expect(pause).toBeVisible()
  await pause.click()
  await expect(play).toBeVisible()
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

test('the populated preview renders real nonblank local pixels', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 688 })
  await page.goto('/?scenario=1-282')

  const preview = page.locator('[data-preview-media]')
  await expect(preview).toBeVisible()
  await expect(preview).toHaveAttribute('src', /\/fixtures\//)
  const sample = await preview.evaluate((element) => {
    const image = element as HTMLImageElement
    const canvas = document.createElement('canvas')
    canvas.width = 8
    canvas.height = 8
    const context = canvas.getContext('2d', { willReadFrequently: true })!
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
    const colors = new Set<string>()
    let nonTransparent = 0
    for (let index = 0; index < pixels.length; index += 4) {
      colors.add(`${pixels[index]},${pixels[index + 1]},${pixels[index + 2]}`)
      if (pixels[index + 3] > 0) nonTransparent += 1
    }
    return { colorCount: colors.size, nonTransparent }
  })

  expect(sample.nonTransparent).toBe(64)
  expect(sample.colorCount).toBeGreaterThan(4)
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
