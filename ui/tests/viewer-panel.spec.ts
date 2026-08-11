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

test('protocol-incompatible Viewer commands stay disabled with accessible explanations', async ({ page }) => {
  await page.goto('/?scenario=1-282')

  for (const name of ['Crop', 'Rotate', 'Duplicate', 'Delete', 'Bring forward', 'Send backward']) {
    const command = page.getByRole('button', { name })
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
