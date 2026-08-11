import { expect, test } from '@playwright/test'

test('renders the populated asset library at the approved panel size', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 688 })
  await page.goto('/?scenario=1-84')

  const panel = page.getByRole('region', { name: 'Library' })
  await expect(panel).toBeVisible()
  await expect(panel).toHaveCSS('width', '320px')
  await expect(panel).toHaveCSS('height', '688px')
  await expect(page.getByText('Product teaser.mov', { exact: true })).toBeVisible()
  await expect(page.getByText('Founder interview.mp4', { exact: true })).toBeVisible()

  const tabList = page.getByRole('tablist', { name: 'Library sections' })
  const dimensions = await tabList.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
  }))
  expect(dimensions.clientWidth).toBe(296)
  expect(dimensions.scrollWidth).toBeGreaterThan(dimensions.clientWidth)
  await expect(page.getByRole('tab', { name: 'Transcript' })).toHaveCount(0)
})

test('switches the single library panel across all four tabs', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 688 })
  await page.goto('/?scenario=1-84')

  const assets = page.getByRole('tab', { name: 'My Assets' })
  const captions = page.getByRole('tab', { name: 'Captions' })
  const cards = page.getByRole('tab', { name: 'Cards' })
  const motion = page.getByRole('tab', { name: 'Graphic Motion' })

  await expect(assets).toHaveAttribute('aria-selected', 'true')

  await captions.click()
  await expect(captions).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByPlaceholder('Search caption styles')).toBeVisible()
  await expect(page.getByText('Social bold', { exact: true })).toBeVisible()

  await cards.click()
  await expect(cards).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByPlaceholder('Search content cards')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Insert content card' })).toBeVisible()

  await motion.click()
  await expect(motion).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByPlaceholder('Search motion recipes')).toBeVisible()
  await expect(page.getByText('XYZ Fade Up', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Insert motion' })).toBeVisible()
  expect(await page.getByRole('tablist', { name: 'Library sections' }).evaluate((node) => node.scrollLeft)).toBeGreaterThan(0)

  await assets.click()
  await expect(assets).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByPlaceholder('Search assets')).toBeVisible()
})

test('moves tab focus and selection with the keyboard', async ({ page }) => {
  await page.goto('/?scenario=1-84')

  const assets = page.getByRole('tab', { name: 'My Assets' })
  const captions = page.getByRole('tab', { name: 'Captions' })
  const motion = page.getByRole('tab', { name: 'Graphic Motion' })

  await assets.focus()
  await page.keyboard.press('ArrowRight')
  await expect(captions).toBeFocused()
  await expect(captions).toHaveAttribute('aria-selected', 'true')

  await page.keyboard.press('End')
  await expect(motion).toBeFocused()
  await expect(motion).toHaveAttribute('aria-selected', 'true')

  await page.keyboard.press('Home')
  await expect(assets).toBeFocused()
  await expect(assets).toHaveAttribute('aria-selected', 'true')
})

test('renders the empty asset drop zone from the empty scenario', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 688 })
  await page.goto('/?scenario=18-3')

  await expect(page.getByRole('button', { name: 'Import media' })).toBeVisible()
  await expect(page.getByText('Drag and drop videos, photos, and audio files here')).toBeVisible()
  await expect(page.getByText('MP4, MOV, WebM, MP3, WAV, JPG, PNG')).toBeVisible()
  await expect(page.getByText('Product teaser.mov', { exact: true })).toHaveCount(0)
})
