import { expect, test } from '@playwright/test'
import { isTimeInHalfOpenRange, pxToTime, timeToPx } from '../src/editor/TimelinePanel'
import { applyTimelineEdit, trimSourceAtProgramDelta } from '../src/editor/timeline-edit'
import { getScenario } from '../src/editor/scenarios'

test('clip ranges include their start and exclude their exact end', () => {
  expect(isTimeInHalfOpenRange(4, 4, 8)).toBe(true)
  expect(isTimeInHalfOpenRange(7.999, 4, 8)).toBe(true)
  expect(isTimeInHalfOpenRange(8, 4, 8)).toBe(false)
})

test('Timeline fixture keeps visual inset out of protocol clip ranges', () => {
  const project = getScenario('1-324')?.initialState.project
  const video = project?.tracks.find((track) => track.kind === 'video')
  const audio = project?.tracks.find((track) => track.kind === 'audio')

  expect(video?.clips?.[0].programRange.startS).toBe(0)
  expect(video?.clips?.[0].sourceRange.startS).toBe(0)
  expect(audio?.clips?.[0].programRange.startS).toBe(0)
  expect(audio?.clips?.[0].sourceRange.startS).toBe(0)
})

test('Timeline renders scenario program ranges with a zoomed presentation inset', async ({ page }) => {
  const project = getScenario('1-324')?.initialState.project
  expect(project).toBeDefined()
  const expectedClips = project!.tracks
    .flatMap((track) => track.clips ?? [])
    .filter((clip) => ['video-1', 'video-2', 'audio-1'].includes(clip.id))

  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const content = page.locator('.timeline-content')
  const zoomIn = page.getByRole('button', { name: 'Zoom in timeline' })

  for (const zoom of [1, 1.5]) {
    const contentBox = await content.boundingBox()
    expect(contentBox).not.toBeNull()

    for (const clip of expectedClips) {
      const box = await page.locator(`[data-timeline-clip="${clip.id}"]`).boundingBox()
      expect(box).not.toBeNull()
      expect(box!.x).toBeCloseTo(
        contentBox!.x + 16 * zoom + timeToPx(clip.programRange.startS, project!.durationS, 876, zoom),
        1,
      )
      expect(box!.width).toBeCloseTo(
        timeToPx(clip.programRange.endS - clip.programRange.startS, project!.durationS, 876, zoom),
        1,
      )
    }

    if (zoom === 1) {
      await zoomIn.click()
      await zoomIn.click()
    }
  }
})

test('Timeline ruler draws every second across the canonical twenty-second domain', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const ticks = page.locator('[data-timeline-ruler-tick]')
  await expect(ticks).toHaveCount(21)
  await expect(ticks.nth(0)).toHaveAttribute('data-timeline-ruler-tick', '0')
  await expect(ticks.nth(20)).toHaveAttribute('data-timeline-ruler-tick', '20')
  await expect(ticks.nth(0).locator('span')).toHaveCSS('font-style', 'normal')
})

test('Timeline keeps terminal ruler and protocol clips visible without synthetic media drawings', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const ruler = page.locator('.timeline-ruler')
  const rulerScroll = page.locator('.timeline-ruler-scroll')
  const terminalTick = page.locator('[data-timeline-ruler-tick="20"]')
  const terminalLabel = terminalTick.locator('span')
  const [rulerBox, rulerScrollBox, terminalTickBox, terminalLabelBox] = await Promise.all([
    ruler.boundingBox(),
    rulerScroll.boundingBox(),
    terminalTick.boundingBox(),
    terminalLabel.boundingBox(),
  ])
  expect(rulerBox).not.toBeNull()
  expect(rulerScrollBox).not.toBeNull()
  expect(terminalTickBox).not.toBeNull()
  expect(terminalLabelBox).not.toBeNull()
  expect(terminalTickBox!.width).toBeGreaterThan(0)
  expect(terminalTickBox!.height).toBeGreaterThan(0)
  expect(terminalLabelBox!.width).toBeGreaterThan(0)
  expect(terminalLabelBox!.height).toBeGreaterThan(0)
  for (const box of [terminalTickBox!, terminalLabelBox!]) {
    expect(box.x).toBeGreaterThanOrEqual(rulerBox!.x - 1)
    expect(box.x + box.width).toBeLessThanOrEqual(rulerBox!.x + rulerBox!.width + 1)
    expect(box.x).toBeGreaterThanOrEqual(rulerScrollBox!.x - 1)
    expect(box.x + box.width).toBeLessThanOrEqual(rulerScrollBox!.x + rulerScrollBox!.width + 1)
  }
  await expect(terminalLabel).toHaveText('00:20')
  await expect(terminalLabel).toHaveCSS('font-style', 'normal')

  const firstVideo = page.locator('[data-timeline-clip="video-1"]')
  const firstVideoBox = await firstVideo.boundingBox()
  expect(firstVideoBox).not.toBeNull()
  expect(firstVideoBox!.width).toBeGreaterThan(0)
  await expect(firstVideo.locator('.timeline-clip-label')).toContainText('Unknown media')
  await expect(page.locator('.timeline-thumbnails')).toHaveCount(0)
  await expect(page.locator('.timeline-waveform')).toHaveCount(0)

  await page.goto('/?scenario=1-754')
  const selectedVideo = page.locator('[data-timeline-clip="video-2"]')
  await expect(selectedVideo).toHaveAttribute('aria-pressed', 'true')
  await expect(selectedVideo).toHaveCSS('background-color', 'rgb(41, 78, 74)')
  await expect(selectedVideo).toHaveCSS('border-color', 'rgb(121, 183, 167)')
  await expect(selectedVideo.locator('.timeline-clip-label')).toHaveCSS('background-color', 'rgb(30, 48, 52)')
  await expect(selectedVideo.locator('.timeline-clip-label')).toHaveCSS('height', '17px')
  await expect(selectedVideo.locator('.timeline-clip-speed')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Speed' }).first()).toBeDisabled()

  await page.goto('/?scenario=123-167')
  await expect(page.locator('[data-timeline-clip="caption-3"]')).toHaveCSS('box-shadow', 'rgb(255, 255, 255) 0px 0px 0px 1px inset')
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

test('timeline domain split, ripple delete, trim, and inverse commands preserve canonical ranges', () => {
  const project = getScenario('timeline-editing')!.initialState.project!
  const originalVideo = project.tracks.find((track) => track.kind === 'video')!.clips!
  const splitAtS = (originalVideo[0].programRange.startS + originalVideo[0].programRange.endS) / 2

  const split = applyTimelineEdit(project, { type: 'split', clipId: 'edit-video-1', atS: splitAtS })
  const splitVideo = split.project.tracks.find((track) => track.kind === 'video')!.clips!
  expect(splitVideo).toHaveLength(3)
  expect(splitVideo[0].sourceRange.endS).toBeCloseTo(splitVideo[1].sourceRange.startS, 8)
  expect(splitVideo[1].programRange.startS).toBeCloseTo(splitVideo[0].programRange.endS, 8)
  expect(split.project.durationS).toBeCloseTo(project.durationS, 8)

  const joined = applyTimelineEdit(split.project, split.inverse)
  expect(joined.project.tracks.find((track) => track.kind === 'video')!.clips).toEqual(originalVideo)

  const deleted = applyTimelineEdit(project, { type: 'delete', clipId: 'edit-video-1' })
  const remaining = deleted.project.tracks.find((track) => track.kind === 'video')!.clips!
  expect(remaining).toHaveLength(1)
  expect(remaining[0].programRange.startS).toBe(0)
  expect(deleted.project.durationS).toBeCloseTo(
    originalVideo[1].sourceRange.endS - originalVideo[1].sourceRange.startS,
    8,
  )
  expect(applyTimelineEdit(deleted.project, deleted.inverse).project.tracks.find((track) => track.kind === 'video')!.clips).toEqual(originalVideo)

  const restoredStart = trimSourceAtProgramDelta(project, 'edit-video-2', 'start', -5)
  expect(restoredStart).toBe(originalVideo[0].sourceRange.endS)
  const trimmed = applyTimelineEdit(project, { type: 'trim', clipId: 'edit-video-2', edge: 'start', sourceS: restoredStart! })
  expect(trimmed.project.durationS).toBeGreaterThan(project.durationS)
  expect(applyTimelineEdit(trimmed.project, trimmed.inverse).project.tracks.find((track) => track.kind === 'video')!.clips).toEqual(originalVideo)
})

test('ripple trim shifts every later track element and layer together', () => {
  const project = getScenario('timeline-editing')!.initialState.project!
  const endTrim = applyTimelineEdit(project, {
    type: 'trim', clipId: 'edit-video-1', edge: 'end', sourceS: 10,
  })
  const endCard = endTrim.project.tracks.find((track) => track.kind === 'card')!.clips![0]
  expect(endCard.programRange).toEqual({ startS: 18, endS: 20 })
  expect(endTrim.project.layers![0].programRange).toEqual({ startS: 18, endS: 20 })
  expect(endTrim.project.tracks.find((track) => track.kind === 'video')!.clips![1].programRange.startS).toBe(10)

  const startTrim = applyTimelineEdit(project, {
    type: 'trim', clipId: 'edit-video-1', edge: 'start', sourceS: 2,
  })
  const startCard = startTrim.project.tracks.find((track) => track.kind === 'card')!.clips![0]
  expect(startCard.programRange).toEqual({ startS: 14, endS: 16 })
  expect(startTrim.project.tracks.find((track) => track.kind === 'video')!.clips![1].programRange.startS).toBe(6)
})

test('deleting the final clip creates an undoable empty timeline', () => {
  const project = getScenario('timeline-editing')!.initialState.project!
  const firstDelete = applyTimelineEdit(project, { type: 'delete', clipId: 'edit-video-1' })
  const finalDelete = applyTimelineEdit(firstDelete.project, { type: 'delete', clipId: 'edit-video-2' })

  expect(finalDelete.project.durationS).toBe(0)
  expect(finalDelete.project.tracks.find((track) => track.kind === 'video')!.clips).toEqual([])

  const restored = applyTimelineEdit(finalDelete.project, finalDelete.inverse)
  expect(restored.project.tracks.find((track) => track.kind === 'video')!.clips).toEqual(
    firstDelete.project.tracks.find((track) => track.kind === 'video')!.clips,
  )
})

test('timeline selection and click seek update one store playhead', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const timeline = page.getByRole('region', { name: 'Timeline' })
  await expect(timeline).toBeVisible()
  await timeline.locator('[data-timeline-surface]').click({ position: { x: timeToPx(10, 20, 876), y: 40 } })
  await expect(page.getByLabel('Playhead time')).toContainText('00:10')

  const clip = page.locator('[data-timeline-clip="video-2"]')
  await clip.click()
  await expect(clip).toHaveAttribute('aria-pressed', 'true')
})

test('timeline context menu keeps the playhead stable and supports keyboard navigation', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=timeline-editing')

  const canvas = page.locator('[data-timeline-surface]')
  const before = await page.getByLabel('Playhead time').textContent()
  await canvas.click({ button: 'right', position: { x: 700, y: 300 } })

  const menu = page.getByRole('menu', { name: 'Timeline' })
  await expect(menu).toBeVisible()
  await expect(page.getByLabel('Playhead time')).toHaveText(before ?? '')
  await expect(menu.getByRole('menuitem', { name: /Move playhead/ })).toBeFocused()
  await page.keyboard.press('End')
  await expect(menu.getByRole('menuitem', { name: /snapping/ })).toBeFocused()
  await page.keyboard.press('Home')
  await page.keyboard.press('Enter')
  await expect(menu).toHaveCount(0)
  await expect(page.getByLabel('Playhead time')).not.toHaveText(before ?? '')

  await canvas.focus()
  await page.keyboard.press('Shift+F10')
  await expect(page.getByRole('menu', { name: 'Timeline' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('menu', { name: 'Timeline' })).toHaveCount(0)
  await expect(canvas).toBeFocused()
})

test('timeline context menu clamps to the viewport and copies its context timecode', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=timeline-editing')
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: (value: string) => { document.documentElement.dataset.copiedTimecode = value } },
    })
  })

  const canvas = page.locator('[data-timeline-surface]')
  await canvas.click({ button: 'right', position: { x: 870, y: 310 } })
  const menu = page.getByRole('menu', { name: 'Timeline' })
  const box = await menu.boundingBox()
  expect(box).not.toBeNull()
  expect(box!.x + box!.width).toBeLessThanOrEqual(1000)
  expect(box!.y + box!.height).toBeLessThanOrEqual(436)
  await menu.getByRole('menuitem', { name: 'Copy timecode' }).click()
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.copiedTimecode)).toMatch(/^00:\d{2}\.\d{3}$/)
})

test('timeline split, delete, keyboard undo, and redo form one edit history', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=timeline-editing')

  const firstClip = page.locator('[data-timeline-clip="edit-video-1"]')
  await firstClip.click()
  const firstBox = await firstClip.boundingBox()
  const surfaceBox = await page.locator('[data-timeline-surface]').boundingBox()
  expect(firstBox).not.toBeNull()
  expect(surfaceBox).not.toBeNull()
  await page.locator('[data-timeline-surface]').click({ position: {
    x: firstBox!.x + firstBox!.width / 2 - surfaceBox!.x,
    y: firstBox!.y - surfaceBox!.y + firstBox!.height / 2,
  } })
  await firstClip.click()
  await page.getByRole('button', { name: 'Split' }).click()
  await expect(page.locator('.timeline-clip--video')).toHaveCount(3)

  await page.getByRole('button', { name: 'Delete clip' }).click()
  await expect(page.locator('.timeline-clip--video')).toHaveCount(2)
  await page.keyboard.press('Control+z')
  await expect(page.locator('.timeline-clip--video')).toHaveCount(3)
  await page.keyboard.press('Control+Shift+z')
  await expect(page.locator('.timeline-clip--video')).toHaveCount(2)
})

test('deleting every clip leaves undo available and restores the final clip', async ({ page }) => {
  await page.goto('/?scenario=timeline-editing')

  for (const clipId of ['edit-video-1', 'edit-video-2']) {
    await page.locator(`[data-timeline-clip="${clipId}"]`).click()
    await page.getByRole('button', { name: 'Delete clip' }).click()
  }

  await expect(page.locator('.timeline-clip--video')).toHaveCount(0)
  await expect(page.getByText('Drag media here to start creating')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Undo' })).toBeEnabled()
  await page.getByRole('button', { name: 'Undo' }).click()
  await expect(page.locator('[data-timeline-clip="edit-video-2"]')).toBeVisible()
})

test('selected video exposes two drag handles and previews a frame-snapped ripple trim', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=timeline-editing')

  const clip = page.locator('[data-timeline-clip="edit-video-2"]')
  await clip.click()
  await expect(page.getByRole('button', { name: 'Trim clip start' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Trim clip end' })).toBeVisible()
  const before = await clip.boundingBox()
  const handle = page.getByRole('button', { name: 'Trim clip start' })
  const handleBox = await handle.boundingBox()
  expect(before).not.toBeNull()
  expect(handleBox).not.toBeNull()

  await page.mouse.move(handleBox!.x + handleBox!.width / 2, handleBox!.y + handleBox!.height / 2)
  await page.mouse.down()
  await page.mouse.move(handleBox!.x + handleBox!.width / 2 + 44, handleBox!.y + handleBox!.height / 2)
  await expect(page.locator('.timeline-trim-readout')).toContainText('In ')
  await expect(page.locator('.timeline-trim-readout')).toContainText('Duration ')
  await page.mouse.up()

  const after = await page.locator('[data-timeline-clip="edit-video-2"]').boundingBox()
  expect(after).not.toBeNull()
  expect(after!.width).toBeLessThan(before!.width)
  await page.keyboard.press('Control+z')
  const restored = await page.locator('[data-timeline-clip="edit-video-2"]').boundingBox()
  expect(restored!.width).toBeCloseTo(before!.width, 1)
})

test('dragging a video edge moves every later timeline element together', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=timeline-editing')

  const clip = page.locator('[data-timeline-clip="edit-video-1"]')
  const laterVideo = page.locator('[data-timeline-clip="edit-video-2"]')
  const laterCard = page.locator('[data-timeline-clip="edit-card-1"]')
  await clip.click()
  const handle = page.getByRole('button', { name: 'Trim clip end' })
  const handleBox = await handle.boundingBox()
  const beforeVideo = await laterVideo.boundingBox()
  const beforeCard = await laterCard.boundingBox()
  expect(handleBox).not.toBeNull()
  expect(beforeVideo).not.toBeNull()
  expect(beforeCard).not.toBeNull()

  await page.mouse.move(handleBox!.x + handleBox!.width / 2, handleBox!.y + handleBox!.height / 2)
  await page.mouse.down()
  await page.mouse.move(handleBox!.x + handleBox!.width / 2 + 44, handleBox!.y + handleBox!.height / 2)
  const previewVideo = await laterVideo.boundingBox()
  const previewCard = await laterCard.boundingBox()
  expect(previewVideo!.x - beforeVideo!.x).toBeCloseTo(previewCard!.x - beforeCard!.x, 1)
  expect(previewVideo!.x).toBeGreaterThan(beforeVideo!.x)
  await page.mouse.up()

  const savedVideo = await laterVideo.boundingBox()
  const savedCard = await laterCard.boundingBox()
  expect(savedVideo!.x - beforeVideo!.x).toBeCloseTo(savedCard!.x - beforeCard!.x, 1)
  expect(savedCard!.x).toBeGreaterThan(beforeCard!.x)
})

test('timeline seek roundtrips the playhead between the two video spans', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const surface = page.locator('[data-timeline-surface]')
  const firstVideo = await page.locator('[data-timeline-clip="video-1"]').boundingBox()
  const secondVideo = await page.locator('[data-timeline-clip="video-2"]').boundingBox()
  const surfaceBox = await surface.boundingBox()
  expect(firstVideo).not.toBeNull()
  expect(secondVideo).not.toBeNull()
  expect(surfaceBox).not.toBeNull()

  const playheadX = firstVideo!.x + firstVideo!.width + 1
  await surface.click({ position: { x: playheadX - surfaceBox!.x, y: 40 } })
  await expect(page.getByLabel('Playhead time')).toHaveText('00:06')
  const playhead = await page.locator('.timeline-playhead').boundingBox()
  expect(playhead).not.toBeNull()
  const snappedTimeS = Math.round((280 / 876 * 20) * 30) / 30
  expect(playhead!.x).toBeCloseTo(surfaceBox!.x + timeToPx(snappedTimeS, 20, 876), 1)
  expect(playhead!.x).toBeGreaterThan(firstVideo!.x + firstVideo!.width)
  expect(playhead!.x).toBeLessThan(secondVideo!.x)
})

test('timeline drag clamps at duration and zoom controls stay in bounds', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const surface = page.locator('[data-timeline-surface]')
  await surface.hover({ position: { x: 100, y: 100 } })
  await page.mouse.down()
  await page.mouse.move(1200, 100)
  await page.mouse.up()
  await expect(page.getByLabel('Playhead time')).toContainText('00:20')

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
  await surface.evaluate((element) => {
    element.scrollLeft = 240
    element.dispatchEvent(new Event('scroll'))
  })

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

test('zoom scales adjacent clip ranges in the ruler and playhead coordinate system', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const content = page.locator('.timeline-content')
  const ruler = page.locator('.timeline-ruler')
  const playhead = page.locator('.timeline-playhead')
  const clips = page.locator('.timeline-clip--video')
  const zoomIn = page.getByRole('button', { name: 'Zoom in timeline' })

  await zoomIn.click()
  await zoomIn.click()

  const [contentBox, rulerBox, playheadBox, firstClip, secondClip] = await Promise.all([
    content.boundingBox(),
    ruler.boundingBox(),
    playhead.boundingBox(),
    clips.nth(0).boundingBox(),
    clips.nth(1).boundingBox(),
  ])
  expect(contentBox).not.toBeNull()
  expect(rulerBox).not.toBeNull()
  expect(playheadBox).not.toBeNull()
  expect(firstClip).not.toBeNull()
  expect(secondClip).not.toBeNull()
  expect(rulerBox!.x).toBeCloseTo(contentBox!.x, 0)
  expect(rulerBox!.width).toBeCloseTo(876 * 1.5, 0)
  expect(playheadBox!.x - contentBox!.x).toBeCloseTo(280 * 1.5, 2)
  expect(firstClip!.x - contentBox!.x).toBeCloseTo(16 * 1.5, 2)
  expect(firstClip!.width).toBeCloseTo(263 * 1.5, 2)
  expect(secondClip!.x - contentBox!.x).toBeCloseTo(283 * 1.5, 2)
  expect(secondClip!.x).toBeGreaterThan(playheadBox!.x)
  expect(secondClip!.x + secondClip!.width - contentBox!.x).toBeCloseTo(796 * 1.5, 2)
})

test('selected Timeline scenario initializes its second video span as selected', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-754')

  await expect(page.locator('[data-timeline-clip="video-2"]')).toHaveAttribute('aria-pressed', 'true')
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

test('an unselected caption track keeps its real lane and cues before video', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  const captionBox = await page.getByText('C1', { exact: true }).boundingBox()
  const videoBox = await page.getByText('V1', { exact: true }).boundingBox()
  expect(captionBox).not.toBeNull()
  expect(videoBox).not.toBeNull()
  expect(captionBox!.y).toBeLessThan(videoBox!.y)
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

test('the populated Timeline fixture renders its two source spans on the twenty-second ruler', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=1-324')

  await expect(page.locator('.timeline-ruler span').last()).toHaveText('00:20')
  const clips = page.locator('.timeline-clip--video')
  await expect(clips).toHaveCount(2)

  const [firstVideo, secondVideo, audio] = await Promise.all([
    clips.nth(0).boundingBox(),
    clips.nth(1).boundingBox(),
    page.locator('[data-timeline-clip="audio-1"]').boundingBox(),
  ])
  expect(firstVideo).toMatchObject({ x: 148, height: 80 })
  expect(firstVideo?.width).toBeCloseTo(263, 1)
  expect(secondVideo).toMatchObject({ y: firstVideo?.y, height: 80 })
  expect(secondVideo?.x).toBeCloseTo(415, 1)
  expect(secondVideo?.width).toBeCloseTo(513, 1)
  expect(secondVideo!.x - (firstVideo!.x + firstVideo!.width)).toBeCloseTo(4, 1)
  expect(audio).toMatchObject({ x: 148, height: 60 })
  expect(audio!.y).toBeGreaterThan(firstVideo!.y + firstVideo!.height)
  expect(audio?.width).toBeCloseTo(780, 1)
  expect(1008 - (audio!.x + audio!.width)).toBeCloseTo(80, 1)
})

test('the caption Timeline fixture preserves its measured lane hierarchy', async ({ page }) => {
  await page.setViewportSize({ width: 1008, height: 444 })
  await page.goto('/?scenario=123-167')

  const [caption, video, audio] = await Promise.all([
    page.locator('.timeline-lane--caption').boundingBox(),
    page.locator('.timeline-lane--video').boundingBox(),
    page.locator('.timeline-lane--audio').boundingBox(),
  ])
  expect(caption?.height).toBe(64)
  expect(video?.height).toBe(108)
  expect(audio?.height).toBe(76)
  expect(video?.y).toBe(caption!.y + caption!.height)
  expect(audio?.y).toBe(video!.y + video!.height)
  await expect(page.locator('[data-timeline-clip="caption-3"]')).toHaveAttribute('aria-pressed', 'true')
})
