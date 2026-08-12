import { expect, test, type Page } from '@playwright/test'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const STRICT_DIFF_RATIO_THRESHOLD = 0.01
const PIXEL_CHANNEL_TOLERANCE = 16
const SCREENSHOT_DIR = resolve(process.cwd(), 'tests', 'screenshots')

type Dimensions = Readonly<{ width: number; height: number }>

type FigmaScenario = Readonly<{
  nodeId: string
  scenarioId: string
  viewport: Dimensions
  referenceCrop: Readonly<{ x: number; y: number }>
}>

type ComparisonResult = Readonly<{
  label: 'figma-match' | 'user-extension'
  nodeId: string | null
  scenarioId: string
  viewport: Dimensions
  reference: Dimensions | null
  referenceCompared: Readonly<{
    dimensions: Dimensions
    crop: Readonly<{ x: number; y: number }>
  }> | null
  browser: Dimensions
  differentPixels: number | null
  totalPixels: number | null
  diffRatio: number | null
  threshold: number | null
  pixelChannelTolerance: number | null
  verdict: 'pass' | 'fail' | 'baseline'
  artifacts: Readonly<{
    referenceRaw: string | null
    referenceCompared: string | null
    browser: string
    diff: string | null
    result: string
  }>
}>

const figmaScenarios: readonly FigmaScenario[] = [
  { nodeId: '1:60', scenarioId: '1-60', viewport: { width: 1440, height: 1200 }, referenceCrop: { x: 0, y: 0 } },
  { nodeId: '1:1373', scenarioId: '1-1373', viewport: { width: 1440, height: 1200 }, referenceCrop: { x: 0, y: 0 } },
  { nodeId: '1:84', scenarioId: '1-84', viewport: { width: 320, height: 688 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '1:282', scenarioId: '1-282', viewport: { width: 680, height: 688 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '57:152', scenarioId: '57-152', viewport: { width: 216, height: 462 }, referenceCrop: { x: 18, y: 10 } },
  { nodeId: '1:1026', scenarioId: '1-1026', viewport: { width: 680, height: 688 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '1:324', scenarioId: '1-324', viewport: { width: 1008, height: 444 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '1:1115', scenarioId: '1-1115', viewport: { width: 1008, height: 444 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '1:754', scenarioId: '1-754', viewport: { width: 1008, height: 444 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '1:528', scenarioId: '1-528', viewport: { width: 280, height: 321 }, referenceCrop: { x: 16, y: 8 } },
  { nodeId: '18:3', scenarioId: '18-3', viewport: { width: 320, height: 688 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '76:2', scenarioId: '76-2', viewport: { width: 1785, height: 1746 }, referenceCrop: { x: 0, y: 0 } },
  { nodeId: '123:2', scenarioId: '123-2', viewport: { width: 320, height: 688 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '123:79', scenarioId: '123-79', viewport: { width: 680, height: 688 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '123:167', scenarioId: '123-167', viewport: { width: 1008, height: 444 }, referenceCrop: { x: 12, y: 8 } },
  { nodeId: '126:2', scenarioId: '126-2', viewport: { width: 320, height: 688 }, referenceCrop: { x: 12, y: 8 } },
] as const

const geometryScenarios: readonly Readonly<{ scenarioId: string; viewport: Dimensions }>[] = [
  ...figmaScenarios.map(({ scenarioId, viewport }) => ({ scenarioId, viewport })),
  { scenarioId: 'graphic-motion', viewport: { width: 320, height: 688 } },
]

mkdirSync(SCREENSHOT_DIR, { recursive: true })

function artifactName(label: string, scenarioId: string, kind: string, extension: 'png' | 'json') {
  return `${label}-${scenarioId}-${kind}.${extension}`
}

test('visual comparison artifacts retain the raw reference and the exact compared reference', () => {
  const result = JSON.parse(
    readFileSync(resolve(SCREENSHOT_DIR, artifactName('figma', '1-84', 'result', 'json')), 'utf8'),
  ) as ComparisonResult

  expect(result.artifacts.referenceRaw).toBe('figma-1-84-reference.png')
  expect(result.artifacts.referenceCompared).toBe('figma-1-84-reference-compared.png')
  expect(existsSync(resolve(SCREENSHOT_DIR, result.artifacts.referenceCompared))).toBe(true)
})

function writeResult(result: ComparisonResult) {
  writeFileSync(
    resolve(SCREENSHOT_DIR, result.artifacts.result),
    `${JSON.stringify(result, null, 2)}\n`,
    'utf8',
  )
  writeAggregateResults()
}

function writeAggregateResults() {
  const resultFiles = [
    ...figmaScenarios.map((scenario) => artifactName('figma', scenario.scenarioId, 'result', 'json')),
    artifactName('user-extension', 'graphic-motion', 'result', 'json'),
  ]
  const aggregateResults = resultFiles
    .filter((file) => existsSync(resolve(SCREENSHOT_DIR, file)))
    .map((file) => JSON.parse(readFileSync(resolve(SCREENSHOT_DIR, file), 'utf8')) as ComparisonResult)

  writeFileSync(
    resolve(SCREENSHOT_DIR, 'visual-comparison-results.json'),
    `${JSON.stringify({
      generatedAt: new Date().toISOString(),
      strictDiffRatioThreshold: STRICT_DIFF_RATIO_THRESHOLD,
      pixelChannelTolerance: PIXEL_CHANNEL_TOLERANCE,
      results: aggregateResults,
    }, null, 2)}\n`,
    'utf8',
  )
}

async function settleVisuals(page: Page) {
  await page.evaluate(() => document.fonts.ready)
  await page.addStyleTag({
    content: '*, *::before, *::after { animation: none !important; transition: none !important; caret-color: transparent !important; }',
  })
}

async function geometryFailures(page: Page, scenarioId: string) {
  return page.evaluate((currentScenarioId) => {
    const failures: string[] = []
    const leafSelector = [
      'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label', 'output', 'button',
      '[role="tab"]', '[role="menuitem"]', '.timeline-clip-label',
      '.timeline-caption-cue', '[class*="library-"]',
    ].join(', ')
    const overlapGroups = [
      '.library-tabs [role="tab"]',
      '.viewer-menu [role="menuitem"]',
      '.viewer-aspect-option',
      '.timeline-caption-cue',
      '.timeline-clip-label, .timeline-clip-speed',
    ]
    const isVisible = (element: HTMLElement) => {
      const style = getComputedStyle(element)
      const rect = element.getBoundingClientRect()
      return style.display !== 'none'
        && style.visibility !== 'hidden'
        && Number(style.opacity) !== 0
        && !element.closest('.sr-only, [aria-hidden="true"]')
        && rect.width > 0
        && rect.height > 0
        && rect.right > 0
        && rect.bottom > 0
        && rect.left < window.innerWidth
        && rect.top < window.innerHeight
    }
    const description = (element: HTMLElement) => {
      const className = typeof element.className === 'string' && element.className
        ? `.${element.className.trim().split(/\s+/).join('.')}`
        : ''
      return `${element.tagName.toLowerCase()}${element.id ? `#${element.id}` : ''}${className} (${JSON.stringify(element.innerText.trim())})`
    }
    const leaves = [...document.querySelectorAll<HTMLElement>(leafSelector)].filter((element) => {
      if (!isVisible(element) || !element.innerText.trim()) return false
      return ![...element.querySelectorAll<HTMLElement>(leafSelector)].some((child) => child !== element && isVisible(child) && child.innerText.trim())
    })

    for (const element of leaves) {
      const rect = element.getBoundingClientRect()
      if (!element.closest('.library-tabs')
        && (rect.left < -1 || rect.top < -1 || rect.right > window.innerWidth + 1 || rect.bottom > window.innerHeight + 1)) {
        failures.push(`${currentScenarioId}: text outside viewport: ${description(element)} at ${rect.left},${rect.top},${rect.width}x${rect.height}`)
      }
      const style = getComputedStyle(element)
      const clipsText = style.overflowX === 'hidden' || style.overflowX === 'clip'
        || style.overflowY === 'hidden' || style.overflowY === 'clip'
      if (clipsText && !element.matches('.library-tabs')
        && (element.scrollWidth > element.clientWidth + 1 || element.scrollHeight > element.clientHeight + 1)) {
        failures.push(`${currentScenarioId}: clipped text leaf: ${description(element)} (${element.scrollWidth}x${element.scrollHeight} > ${element.clientWidth}x${element.clientHeight})`)
      }
    }

    for (const selector of overlapGroups) {
      const elements = [...document.querySelectorAll<HTMLElement>(selector)].filter(isVisible)
      for (let index = 0; index < elements.length; index += 1) {
        for (let otherIndex = index + 1; otherIndex < elements.length; otherIndex += 1) {
          const first = elements[index]
          const second = elements[otherIndex]
          if (first.parentElement !== second.parentElement || first.contains(second) || second.contains(first)) continue
          if (first.closest('.viewer-selection-bounds, .viewer-opacity-track') || second.closest('.viewer-selection-bounds, .viewer-opacity-track')) continue
          const left = first.getBoundingClientRect()
          const right = second.getBoundingClientRect()
          const intersection = Math.max(0, Math.min(left.right, right.right) - Math.max(left.left, right.left))
            * Math.max(0, Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top))
          if (intersection > 1) {
            failures.push(`${currentScenarioId}: overlapping ${selector}: ${description(first)} / ${description(second)} (${intersection.toFixed(2)}px2)`)
          }
        }
      }
    }
    return failures
  }, scenarioId)
}

async function comparePngs(
  page: Page,
  referencePath: string,
  referenceComparedPath: string,
  browserPath: string,
  diffPath: string,
  viewport: Dimensions,
  crop: Readonly<{ x: number; y: number }>,
) {
  const referenceBase64 = readFileSync(referencePath).toString('base64')
  const browserBase64 = readFileSync(browserPath).toString('base64')

  const dimensions = await page.evaluate(
    async ({ referenceBase64, browserBase64, tolerance, viewport, crop }) => {
      const loadImage = async (base64: string) => {
        const image = new Image()
        image.src = `data:image/png;base64,${base64}`
        await image.decode()
        return image
      }

      const [referenceImage, browserImage] = await Promise.all([
        loadImage(referenceBase64),
        loadImage(browserBase64),
      ])
      if (
        crop.x < 0
        || crop.y < 0
        || crop.x + viewport.width > referenceImage.naturalWidth
        || crop.y + viewport.height > referenceImage.naturalHeight
      ) {
        throw new Error(`Official reference ${referenceImage.naturalWidth}x${referenceImage.naturalHeight} is smaller than ${viewport.width}x${viewport.height}`)
      }
      const width = viewport.width
      const height = viewport.height
      const referenceCanvas = document.createElement('canvas')
      referenceCanvas.width = width
      referenceCanvas.height = height

      referenceCanvas.getContext('2d', { willReadFrequently: true })!.drawImage(
        referenceImage,
        crop.x,
        crop.y,
        width,
        height,
        0,
        0,
        width,
        height,
      )
      referenceCanvas.id = 'visual-reference-compared-canvas'
      referenceCanvas.style.cssText = `display:block;width:${width}px;height:${height}px`
      document.body.append(referenceCanvas)

      return {
        reference: { width: referenceImage.naturalWidth, height: referenceImage.naturalHeight },
        referenceCompared: { dimensions: { width, height }, crop },
        browser: { width: browserImage.naturalWidth, height: browserImage.naturalHeight },
      }
    },
    { referenceBase64, browserBase64, tolerance: PIXEL_CHANNEL_TOLERANCE, viewport, crop },
  )

  await page.locator('#visual-reference-compared-canvas').screenshot({ path: referenceComparedPath })

  const comparison = await page.evaluate(
    async ({ browserBase64, tolerance, viewport }) => {
      const loadImage = async (base64: string) => {
        const image = new Image()
        image.src = `data:image/png;base64,${base64}`
        await image.decode()
        return image
      }

      const browserImage = await loadImage(browserBase64)
      const width = viewport.width
      const height = viewport.height
      const referenceCanvas = document.querySelector<HTMLCanvasElement>('#visual-reference-compared-canvas')!
      const browserCanvas = document.createElement('canvas')
      const diffCanvas = document.createElement('canvas')
      for (const canvas of [browserCanvas, diffCanvas]) {
        canvas.width = width
        canvas.height = height
      }
      browserCanvas.getContext('2d', { willReadFrequently: true })!.drawImage(browserImage, 0, 0)
      const referencePixels = referenceCanvas.getContext('2d', { willReadFrequently: true })!
        .getImageData(0, 0, width, height)
      const browserPixels = browserCanvas.getContext('2d', { willReadFrequently: true })!
        .getImageData(0, 0, width, height)
      const diffPixels = new ImageData(width, height)
      let differentPixels = 0

      for (let offset = 0; offset < referencePixels.data.length; offset += 4) {
        const redDelta = Math.abs(referencePixels.data[offset] - browserPixels.data[offset])
        const greenDelta = Math.abs(referencePixels.data[offset + 1] - browserPixels.data[offset + 1])
        const blueDelta = Math.abs(referencePixels.data[offset + 2] - browserPixels.data[offset + 2])
        const alphaDelta = Math.abs(referencePixels.data[offset + 3] - browserPixels.data[offset + 3])
        const maximumDelta = Math.max(redDelta, greenDelta, blueDelta, alphaDelta)
        const isDifferent = maximumDelta > tolerance

        if (isDifferent) {
          differentPixels += 1
          diffPixels.data[offset] = 255
          diffPixels.data[offset + 1] = Math.min(48 + maximumDelta, 255)
          diffPixels.data[offset + 2] = 96
          diffPixels.data[offset + 3] = 255
        } else {
          const luminance = Math.round(
            referencePixels.data[offset] * 0.2126
            + referencePixels.data[offset + 1] * 0.7152
            + referencePixels.data[offset + 2] * 0.0722,
          )
          const muted = Math.round(22 + luminance * 0.18)
          diffPixels.data[offset] = muted
          diffPixels.data[offset + 1] = muted
          diffPixels.data[offset + 2] = muted
          diffPixels.data[offset + 3] = 255
        }
      }

      diffCanvas.id = 'visual-diff-canvas'
      diffCanvas.style.cssText = `display:block;width:${width}px;height:${height}px`
      diffCanvas.getContext('2d')!.putImageData(diffPixels, 0, 0)
      document.body.append(diffCanvas)

      return {
        differentPixels,
        totalPixels: width * height,
        diffRatio: differentPixels / (width * height),
      }
    },
    { browserBase64, tolerance: PIXEL_CHANNEL_TOLERANCE, viewport },
  )

  await page.locator('#visual-diff-canvas').screenshot({ path: diffPath })
  await page.locator('#visual-reference-compared-canvas, #visual-diff-canvas').evaluateAll((elements) => elements.forEach((element) => element.remove()))
  return { ...dimensions, ...comparison }
}

for (const scenario of figmaScenarios) {
  test(`figma-match ${scenario.nodeId} matches ${scenario.viewport.width}x${scenario.viewport.height}`, async ({ page }) => {
    const referenceFile = artifactName('figma', scenario.scenarioId, 'reference', 'png')
    const referenceComparedFile = artifactName('figma', scenario.scenarioId, 'reference-compared', 'png')
    const browserFile = artifactName('figma', scenario.scenarioId, 'browser', 'png')
    const diffFile = artifactName('figma', scenario.scenarioId, 'diff', 'png')
    const resultFile = artifactName('figma', scenario.scenarioId, 'result', 'json')
    const referencePath = resolve(SCREENSHOT_DIR, referenceFile)
    const referenceComparedPath = resolve(SCREENSHOT_DIR, referenceComparedFile)
    const browserPath = resolve(SCREENSHOT_DIR, browserFile)
    const diffPath = resolve(SCREENSHOT_DIR, diffFile)

    await page.setViewportSize(scenario.viewport)
    await page.goto(`/?scenario=${scenario.scenarioId}`)
    await expect(page.locator('[data-scenario-id]')).toHaveAttribute('data-scenario-id', scenario.scenarioId)
    await settleVisuals(page)
    await page.screenshot({ path: browserPath, animations: 'disabled', caret: 'hide' })

    expect(
      existsSync(referencePath),
      `Missing official Figma reference ${referenceFile}; capture node ${scenario.nodeId} before comparison.`,
    ).toBe(true)

    const comparison = await comparePngs(
      page,
      referencePath,
      referenceComparedPath,
      browserPath,
      diffPath,
      scenario.viewport,
      scenario.referenceCrop,
    )
    const dimensionsMatch = comparison.referenceCompared.dimensions.width === scenario.viewport.width
      && comparison.referenceCompared.dimensions.height === scenario.viewport.height
      && comparison.browser.width === scenario.viewport.width
      && comparison.browser.height === scenario.viewport.height
    const verdict = dimensionsMatch && comparison.diffRatio <= STRICT_DIFF_RATIO_THRESHOLD ? 'pass' : 'fail'

    const result: ComparisonResult = {
      label: 'figma-match',
      nodeId: scenario.nodeId,
      scenarioId: scenario.scenarioId,
      viewport: scenario.viewport,
      reference: comparison.reference,
      referenceCompared: comparison.referenceCompared,
      browser: comparison.browser,
      differentPixels: comparison.differentPixels,
      totalPixels: comparison.totalPixels,
      diffRatio: comparison.diffRatio,
      threshold: STRICT_DIFF_RATIO_THRESHOLD,
      pixelChannelTolerance: PIXEL_CHANNEL_TOLERANCE,
      verdict,
      artifacts: {
        referenceRaw: referenceFile,
        referenceCompared: referenceComparedFile,
        browser: browserFile,
        diff: diffFile,
        result: resultFile,
      },
    }
    writeResult(result)

    expect(comparison.referenceCompared.dimensions).toEqual(scenario.viewport)
    expect(comparison.browser).toEqual(scenario.viewport)
    expect(comparison.diffRatio).toBeLessThanOrEqual(STRICT_DIFF_RATIO_THRESHOLD)
  })
}

test('user-extension Graphic Motion captures a 320x688 browser baseline', async ({ page }) => {
  const viewport = { width: 320, height: 688 }
  const browserFile = artifactName('user-extension', 'graphic-motion', 'browser', 'png')
  const resultFile = artifactName('user-extension', 'graphic-motion', 'result', 'json')
  const browserPath = resolve(SCREENSHOT_DIR, browserFile)

  await page.setViewportSize(viewport)
  await page.goto('/?scenario=graphic-motion')
  await expect(page.locator('[data-scenario-id]')).toHaveAttribute('data-scenario-id', 'graphic-motion')
  await settleVisuals(page)
  await page.screenshot({ path: browserPath, animations: 'disabled', caret: 'hide' })

  writeResult({
    label: 'user-extension',
    nodeId: null,
    scenarioId: 'graphic-motion',
    viewport,
    reference: null,
    referenceCompared: null,
    browser: viewport,
    differentPixels: null,
    totalPixels: null,
    diffRatio: null,
    threshold: null,
    pixelChannelTolerance: null,
    verdict: 'baseline',
    artifacts: {
      referenceRaw: null,
      referenceCompared: null,
      browser: browserFile,
      diff: null,
      result: resultFile,
    },
  })
})

test('all scenarios have unclipped, non-overlapping visible text leaves', async ({ page }) => {
  const failures: string[] = []
  for (const scenario of geometryScenarios) {
    await page.setViewportSize(scenario.viewport)
    await page.goto(`/?scenario=${scenario.scenarioId}`)
    await expect(page.locator('[data-scenario-id]')).toHaveAttribute('data-scenario-id', scenario.scenarioId)
    await settleVisuals(page)
    failures.push(...await geometryFailures(page, scenario.scenarioId))
  }
  expect(failures, failures.join('\n')).toEqual([])
})

test.afterAll(() => {
  writeAggregateResults()
})
