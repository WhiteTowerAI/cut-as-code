import { expect, test } from '@playwright/test'

test('loads the local Inter faces used by the Library typography', async ({ page }) => {
  await page.goto('/?scenario=18-3')

  const typography = await page.evaluate(async () => {
    await document.fonts.ready
    const loadedWeights: number[] = []
    document.fonts.forEach((face) => {
      if (face.family.replaceAll('"', '') === 'Inter' && face.status === 'loaded') {
        loadedWeights.push(Number(face.weight))
      }
    })
    return {
      family: getComputedStyle(document.querySelector('.library-panel')!).fontFamily,
      loadedWeights: loadedWeights.sort((left, right) => left - right),
    }
  })

  expect(typography).toEqual({
    family: 'Inter, ui-sans-serif, system-ui, sans-serif',
    loadedWeights: [400, 500, 600],
  })
})

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
  expect(dimensions.scrollWidth).toBe(dimensions.clientWidth)
  await expect(page.getByRole('tab', { name: 'Transcript' })).toHaveCount(0)
})

test('selects a project-backed asset by its canonical ID', async ({ page }) => {
  await page.goto('/?scenario=1-84')

  const asset = page.locator('[data-asset-id="asset-product"]')
  await expect(asset).toContainText('Product teaser.mov')
  await expect(asset).toHaveAttribute('aria-pressed', 'false')

  await asset.click()

  await expect(asset).toHaveAttribute('aria-pressed', 'true')
})

test.skip('project-backed previews use nonblank frozen local artwork', async ({ page }) => {
  await page.goto('/?scenario=1-84')

  const previews = page.locator('[data-asset-id] img[data-library-preview]')
  await expect(previews).toHaveCount(4)
  for (const preview of await previews.all()) {
    await expect(preview).toHaveAttribute('src', /^\/assets\/editor\/[a-z-]+\.png$/)
    const sample = await preview.evaluate(async (element) => {
      const image = element as HTMLImageElement
      if (!image.complete) await image.decode()
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
      const imageBox = image.getBoundingClientRect()
      const cardBox = image.closest('[data-asset-id]')!.getBoundingClientRect()
      return {
        naturalWidth: image.naturalWidth,
        naturalHeight: image.naturalHeight,
        renderedWidth: imageBox.width,
        renderedHeight: imageBox.height,
        leftInset: imageBox.left - cardBox.left,
        topInset: imageBox.top - cardBox.top,
        nonTransparent,
        colors: colors.size,
      }
    })
    expect(sample.naturalWidth).toBeGreaterThan(0)
    expect(sample.naturalHeight).toBeGreaterThan(0)
    expect(sample.renderedWidth).toBe(144)
    expect(sample.renderedHeight).toBe(96)
    expect(sample.leftInset).toBe(0)
    expect(sample.topInset).toBe(0)
    expect(sample.nonTransparent).toBe(64)
    expect(sample.colors).toBeGreaterThan(2)
  }
})

test('project-backed asset rows keep the reference 16 pixel gap', async ({ page }) => {
  await page.goto('/?scenario=1-84')

  const rowOffsets = await page.locator('[data-asset-id]').evaluateAll((elements) => {
    const tops = elements.map((element) => element.getBoundingClientRect().top)
    return tops.map((top) => top - tops[0])
  })

  expect(rowOffsets).toEqual([0, 0, 134, 134])
})

test.skip('caption and content-card previews use frozen official child artwork', async ({ page }) => {
  await page.goto('/?scenario=123-2')

  for (const { tab, count, prefix } of [
    { tab: 'Captions', count: 7, prefix: 'caption' },
    { tab: 'Cards', count: 6, prefix: 'card' },
  ] as const) {
    await page.getByRole('tab', { name: tab }).click()
    const previews = page.locator('.library-tile img[data-library-preview]')
    await expect(previews).toHaveCount(count)

    for (const preview of await previews.all()) {
      await expect(preview).toHaveAttribute('src', new RegExp(`^/assets/editor/${prefix}-[a-z-]+\\.png$`))
      expect(await preview.evaluate((element) => element.parentElement!.children.length)).toBe(1)
      const sample = await preview.evaluate(async (element) => {
        const image = element as HTMLImageElement
        if (!image.complete) await image.decode()
        const canvas = document.createElement('canvas')
        canvas.width = 8
        canvas.height = 8
        const context = canvas.getContext('2d', { willReadFrequently: true })!
        context.drawImage(image, 0, 0, canvas.width, canvas.height)
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
        const colors = new Set<string>()
        for (let index = 0; index < pixels.length; index += 4) {
          colors.add(`${pixels[index]},${pixels[index + 1]},${pixels[index + 2]},${pixels[index + 3]}`)
        }
        const imageBox = image.getBoundingClientRect()
        const cardBox = image.closest('.library-tile')!.getBoundingClientRect()
        return {
          naturalWidth: image.naturalWidth,
          naturalHeight: image.naturalHeight,
          renderedWidth: imageBox.width,
          renderedHeight: imageBox.height,
          leftInset: imageBox.left - cardBox.left,
          topInset: imageBox.top - cardBox.top,
          colors: colors.size,
        }
      })
      expect(sample).toMatchObject({
        naturalWidth: 144,
        naturalHeight: 50,
        renderedWidth: 144,
        renderedHeight: 50,
        leftInset: 0,
        topInset: 0,
      })
      expect(sample.colors).toBeGreaterThan(2)
    }
  }
})

test.skip('content-card controls match the official vertical geometry', async ({ page }) => {
  await page.goto('/?scenario=126-2')

  const geometry = await page.locator('.library-content').evaluate((content) => {
    const contentBox = content.getBoundingClientRect()
    const relativeBox = (selector: string) => {
      const box = content.querySelector(selector)!.getBoundingClientRect()
      return { top: box.top - contentBox.top, height: box.height }
    }
    return {
      grid: relativeBox('.library-grid'),
      placement: relativeBox('.placement-control'),
      options: relativeBox('.placement-options'),
      action: relativeBox('.library-primary-action'),
    }
  })

  expect(geometry).toEqual({
    grid: { top: 58, height: 236 },
    placement: { top: 308, height: 50 },
    options: { top: 330, height: 28 },
    action: { top: 382, height: 36 },
  })
})

test.skip('caption theme controls match the official panel geometry', async ({ page }) => {
  await page.goto('/?scenario=123-2')

  const geometry = await page.locator('.library-panel').evaluate((panel) => {
    const panelBox = panel.getBoundingClientRect()
    const relativeBox = (selector: string) => {
      const box = panel.querySelector(selector)!.getBoundingClientRect()
      return {
        left: Math.round(box.left - panelBox.left),
        top: Math.round(box.top - panelBox.top),
        width: box.width,
        height: box.height,
      }
    }
    return {
      firstSwatch: relativeBox('.theme-swatch'),
      toggle: relativeBox('.word-highlight-row input'),
    }
  })

  expect(geometry).toEqual({
    firstSwatch: { left: 62, top: 427, width: 18, height: 18 },
    toggle: { left: 272, top: 466, width: 36, height: 20 },
  })
})

test.skip('keeps Graphic Motion discoverable in the compact four-tab strip', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 688 })
  await page.goto('/?scenario=1-84')

  const tablist = page.getByRole('tablist', { name: 'Library sections' })
  const assets = page.getByRole('tab', { name: 'My Assets' })
  const motion = page.getByRole('tab', { name: 'Graphic Motion' })
  const tabGeometry = () => tablist.evaluate((node) => {
    const listBox = node.getBoundingClientRect()
    const relativeBox = (tab: string) => {
      const box = node.querySelector<HTMLElement>(`[data-tab="${tab}"]`)!.getBoundingClientRect()
      return {
        left: Math.round(box.left - listBox.left + node.scrollLeft),
        width: Math.round(box.width),
      }
    }
    return {
      scrollLeft: Math.round(node.scrollLeft),
      clientWidth: node.clientWidth,
      scrollWidth: node.scrollWidth,
      assets: relativeBox('assets'),
      captions: relativeBox('captions'),
      cards: relativeBox('cards'),
      motion: relativeBox('graphic-motion'),
    }
  })
  const selectedTabViewport = () => tablist.evaluate((node) => {
    const listBox = node.getBoundingClientRect()
    const selectedBox = node.querySelector<HTMLElement>('[aria-selected="true"]')!.getBoundingClientRect()
    return {
      scrollLeft: Math.round(node.scrollLeft),
      left: Math.round(selectedBox.left - listBox.left),
      right: Math.round(selectedBox.right - listBox.left),
      clientWidth: node.clientWidth,
    }
  })

  expect(await tabGeometry()).toEqual({
    scrollLeft: 0,
    clientWidth: 296,
    scrollWidth: 296,
    assets: { left: 0, width: 72 },
    captions: { left: 76, width: 64 },
    cards: { left: 143, width: 47 },
    motion: { left: 195, width: 98 },
  })

  await motion.evaluate((element) => element.click())
  await expect(motion).toHaveAttribute('aria-selected', 'true')
  await expect.poll(selectedTabViewport).toEqual({ scrollLeft: 0, left: 195, right: 292, clientWidth: 296 })

  await assets.evaluate((element) => element.click())
  await expect(assets).toHaveAttribute('aria-selected', 'true')
  await expect.poll(() => tablist.evaluate((node) => Math.round(node.scrollLeft))).toBe(0)

  await assets.focus()
  await page.keyboard.press('End')
  await expect(motion).toBeFocused()
  await expect.poll(selectedTabViewport).toEqual({ scrollLeft: 0, left: 195, right: 292, clientWidth: 296 })

  await page.keyboard.press('Home')
  await expect(assets).toBeFocused()
  await expect.poll(() => tablist.evaluate((node) => Math.round(node.scrollLeft))).toBe(0)
})

test.skip('keeps Graphic Motion discoverable in the workspace Library', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1200 })
  await page.goto('/?scenario=1-1373')

  const tablist = page.getByRole('tablist', { name: 'Library sections' })
  const geometry = await tablist.evaluate((node) => {
    const listBox = node.getBoundingClientRect()
    const motionBox = node.querySelector<HTMLElement>('[data-tab="graphic-motion"]')!.getBoundingClientRect()
    return {
      scrollLeft: Math.round(node.scrollLeft),
      clientWidth: node.clientWidth,
      motionLeft: Math.round(motionBox.left - listBox.left),
    }
  })

  expect(geometry).toEqual({ scrollLeft: 0, clientWidth: 296, motionLeft: 195 })
})

test('expands the empty workspace drop zone to the Library content width', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1200 })
  await page.goto('/?scenario=1-1373')

  const geometry = await page.locator('.library-content').evaluate((content) => {
    const contentBox = content.getBoundingClientRect()
    const dropzoneBox = content.querySelector('.asset-dropzone')!.getBoundingClientRect()
    return {
      contentWidth: contentBox.width,
      dropzoneLeft: Math.round(dropzoneBox.left - contentBox.left),
      dropzoneWidth: dropzoneBox.width,
      dropzoneRight: Math.round(contentBox.right - dropzoneBox.right),
    }
  })

  expect(geometry.contentWidth).toBeGreaterThan(300)
  expect(geometry.dropzoneLeft).toBe(12)
  expect(geometry.dropzoneRight).toBe(12)
  expect(geometry.dropzoneWidth).toBeCloseTo(geometry.contentWidth - 24, 1)
})

test.skip('switches the single library panel across all four tabs', async ({ page }) => {
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
  expect(await page.getByRole('tablist', { name: 'Library sections' }).evaluate((node) => node.scrollLeft)).toBe(0)

  await assets.click()
  await expect(assets).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByPlaceholder('Search assets')).toBeVisible()
})

test.skip('moves tab focus and selection with the keyboard', async ({ page }) => {
  await page.goto('/?scenario=1-84')

  const assets = page.getByRole('tab', { name: 'My Assets' })
  const captions = page.getByRole('tab', { name: 'Captions' })
  const cards = page.getByRole('tab', { name: 'Cards' })
  const motion = page.getByRole('tab', { name: 'Graphic Motion' })

  for (const tab of [assets, captions, cards, motion]) {
    const panelId = await tab.getAttribute('aria-controls')
    expect(panelId).toBeTruthy()
    await expect(page.locator(`#${panelId}`)).toHaveCount(1)
  }

  const tabPanel = page.getByRole('tabpanel')
  await expect(assets).toHaveAttribute('id', 'library-tab-assets')
  await expect(tabPanel).toHaveAttribute('aria-labelledby', 'library-tab-assets')

  await assets.focus()
  await page.keyboard.press('ArrowRight')
  await expect(captions).toBeFocused()
  await expect(captions).toHaveAttribute('aria-selected', 'true')
  expect(await captions.evaluate((element) => getComputedStyle(element).boxShadow)).not.toBe('none')
  await expect(tabPanel).toHaveAttribute('aria-labelledby', 'library-tab-captions')

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

test('keeps only My Assets visible and does not synthesize asset previews', async ({ page }) => {
  await page.goto('/?scenario=1-84')

  await expect(page.getByRole('tab', { name: 'My Assets' })).toHaveCount(1)
  await expect(page.getByRole('tab', { name: 'Captions' })).toHaveCount(0)
  await expect(page.getByRole('tab', { name: 'Cards' })).toHaveCount(0)
  await expect(page.getByRole('tab', { name: 'Graphic Motion' })).toHaveCount(0)
  await expect(page.locator('[data-asset-id] [data-library-preview]')).toHaveCount(0)
})
