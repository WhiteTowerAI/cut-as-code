import { expect, test } from '@playwright/test'
import { isTimeInHalfOpenRange, pxToTime, timeToPx } from '../src/editor/TimelinePanel'

test('clip ranges include their start and exclude their exact end', () => {
  expect(isTimeInHalfOpenRange(4, 4, 8)).toBe(true)
  expect(isTimeInHalfOpenRange(7.999, 4, 8)).toBe(true)
  expect(isTimeInHalfOpenRange(8, 4, 8)).toBe(false)
})

test('time and pixel mapping clamps the half-open timeline range', () => {
  expect(timeToPx(-2, 20, 876)).toBe(0)
  expect(timeToPx(10, 20, 876)).toBe(438)
  expect(timeToPx(30, 20, 876)).toBe(876)
  expect(pxToTime(-10, 20, 876)).toBe(0)
  expect(pxToTime(438, 20, 876)).toBe(10)
  expect(pxToTime(999, 20, 876)).toBe(20)
})

test('pixel mapping snaps seeks to rational FPS only when snap is enabled', () => {
  const fps = { numerator: 30000, denominator: 1001 }
  const raw = (100 / 876) * 20
  const frame = 1001 / 30000
  expect(pxToTime(100, 20, 876, { fps, snapEnabled: true })).toBeCloseTo(Math.round(raw / frame) * frame, 8)
  expect(pxToTime(100, 20, 876, { fps, snapEnabled: false })).toBeCloseTo(raw, 8)
})

test('timeline selection and click seek update one store playhead', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const timeline = page.getByRole('region', { name: 'Timeline' })
  await expect(timeline).toBeVisible()
  await timeline.locator('[data-timeline-surface]').click({ position: { x: 438, y: 40 } })
  await expect(page.getByLabel('Playhead time')).toContainText('01:03')

  const clip = page.locator('[data-timeline-clip="track-video"]')
  await clip.click()
  await expect(clip).toHaveAttribute('aria-pressed', 'true')
})

test('timeline drag clamps at duration and zoom controls stay in bounds', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const surface = page.locator('[data-timeline-surface]')
  await surface.hover({ position: { x: 100, y: 100 } })
  await page.mouse.down()
  await page.mouse.move(1200, 100)
  await page.mouse.up()
  await expect(page.getByLabel('Playhead time')).toContainText('02:07')

  const zoomIn = page.getByRole('button', { name: 'Zoom in timeline' })
  const zoomOut = page.getByRole('button', { name: 'Zoom out timeline' })
  while (await zoomIn.isEnabled()) await zoomIn.click()
  await expect(zoomIn).toBeDisabled()
  while (await zoomOut.isEnabled()) await zoomOut.click()
  await expect(zoomOut).toBeDisabled()
})

test('zoomed horizontal scroll keeps ruler content and playhead on one scale', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const surface = page.locator('[data-timeline-surface]')
  const ruler = page.locator('.timeline-ruler')
  const content = page.locator('.timeline-content')
  const playhead = page.locator('.timeline-playhead')
  const zoomIn = page.getByRole('button', { name: 'Zoom in timeline' })
  const zoomOut = page.getByRole('button', { name: 'Zoom out timeline' })

  await zoomIn.click()
  await zoomIn.click()
  await surface.evaluate((element) => { element.scrollLeft = 240 })

  const [rulerBox, contentBox, playheadBox] = await Promise.all([
    ruler.boundingBox(),
    content.boundingBox(),
    playhead.boundingBox(),
  ])
  expect(rulerBox).not.toBeNull()
  expect(contentBox).not.toBeNull()
  expect(playheadBox).not.toBeNull()
  expect(rulerBox!.x).toBeCloseTo(contentBox!.x, 0)
  expect(rulerBox!.width).toBeCloseTo(contentBox!.width, 0)
  expect(playheadBox!.x - rulerBox!.x).toBeCloseTo(playheadBox!.x - contentBox!.x, 0)

  await page.getByRole('button', { name: 'Fit timeline' }).click()
  await zoomOut.click()
  await zoomOut.click()
  await expect(ruler).toHaveCSS('width', await content.evaluate((element) => getComputedStyle(element).width))
})

test('unsupported timeline commands remain disabled with explanations', async ({ page }) => {
  await page.goto('/?scenario=1-324')
  for (const name of ['Reverse', 'Duplicate', 'Copy', 'Reorder tracks', 'Speed']) {
    const command = page.getByRole('button', { name }).first()
    await expect(command).toBeDisabled()
    const descriptionId = await command.getAttribute('aria-describedby')
    expect(descriptionId).toBeTruthy()
    await expect(page.locator(`#${descriptionId}`)).toContainText('not available in project protocol V1')
  }
})

test('caption timeline renders its lane before video without reordering project state', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=123-167')

  const captionBox = await page.getByText('C1', { exact: true }).boundingBox()
  const videoBox = await page.getByText('V1', { exact: true }).boundingBox()
  expect(captionBox).not.toBeNull()
  expect(videoBox).not.toBeNull()
  expect(captionBox!.y).toBeLessThan(videoBox!.y)
})

test('an unselected caption track keeps its reserved lane before video', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  await expect(page.getByText('C1', { exact: true })).toHaveCount(0)
  const videoBox = await page.getByText('V1', { exact: true }).boundingBox()
  expect(videoBox).not.toBeNull()
  expect(videoBox!.y).toBeGreaterThanOrEqual(160)
})

test('an empty timeline omits the ruler and uses its narrow media gutter', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-1115')

  const timeline = page.getByRole('region', { name: 'Timeline' })
  await expect(timeline.locator('.timeline-ruler')).toHaveCount(0)
  const [gutterBox, surfaceBox, emptyBox] = await Promise.all([
    timeline.locator('.timeline-gutter').boundingBox(),
    timeline.locator('[data-timeline-surface]').boundingBox(),
    timeline.getByText('Drag media here to start creating').locator('..').boundingBox(),
  ])
  expect(gutterBox).not.toBeNull()
  expect(surfaceBox).not.toBeNull()
  expect(emptyBox).not.toBeNull()
  expect(gutterBox!.width).toBe(48)
  expect(surfaceBox!.x).toBe(48)
  expect(surfaceBox!.width).toBe(960)
  expect(emptyBox!.x).toBe(48)
  expect(emptyBox!.width).toBe(912)
})

test('the caption Timeline frame uses the same canonical twenty-second project clock', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=123-167')

  await expect(page.getByLabel('Playhead time')).toHaveText('00:06')
  await expect(page.locator('.timeline-ruler span').last()).toHaveText('00:20')
})
