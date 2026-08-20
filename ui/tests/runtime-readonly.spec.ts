import { expect, request, test, type APIRequestContext } from '@playwright/test'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { execFile } from 'node:child_process'
import { createHash } from 'node:crypto'
import { promisify } from 'node:util'
import { cp, mkdtemp, mkdir, readFile, rm, stat, symlink, utimes, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

type ReadyMessage = Readonly<{
  host: string
  port: number
  projectId: string
}>

type StartedSidecar = Readonly<{
  process: ChildProcessWithoutNullStreams
  ready: ReadyMessage
  readLine: () => Promise<string>
  getStderr: () => string
}>

const uiRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(uiRoot, '..')
const bundledPython = 'C:\\Users\\Charles Kang\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe'
const execFileAsync = promisify(execFile)

let projectRoot: string
let sidecar: ChildProcessWithoutNullStreams
let startedSidecar: StartedSidecar
let ready: ReadyMessage
let baseURL: string

test.beforeAll(async () => {
  projectRoot = await createProjectFixture()
  startedSidecar = await startSidecar(projectRoot)
  sidecar = startedSidecar.process
  ready = startedSidecar.ready
  baseURL = `http://${ready.host}:${ready.port}`
})

test.afterAll(async () => {
  if (sidecar) await stopSidecar(sidecar)
  if (projectRoot) await rm(projectRoot, { recursive: true, force: true })
})

test('binds to loopback and redeems distinct one-time browser launches to a clean URL', async () => {
  expect(ready.host).toBe('127.0.0.1')
  expect(ready.port).toBeGreaterThan(0)
  expect(ready.projectId).toMatch(/^project_[a-f0-9]+$/)

  const first = await request.newContext({ baseURL })
  const launch = await armLaunch(startedSidecar)
  expect(launch).toMatch(new RegExp(`^${baseURL.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/\\?project=${encodeURIComponent(ready.projectId)}&launch=[A-Za-z0-9_-]{43}$`))
  const secondLaunch = await armLaunch(startedSidecar)
  expect(secondLaunch).not.toBe(launch)
  const opened = await browserNavigation(first, launch)
  expect(opened.status()).toBe(303)
  expect(opened.headers().location).toBe(`/?project=${encodeURIComponent(ready.projectId)}`)
  expect(opened.headers()['set-cookie']).toContain('HttpOnly')
  const clean = await first.get(opened.headers().location!, { headers: { 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Site': 'none' } })
  expect(clean.status()).toBe(200)
  expect(await clean.text()).toContain('<div id="root">')

  const replay = await request.newContext({ baseURL })
  const rejected = await browserNavigation(replay, launch)
  expect(rejected.status()).toBe(401)
  expect(rejected.headers()['content-type']).toBe('text/html; charset=utf-8')
  expect(await rejected.text()).toContain('Editor launch unavailable')
  expect((await browserNavigation(replay, secondLaunch)).status()).toBe(303)
  const pickerLaunch = await armLaunch(startedSidecar)
  expect((await browserNavigation(first, pickerLaunch, 'document', 'same-site')).status()).toBe(303)
  await first.dispose()
  await replay.dispose()
})

test('rejects unarmed, non-navigation, and forged-host launches without consuming a launch', async () => {
  const isolated = await startSidecar(projectRoot)
  const isolatedURL = `http://${isolated.ready.host}:${isolated.ready.port}`
  const client = await request.newContext({ baseURL: isolatedURL })
  try {
    const unarmed = `${isolatedURL}/?project=${encodeURIComponent(isolated.ready.projectId)}&launch=missing`
    const unarmedResponse = await browserNavigation(client, unarmed)
    expect(unarmedResponse.status()).toBe(401)
    expect(unarmedResponse.headers()['content-type']).toBe('text/html; charset=utf-8')

    const launch = await armLaunch(isolated)
    const scriptRequest = await client.get(launch, { headers: { 'Sec-Fetch-Mode': 'no-cors', 'Sec-Fetch-Dest': 'script', 'Sec-Fetch-Site': 'same-origin' } })
    expect(scriptRequest.status()).toBe(401)
    expect(await scriptRequest.text()).toContain('Editor launch unavailable')

    const badHost = await client.get(launch, {
      headers: { Host: 'attacker.invalid', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document' },
    })
    expect(badHost.status()).toBe(400)
    expect((await browserNavigation(client, launch)).status()).toBe(303)
  } finally {
    await client.dispose()
    await stopSidecar(isolated.process)
  }
})

test('loads snapshots and exposes only opaque resource identifiers', async () => {
  const isolated = await authenticatedSidecar()
  try {
    const response = await isolated.client.get(`/v1/projects/${isolated.ready.projectId}/snapshot`)
    expect(response.status()).toBe(200)
    const snapshot = await response.json()

    expect(snapshot.ok).toBe(true)
    expect(snapshot.snapshot.view.active_sequence).toBe('main')
    expect(snapshot.snapshot.view.project_name).toBe(path.basename(projectRoot))
    expect(snapshot.snapshot.resources).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: expect.stringMatching(/^res_[a-f0-9]+$/), kind: 'project' }),
      expect.objectContaining({ id: expect.stringMatching(/^res_[a-f0-9]+$/), kind: 'plan' }),
    ]))
    expect(JSON.stringify(snapshot)).not.toContain(projectRoot)
    const source = snapshot.snapshot.media.find((item: { name: string }) => item.name === 'source.mp4')
    expect(source).toEqual(expect.objectContaining({
      id: expect.stringMatching(/^asset_[a-f0-9]+$/), size: expect.any(Number), media_type: 'video/mp4',
    }))
    expect(source.size).toBeGreaterThan(1_000)
    expect(snapshot.snapshot.view.source_media_id).toBe(source.id)
    expect(snapshot.snapshot.artifacts).toEqual([
      expect.objectContaining({ id: expect.stringMatching(/^artifact_[a-f0-9]+$/), name: 'preview.txt' }),
    ])

    const plan = snapshot.snapshot.resources.find((item: { kind: string }) => item.kind === 'plan')
    const resource = await isolated.client.get(
      `/v1/projects/${isolated.ready.projectId}/resources/${plan.id}`,
    )
    expect(resource.status()).toBe(200)
    expect(await resource.json()).toMatchObject({ ok: true, resource: { content: { cues: [] } } })

    const pathEscape = await isolated.client.get(
      `/v1/projects/${isolated.ready.projectId}/resources/${encodeURIComponent('../../work/project.json')}`,
    )
    expect(pathEscape.status()).toBe(404)
  } finally {
    await isolated.client.dispose()
    await stopSidecar(isolated.process)
  }
})

test('imports a selected media file into the opened project input directory', async () => {
  const isolated = await authenticatedSidecar()
  try {
    const response = await isolated.client.post(
      `/v1/projects/${isolated.ready.projectId}/imports`,
      {
        multipart: {
          asset: { name: 'intro.mp3', mimeType: 'audio/mpeg', buffer: Buffer.from('imported audio') },
        },
        headers: { Origin: isolatedURL(isolated.ready) },
      },
    )
    const body = await response.json()
    expect(response.status(), JSON.stringify(body)).toBe(201)
    expect(body).toMatchObject({
      ok: true,
      import: { name: 'intro.mp3', size: 14, media_type: 'audio/mpeg' },
      snapshot: { media: expect.arrayContaining([expect.objectContaining({ name: 'intro.mp3', media_type: 'audio/mpeg' })]) },
    })
    expect((await readFile(path.join(projectRoot, 'input', 'intro.mp3'))).toString()).toBe('imported audio')
  } finally {
    await isolated.client.dispose()
    await stopSidecar(isolated.process)
  }
})

test('browser file selection immediately adds the imported asset to My Assets', async ({ page }) => {
  const isolated = await startSidecar(projectRoot)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    await expect(page.locator('[data-runtime-project-status]')).toContainText(path.basename(projectRoot))

    const fileInput = page.locator('input.asset-file-input').first()
    await fileInput.setInputFiles({ name: 'voiceover.wav', mimeType: 'audio/wav', buffer: Buffer.from('waveform') })

    await expect(page.locator('[data-asset-id]').filter({ hasText: 'voiceover.wav' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'My Assets' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Captions' })).toHaveCount(0)
  } finally {
    await stopSidecar(isolated.process)
  }
})

test('streams confined media by opaque ID with HTTP byte ranges', async () => {
  const isolated = await authenticatedSidecar()
  try {
    const snapshotResponse = await isolated.client.get(`/v1/projects/${isolated.ready.projectId}/snapshot`)
    const { snapshot } = await snapshotResponse.json()
    const mediaId = snapshot.media[0].id

    const ranged = await isolated.client.get(
      `/v1/projects/${isolated.ready.projectId}/media/${mediaId}`,
      { headers: { Range: 'bytes=2-5' } },
    )
    expect(ranged.status()).toBe(206)
    expect(ranged.headers()['content-type']).toBe('video/mp4')
    expect(ranged.headers()['content-range']).toBe(`bytes 2-5/${snapshot.media[0].size}`)
    expect(Buffer.from(await ranged.body())).toHaveLength(4)

    const unknown = await isolated.client.get(
      `/v1/projects/${isolated.ready.projectId}/media/${encodeURIComponent('../source.mp4')}`,
    )
    expect(unknown.status()).toBe(404)
  } finally {
    await isolated.client.dispose()
    await stopSidecar(isolated.process)
  }
})

test('serves only declared hash-bound Graphic Motion frames through opaque layer URLs', async () => {
  const root = await createGraphicMotionLayerProjectFixture()
  const isolated = await authenticatedSidecarFor(root)
  try {
    const snapshotResponse = await isolated.client.get(`/v1/projects/${isolated.ready.projectId}/snapshot`)
    expect(snapshotResponse.status()).toBe(200)
    const snapshotBody = await snapshotResponse.json()
    const layer = snapshotBody.snapshot.view.layers[0]
    expect(layer).toMatchObject({
      kind: 'graphic-motion',
      media_type: 'image-sequence',
      image_sequence: { frame_count: 1, frame_url_template: expect.stringContaining('/layers/') },
    })
    expect(JSON.stringify(layer)).not.toContain('work/cache')

    const frameURL = layer.image_sequence.frame_url_template.replace('%d', '1')
    const frame = await isolated.client.get(frameURL)
    expect(frame.status()).toBe(200)
    expect(frame.headers()['content-type']).toBe('image/png')
    await frame.body()

    const undeclared = await isolated.client.get(layer.image_sequence.frame_url_template.replace('%d', '2'))
    expect(undeclared.status()).toBe(404)
    await undeclared.body()

    await writeFile(path.join(root, 'work', 'cache', 'graphic-motion', 'rendered', 'motion-001', 'frame_000001.png'), 'tampered')
    const changed = await isolated.client.get(frameURL)
    expect(changed.status()).toBe(404)
    await changed.body()
  } finally {
    await stopSidecar(isolated.process)
    await isolated.client.dispose()
    await rm(root, { recursive: true, force: true })
  }
})

test('explicit export is origin-checked, accepts no command payload, and exposes fixed job status', async () => {
  const isolated = await authenticatedSidecar()
  try {
    const baseURL = isolatedURL(isolated.ready)
    const path = `/v1/projects/${isolated.ready.projectId}/exports`
    const forged = await isolated.client.post(path, {
      headers: { Origin: 'http://attacker.invalid' },
      data: {},
    })
    expect(forged.status()).toBe(403)

    const arbitrary = await isolated.client.post(path, {
      headers: { Origin: baseURL },
      data: { command: 'calc.exe' },
    })
    expect(arbitrary.status()).toBe(400)

    const started = await isolated.client.post(path, {
      headers: { Origin: baseURL },
      data: {},
    })
    expect(started.status()).toBe(202)
    const job = await started.json()
    expect(job).toMatchObject({ ok: true, job: { status: 'running' } })
    expect(job.job.id).toMatch(/^export_[a-f0-9]+$/)

    await expect.poll(async () => {
      const response = await isolated.client.get(`${path}/status`)
      expect(response.status()).toBe(200)
      return (await response.json()).job.status
    }, { timeout: 15_000 }).toBe('failed')
  } finally {
    await isolated.client.dispose()
    await stopSidecar(isolated.process)
  }
})

test('rejects an opaque artifact after its collected path is replaced by an outside junction', async () => {
  const root = await createProjectFixture()
  const registeredDirectory = path.join(root, 'review', 'registered')
  const outsideDirectory = await mkdtemp(path.join(tmpdir(), 'cut-editor-outside-'))
  await mkdir(registeredDirectory)
  await writeFile(path.join(registeredDirectory, 'escape.txt'), 'INSIDE-CONTENT')
  await writeFile(path.join(outsideDirectory, 'escape.txt'), 'OUTSIDE-SECRET')
  const isolated = await authenticatedSidecarFor(root)
  try {
    const snapshotResponse = await isolated.client.get(`/v1/projects/${isolated.ready.projectId}/snapshot`)
    const { snapshot } = await snapshotResponse.json()
    const artifact = snapshot.artifacts.find((item: { name: string }) => item.name === 'escape.txt')
    expect(artifact?.id).toMatch(/^artifact_[a-f0-9]+$/)

    await rm(registeredDirectory, { recursive: true, force: true })
    await symlink(outsideDirectory, registeredDirectory, 'junction')
    const response = await isolated.client.get(
      `/v1/projects/${isolated.ready.projectId}/artifacts/${artifact.id}`,
    )
    const body = Buffer.from(await response.body()).toString('utf8')

    expect(response.status()).toBe(404)
    expect(body).not.toContain('OUTSIDE-SECRET')
  } finally {
    await isolated.client.dispose()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
    await rm(outsideDirectory, { recursive: true, force: true })
  }
})

test('browser runtime is ready from the armed credential-free URL and refreshes after an external change', async ({ page }) => {
  const isolated = await startSidecar(projectRoot)
  try {
    const launch = await armLaunch(isolated)
    await page.goto(launch)
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    expect(page.url()).toBe(`${isolatedURL(isolated.ready)}/?project=${encodeURIComponent(isolated.ready.projectId)}`)
    await expect(page.locator('[data-editor-shell]')).toBeVisible()
    const status = page.locator('[data-runtime-project-status]')
    await expect(status).toBeVisible()
    await expect(status.getByText(isolated.ready.projectId, { exact: true })).toBeVisible()
    await expect(status.getByText('main', { exact: true })).toHaveCount(0)
    await expect(status.getByText('Read only', { exact: true })).toHaveCount(0)
    await expect(status.getByText('3 resources', { exact: true })).toHaveCount(0)
    await expect(status.getByText(/^\d+ protocol errors$/)).toBeVisible()

    const before = Number(await page.locator('html').getAttribute('data-runtime-refresh-count'))
    const fingerprintBefore = await status.getAttribute('data-resource-fingerprint')
    await writeFile(path.join(projectRoot, 'work', 'captions', 'captions-plan.json'), '{"cues":[{"id":"external"}]}\n')
    await expect.poll(async () => Number(
      await page.locator('html').getAttribute('data-runtime-refresh-count'),
    )).toBeGreaterThan(before)
    await expect.poll(() => status.getAttribute('data-resource-fingerprint')).not.toBe(fingerprintBefore)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
  }
})

test('keeps the primary workspace visible without production protocol diagnostics', async ({ page }) => {
  const isolated = await startSidecar(projectRoot)
  try {
    await page.setViewportSize({ width: 1440, height: 900 })
    const launch = await armLaunch(isolated)
    await page.goto(launch)
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    await expect(page.getByText('Project data', { exact: true })).toHaveCount(0)
    await expect(page.getByRole('region', { name: 'Protocol resources' })).toHaveCount(0)

    const geometry = await page.locator('.workspace-primary').evaluate((element) => {
      const rect = element.getBoundingClientRect()
      return { top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height }
    })
    expect(geometry.top).toBeGreaterThanOrEqual(52)
    expect(geometry.top).toBeLessThan(100)
    expect(geometry.bottom).toBeLessThanOrEqual(800)
    expect(geometry.width).toBeGreaterThan(1000)
    expect(geometry.height).toBeGreaterThan(500)

    await expect(page.getByRole('region', { name: 'Library', exact: true })).toBeVisible()
    await expect(page.getByRole('region', { name: 'Viewer', exact: true })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Graphic Motion', exact: true })).toBeVisible()
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
  }
})

test('content cards review keeps Viewer and Timeline meaningfully visible in the first viewport', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createContentCardsArtifactProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    const opened = await page.evaluate(async (projectId) => {
      const response = await fetch(`/v1/projects/${projectId}/snapshot`)
      return response.json()
    }, isolated.ready.projectId)
    expect(opened.snapshot.read_only, JSON.stringify(opened.snapshot.errors)).toBe(false)
    await page.getByRole('tab', { name: 'Cards' }).click()
    await expect(page.getByPlaceholder('Search content cards')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Insert content card' })).toHaveCount(0)
    await page.locator('.library-tile').first().click()
    await expect(page.getByRole('group', { name: 'Content Card fields' })).toHaveCount(0)

    const reviewButton = page.getByRole('button', { name: 'Approve preview' })
    await expect(reviewButton).toBeVisible()
    const reviewHitTarget = await reviewButton.evaluate((button) => {
      const rect = button.getBoundingClientRect()
      return document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2) === button
    })
    expect(reviewHitTarget).toBe(true)

    const visibleHeights = await page.evaluate(() => {
      const clippedHeight = (selector: string) => {
        const rect = document.querySelector(selector)!.getBoundingClientRect()
        return Math.max(0, Math.min(window.innerHeight, rect.bottom) - Math.max(0, rect.top))
      }
      return {
        viewer: clippedHeight('.viewer-panel'),
        timeline: clippedHeight('.timeline-panel'),
      }
    })
    expect(visibleHeights.viewer).toBeGreaterThan(300)
    expect(visibleHeights.timeline).toBeGreaterThan(100)
    await expect(page.getByText('Project data', { exact: true })).toHaveCount(0)
    await expect(page.getByRole('region', { name: 'Protocol resources' })).toHaveCount(0)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('runtime cue lists do not repeat card or motion details below the selected item', async ({ page }) => {
  const root = await createContentCardsArtifactProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    await page.getByRole('tab', { name: 'Cards' }).click()
    await expect(page.locator('.library-tile')).toHaveCount(1)
    await expect(page.getByRole('group', { name: 'Content Card fields' })).toHaveCount(0)

    await page.getByRole('tab', { name: 'Graphic Motion' }).click()
    await expect(page.getByRole('group', { name: 'Graphic Motion fields' })).toHaveCount(0)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('browser inspects every registered protocol resource by its server-issued ID', async ({ page }) => {
  const isolated = await startSidecar(projectRoot)
  try {
    const launch = await armLaunch(isolated)
    await page.goto(launch)
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    await page.goto(`${isolatedURL(isolated.ready)}/?project=${encodeURIComponent(isolated.ready.projectId)}&debug=1`)
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    await page.getByText('Project data', { exact: true }).click()
    const inspector = page.getByRole('region', { name: 'Protocol resources' })
    const picker = inspector.getByLabel('Protocol resource')
    await expect(picker).toHaveCount(1)
    const snapshot = await page.evaluate(async (projectId) => {
      const response = await fetch(`/v1/projects/${projectId}/snapshot`)
      return response.json()
    }, isolated.ready.projectId)
    const plan = snapshot.snapshot.resources.find((resource: { kind: string }) => resource.kind === 'plan')
    const resourceIds = await picker.locator('option').evaluateAll((options) => options.map((option) => option.getAttribute('value')))
    expect(resourceIds).toHaveLength(3)
    expect(resourceIds).toEqual(resourceIds.map((id) => expect.stringMatching(/^res_[a-f0-9]+$/)))

    for (const resourceId of resourceIds) {
      await picker.selectOption(resourceId!)
      await expect(inspector).toHaveAttribute('data-resource-id', resourceId!)
      await expect(inspector.locator('[data-resource-etag]')).toBeVisible()
      await expect(inspector.locator('pre')).not.toBeEmpty()
    }

    await picker.selectOption(plan.id)
    await expect(inspector).toHaveAttribute('data-resource-kind', plan.kind)
    await expect(inspector).toHaveAttribute('data-resource-size', String(plan.size))
    await expect(inspector).toHaveAttribute('data-resource-operation', plan.operation_id)
    const etagBefore = plan.etag
    await writeFile(path.join(projectRoot, 'work', 'captions', 'captions-plan.json'), '{"cues":[{"id":"changed"}]}\n')
    await expect(inspector.locator('pre')).toContainText('changed')
    await expect(inspector).not.toHaveAttribute('data-resource-etag', etagBefore)

    await rm(path.join(projectRoot, 'work', 'captions', 'captions-plan.json'))
    await expect(picker.locator(`option[value="${plan.id}"]`)).toHaveCount(0)
    await expect(inspector).toHaveAttribute('data-resource-id', resourceIds[0]!)
    await expect(inspector.locator('pre')).not.toContainText('changed')
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
  }
})

test('browser displays current Agent review image, video, and sandboxed HTML from opaque artifact URLs', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createContentCardsArtifactProjectFixture()
  const isolated = await startSidecar(root)
  try {
    const browserErrors: string[] = []
    page.on('pageerror', (error) => browserErrors.push(error.stack ?? error.message))
    const launch = await armLaunch(isolated)
    await page.goto(launch)
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const gallery = page.getByRole('region', { name: 'Current review artifacts' })
    await expect(gallery).toBeVisible()
    const image = gallery.locator('img[alt="review-still.png"]')
    await expect(image).toBeVisible()
    await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBeGreaterThan(0)
    await expect(gallery.locator('video')).toHaveAttribute('src', /\/artifacts\/artifact_[a-f0-9]+$/)
    const frame = gallery.locator('iframe[title="review-board.html"]')
    await expect(frame).toHaveAttribute('sandbox', '')
    await expect(frame).toHaveAttribute('src', /\/artifacts\/artifact_[a-f0-9]+$/)
    await expect(page.locator('[data-preview-media][src*="/artifacts/"]')).toBeVisible()
    expect(await gallery.locator('[data-artifact-url]').evaluateAll((items) => items.map((item) => item.getAttribute('data-artifact-url'))))
      .toEqual(expect.arrayContaining([
        expect.stringMatching(/^\/v1\/projects\/project_[a-f0-9]+\/artifacts\/artifact_[a-f0-9]+$/),
      ]))
    expect(browserErrors).toEqual([])
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('browser projects opaque project media into a playable Viewer and shared timeline', async ({ page }) => {
  const isolated = await startSidecar(projectRoot)
  try {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect(source).toHaveAttribute('src', new RegExp(`/v1/projects/${isolated.ready.projectId}/media/asset_[a-f0-9]+$`))
    await expect(viewer.locator('img[src="/assets/editor/viewer-poster.png"]')).toHaveCount(0)
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    const decoded = await source.evaluate(async (video) => {
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const context = canvas.getContext('2d', { willReadFrequently: true })!
      const initialTime = video.currentTime
      let nonBlack = 0
      for (const sampleTime of [0.5, 30]) {
        await new Promise<void>((resolve) => {
          video.addEventListener('seeked', () => resolve(), { once: true })
          video.currentTime = Math.min(sampleTime, Math.max(0, video.duration - 0.1))
        })
        context.drawImage(video, 0, 0)
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
        for (let index = 0; index < pixels.length; index += 4) {
          if (pixels[index] || pixels[index + 1] || pixels[index + 2]) nonBlack += 1
        }
        if (nonBlack > 0) break
      }
      await new Promise<void>((resolve) => {
        video.addEventListener('seeked', () => resolve(), { once: true })
        video.currentTime = initialTime
      })
      return { width: video.videoWidth, height: video.videoHeight, nonBlack }
    })
    expect(decoded.width).toBeGreaterThan(0)
    expect(decoded.height).toBeGreaterThan(0)
    expect(decoded.nonBlack).toBeGreaterThan(0)
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.2, 1)

    for (const tabName of ['My Assets', 'Captions', 'Cards', 'Graphic Motion']) {
      const tab = page.getByRole('tab', { name: tabName, exact: true })
      await expect(tab).toBeVisible()
      await tab.click()
      await expect(tab).toHaveAttribute('aria-selected', 'true')
    }

    const play = viewer.getByRole('button', { name: 'Play' })
    const playbackBefore = await viewer.getByLabel('Playhead time').textContent()
    const hitTarget = await play.evaluate((button) => {
      const box = button.getBoundingClientRect()
      return document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2)
        ?.closest('button')?.getAttribute('aria-label')
    })
    expect(hitTarget).toBe('Play')
    await play.click()
    await expect(viewer.getByRole('button', { name: 'Pause' })).toBeVisible()
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeGreaterThan(0.3)
    await expect.poll(() => viewer.getByLabel('Playhead time').textContent()).not.toBe(playbackBefore)
    const synchronized = await page.evaluate(() => {
      const video = document.querySelector<HTMLVideoElement>('video[data-project-media]')!
      const timecode = document.querySelector('[aria-label="Playhead time"]')!.textContent!.split(' / ')[0]
      const [hours, minutes, seconds, frames] = timecode.split(':').map(Number)
      return { videoTime: video.currentTime, programTime: hours * 3600 + minutes * 60 + seconds + frames / 30 }
    })
    // `timeupdate` is intentionally lower-frequency than decoded video frames.
    expect(Math.abs(synchronized.programTime - (synchronized.videoTime - 0.2))).toBeLessThan(0.35)

    const timeline = page.locator('[data-timeline-surface]')
    await timeline.click({ position: { x: 438, y: 40 } })
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.5, 1)

    const clip = page.getByRole('button', { name: 'Video clip', exact: true })
    await clip.click()
    await expect(clip).toHaveAttribute('aria-pressed', 'true')
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
  }
})

test('native Viewer retimes 2x clips and skips an excluded source gap per frame', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createRetimedProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.2, 1)

    await source.evaluate((video) => new Promise<void>((resolve) => {
      video.addEventListener('seeked', () => resolve(), { once: true })
      video.currentTime = 0.38
    }))
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.38, 2)
    await expect.poll(() => page.evaluate(() => {
      const timecode = document.querySelector('[aria-label="Playhead time"]')!.textContent!.split(' / ')[0]
      const [hours, minutes, seconds, frames] = timecode.split(':').map(Number)
      return hours * 3600 + minutes * 60 + seconds + frames / 30
    })).toBeCloseTo(0.09, 1)
    await source.evaluate((video) => new Promise<void>((resolve) => {
      video.addEventListener('seeked', () => resolve(), { once: true })
      video.currentTime = 0.2
    }))
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.2, 2)

    const observedFrames = source.evaluate(async (video) => await new Promise<{
      playbackRate: number
      sourceTimes: number[]
      finalPresentedSourceTime: number | null
    }>((resolve, reject) => {
      const sourceTimes: number[] = []
      const finalSourceTime = 0.8 - 1 / 30
      let finalPresentedSourceTime: number | null = null
      let paused = false
      let endpointPublished = false
      let settled = false
      const playhead = document.querySelector('[aria-label="Playhead time"]')!
      const timeout = window.setTimeout(() => reject(new Error(
        `video did not settle: current=${video.currentTime} paused=${video.paused}`
        + ` presented=${finalPresentedSourceTime} endpoint=${playhead.textContent}`
        + ` frames=${JSON.stringify(sourceTimes)}`,
      )), 5_000)
      const observer = new MutationObserver(() => {
        endpointPublished = playhead.textContent === '00:00:00:06 / 00:00:00:06'
        finish()
      })
      const finish = () => {
        if (settled || !paused || !endpointPublished || finalPresentedSourceTime === null) return
        settled = true
        window.clearTimeout(timeout)
        observer.disconnect()
        window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
          resolve({ playbackRate: video.playbackRate, sourceTimes, finalPresentedSourceTime })
        }))
      }
      const observeFrame = () => {
        if (!video.requestVideoFrameCallback || settled) return
        video.requestVideoFrameCallback((_now, metadata) => {
          sourceTimes.push(metadata.mediaTime)
          if (metadata.mediaTime >= finalSourceTime - 0.001 && metadata.mediaTime < 0.8) {
            finalPresentedSourceTime = metadata.mediaTime
          }
          finish()
          observeFrame()
        })
      }
      video.addEventListener('pause', () => {
        paused = true
        finish()
      }, { once: true })
      observer.observe(playhead, { childList: true, characterData: true, subtree: true })
      observeFrame()
    }))

    await viewer.getByRole('button', { name: 'Play' }).click()
    const observed = await observedFrames

    expect(observed.playbackRate).toBeCloseTo(2, 5)
    expect(observed.sourceTimes.some((timeS) => timeS >= 0.4 && timeS < 0.6)).toBe(false)
    expect(observed.sourceTimes.some((timeS) => timeS >= 0.6 && timeS < 0.8)).toBe(true)
    expect(observed.sourceTimes.some((timeS) => timeS >= 0.8)).toBe(false)
    if (observed.finalPresentedSourceTime !== null) {
      expect(observed.finalPresentedSourceTime).toBeGreaterThanOrEqual(0.6)
      expect(observed.finalPresentedSourceTime).toBeLessThan(0.8)
    }
    const settledEndpoint = await source.evaluate((video) => ({
      currentTime: video.currentTime,
      paused: video.paused,
    }))
    expect(settledEndpoint.paused).toBe(true)
    expect(settledEndpoint.currentTime).toBeCloseTo(0.8 - 1 / 30, 2)
    await expect(viewer.getByLabel('Playhead time')).toHaveText('00:00:00:06 / 00:00:00:06')

    const replayStart = source.evaluate((video) => new Promise<{
      mediaTime: number
      paused: boolean
      readyState: number
    }>((resolve, reject) => {
      let playing = false
      let firstClipFrame: number | null = null
      const timeout = window.setTimeout(() => reject(new Error('replay did not present a playing first-clip frame')), 2_000)
      const finish = () => {
        if (!playing || firstClipFrame === null) return
        window.clearTimeout(timeout)
        resolve({ mediaTime: firstClipFrame, paused: video.paused, readyState: video.readyState })
      }
      video.addEventListener('playing', () => {
        playing = true
        finish()
      }, { once: true })
      const observeFrame = () => {
        if (!video.requestVideoFrameCallback) {
          if (!video.paused && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA
            && video.currentTime >= 0.2 && video.currentTime < 0.4) {
            firstClipFrame = video.currentTime
            finish()
            return
          }
          window.setTimeout(observeFrame, 0)
          return
        }
        video.requestVideoFrameCallback((_now, metadata) => {
          if (metadata.mediaTime >= 0.2 && metadata.mediaTime < 0.4) {
            firstClipFrame = metadata.mediaTime
            finish()
            return
          }
          observeFrame()
        })
      }
      observeFrame()
    }))
    await viewer.getByRole('button', { name: 'Play' }).click()
    const replay = await replayStart
    expect(replay.paused).toBe(false)
    expect(replay.readyState).toBeGreaterThanOrEqual(2)
    expect(replay.mediaTime).toBeGreaterThanOrEqual(0.2)
    expect(replay.mediaTime).toBeLessThan(0.4)
    await source.evaluate((video) => video.pause())
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('native Viewer presents late frames before proactive 2x clip boundaries', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createLongRetimedProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.2, 2)

    const observedFrames = source.evaluate((video) => new Promise<{
      playbackRate: number
      sourceTimes: number[]
    }>((resolve, reject) => {
      const sourceTimes: number[] = []
      const requestVideoFrame = video.requestVideoFrameCallback.bind(video)
      Object.defineProperty(video, 'requestVideoFrameCallback', {
        configurable: true,
        value: (callback: VideoFrameRequestCallback) => requestVideoFrame((now, metadata) => {
          sourceTimes.push(metadata.mediaTime)
          callback(now, metadata)
        }),
      })
      const timeout = window.setTimeout(() => reject(new Error('long retimed playback did not stop')), 5_000)
      const playhead = document.querySelector('[aria-label="Playhead time"]')!
      const finish = () => {
        if (playhead.textContent !== '00:00:00:18 / 00:00:00:18') return
        window.clearTimeout(timeout)
        observer.disconnect()
        resolve({ playbackRate: video.playbackRate, sourceTimes })
      }
      const observer = new MutationObserver(finish)
      observer.observe(playhead, { childList: true, characterData: true, subtree: true })
      video.addEventListener('pause', finish)
    }))

    await viewer.getByRole('button', { name: 'Play' }).click()
    const observed = await observedFrames

    expect(observed.playbackRate).toBeCloseTo(2, 5)
    expect(
      observed.sourceTimes.some((timeS) => timeS >= 0.65 && timeS < 0.8),
      `presented source frames: ${JSON.stringify(observed.sourceTimes)}`,
    ).toBe(true)
    expect(observed.sourceTimes.some((timeS) => timeS >= 0.8 && timeS < 1)).toBe(false)
    expect(
      observed.sourceTimes.some((timeS) => timeS >= 1.6 - 1 / 30 - 0.001 && timeS < 1.6),
      `presented source frames: ${JSON.stringify(observed.sourceTimes)}`,
    ).toBe(true)
    expect(
      observed.sourceTimes.some((timeS) => timeS >= 1.6),
      `presented source frames: ${JSON.stringify(observed.sourceTimes)}`,
    ).toBe(false)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('native Viewer fallback pauses when hidden', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createRetimedProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await source.evaluate((video) => {
      Object.defineProperty(video, 'requestVideoFrameCallback', { configurable: true, value: undefined })
      Object.defineProperty(document, 'hidden', { configurable: true, value: false })
    })

    const pausedWhileHidden = source.evaluate((video) => new Promise<number>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error('fallback playback did not pause while hidden')), 2_000)
      video.addEventListener('pause', () => {
        window.clearTimeout(timeout)
        resolve(video.currentTime)
      }, { once: true })
    }))
    await viewer.getByRole('button', { name: 'Play' }).click()
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, value: true })
      document.dispatchEvent(new Event('visibilitychange'))
    })
    expect(await pausedWhileHidden).toBeLessThan(0.4)

    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, value: false })
      document.dispatchEvent(new Event('visibilitychange'))
    })
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('native Viewer fallback transitions after the native clock reaches the clip boundary', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createRetimedProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.2, 2)
    await source.evaluate((video) => {
      Object.defineProperty(video, 'requestVideoFrameCallback', { configurable: true, value: undefined })
      Object.defineProperty(document, 'hidden', { configurable: true, value: false })
    })

    const transitioned = source.evaluate((video) => new Promise<{
      targetTime: number
      maxFirstClipTime: number
    }>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error('fallback did not enter the second clip from native media time')), 5_000)
      let maxFirstClipTime = video.currentTime
      const sampler = window.setInterval(() => {
        if (video.currentTime < 0.4) maxFirstClipTime = Math.max(maxFirstClipTime, video.currentTime)
      }, 2)
      const onSeeked = () => {
        if (video.currentTime < 0.59 || video.currentTime >= 0.8) return
        video.pause()
        window.clearTimeout(timeout)
        window.clearInterval(sampler)
        video.removeEventListener('seeked', onSeeked)
        resolve({ targetTime: video.currentTime, maxFirstClipTime })
      }
      video.addEventListener('seeked', onSeeked)
    }))
    await viewer.getByRole('button', { name: 'Play' }).click()
    const transition = await transitioned

    expect(transition.maxFirstClipTime).toBeGreaterThanOrEqual(0.35)
    expect(transition.targetTime).toBeCloseTo(0.6, 1)
    await source.evaluate((video) => video.pause())
    await expect(viewer.getByLabel('Playhead time')).toHaveText('00:00:00:03 / 00:00:00:06')
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('native Viewer follows canonical clip order across a tolerated one-frame source overlap', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createOverlappingProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    const enteredOverlap = source.evaluate((video) => new Promise<number>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error('successor did not seek into the overlap')), 5_000)
      const onSeeked = () => {
        if (video.currentTime < 0.566 || video.currentTime >= 0.6) return
        window.clearTimeout(timeout)
        video.removeEventListener('seeked', onSeeked)
        video.pause()
        resolve(video.currentTime)
      }
      video.addEventListener('seeked', onSeeked)
    }))
    await viewer.getByRole('button', { name: 'Play' }).click()

    expect(await enteredOverlap).toBeCloseTo(0.5666666666666667, 2)
    await expect(source).toHaveJSProperty('paused', true)
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.5666666666666667, 2)
    const programTimeS = await viewer.getByLabel('Playhead time').evaluate((output) => {
      const [hours, minutes, seconds, frames] = output.textContent!.split(' / ')[0].split(':').map(Number)
      return hours * 3600 + minutes * 60 + seconds + frames / 30
    })
    expect(programTimeS).toBeGreaterThanOrEqual(0.4)
    expect(programTimeS).toBeLessThan(0.433334)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('installed Chrome publishes a real user Pause before the final clip', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createLongRetimedProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await viewer.getByRole('button', { name: 'Play' }).click()
    const pause = viewer.getByRole('button', { name: 'Pause' })
    await expect(pause).toBeVisible()
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeGreaterThan(0.3)

    await pause.click()

    await expect(source).toHaveJSProperty('paused', true)
    await expect(viewer.getByRole('button', { name: 'Play' })).toBeVisible()
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('seeking during a boundary hold cancels the stale hold deadline', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createSlowBoundaryHoldProjectFixture(0.0625, 10)
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await source.evaluate((video) => new Promise<void>((resolve) => {
      video.addEventListener('seeked', () => resolve(), { once: true })
      video.currentTime = 0.36
    }))
    const held = source.evaluate((video) => new Promise<number>((resolve, reject) => {
      const deadline = performance.now() + 5_000
      const poll = () => {
        if (video.paused && video.currentTime >= 0.35 && video.currentTime < 0.4) {
          resolve(video.currentTime)
          return
        }
        if (performance.now() >= deadline) {
          reject(new Error(`first clip did not enter its boundary hold: current=${video.currentTime} paused=${video.paused}`))
          return
        }
        requestAnimationFrame(poll)
      }
      poll()
    }))
    await viewer.getByRole('button', { name: 'Play' }).click()
    expect(await held).toBeGreaterThanOrEqual(0.35)

    const timelineSurface = page.locator('[data-timeline-surface]')
    const timelineSurfaceBox = await timelineSurface.boundingBox()
    expect(timelineSurfaceBox).not.toBeNull()
    await timelineSurface.click({ position: { x: timelineSurfaceBox!.width * 4.8 / 6.4, y: 40 } })
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(0.7, 2)
    await expect(viewer.getByLabel('Playhead time')).toHaveText('00:00:04:08 / 00:00:06:04')
    await expect(viewer.getByRole('button', { name: 'Play' })).toBeVisible()
    await page.waitForTimeout(2_000)

    await expect(source).toHaveJSProperty('paused', true)
    await expect(viewer.getByLabel('Playhead time')).toHaveText('00:00:04:08 / 00:00:06:04')
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('installed Chrome treats Pause clicked during a boundary hold as explicit user intent', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createSlowBoundaryHoldProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await source.evaluate((video) => new Promise<void>((resolve) => {
      video.addEventListener('seeked', () => resolve(), { once: true })
      video.currentTime = 0.36
    }))
    const held = source.evaluate((video) => new Promise<number>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error('first clip did not enter its boundary hold')), 5_000)
      const onPause = () => {
        if (video.currentTime < 0.35 || video.currentTime >= 0.4) return
        window.clearTimeout(timeout)
        video.removeEventListener('pause', onPause)
        resolve(video.currentTime)
      }
      video.addEventListener('pause', onPause)
    }))
    await viewer.getByRole('button', { name: 'Play' }).click()
    const heldSourceTime = await held

    await viewer.getByRole('button', { name: 'Pause' }).click()
    await page.waitForTimeout(500)

    await expect(source).toHaveJSProperty('paused', true)
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(heldSourceTime, 3)
    await expect(viewer.getByRole('button', { name: 'Play' })).toBeVisible()
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('same-source successor seek retires the hold before the native seek early return', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createSlowOverlappingBoundaryHoldProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await source.evaluate((video) => new Promise<void>((resolve) => {
      video.addEventListener('seeked', () => resolve(), { once: true })
      video.currentTime = 0.36
    }))
    const held = source.evaluate((video) => new Promise<number>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error('overlap predecessor did not enter its boundary hold')), 5_000)
      const onPause = () => {
        if (video.currentTime < 0.35 || video.currentTime >= 0.4) return
        window.clearTimeout(timeout)
        video.removeEventListener('pause', onPause)
        resolve(video.currentTime)
      }
      video.addEventListener('pause', onPause)
    }))
    await viewer.getByRole('button', { name: 'Play' }).click()
    const heldSourceTime = await held

    const timelineSurface = page.locator('[data-timeline-surface]')
    const timelineSurfaceBox = await timelineSurface.boundingBox()
    expect(timelineSurfaceBox).not.toBeNull()
    await timelineSurface.click({ position: { x: timelineSurfaceBox!.width * 2 / 4, y: 40 } })
    await expect(viewer.getByLabel('Playhead time')).toHaveText('00:00:02:00 / 00:00:04:00')
    await page.waitForTimeout(500)

    await expect(source).toHaveJSProperty('paused', true)
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(heldSourceTime, 3)
    await expect(viewer.getByRole('button', { name: 'Play' })).toBeVisible()
    await expect(viewer.getByLabel('Playhead time')).toHaveText('00:00:02:00 / 00:00:04:00')
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('runtime clip refresh during a boundary hold publishes stopped playback', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createSlowBoundaryHoldProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
    const source = viewer.locator('video[aria-label="source.mp4"]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    await source.evaluate((video) => new Promise<void>((resolve) => {
      video.addEventListener('seeked', () => resolve(), { once: true })
      video.currentTime = 0.36
    }))
    const held = source.evaluate((video) => new Promise<number>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error('first clip did not enter its boundary hold')), 5_000)
      const onPause = () => {
        if (video.currentTime < 0.35 || video.currentTime >= 0.4) return
        window.clearTimeout(timeout)
        video.removeEventListener('pause', onPause)
        resolve(video.currentTime)
      }
      video.addEventListener('pause', onPause)
    }))
    await viewer.getByRole('button', { name: 'Play' }).click()
    const heldSourceTime = await held

    const refreshBefore = Number(await page.locator('html').getAttribute('data-runtime-refresh-count'))
    const timelinePath = path.join(root, 'work', 'timeline.json')
    const timeline = JSON.parse(await readFile(timelinePath, 'utf8'))
    timeline.clips[1].id = 'clip-slow-b-refreshed'
    await writeFile(timelinePath, JSON.stringify(timeline))
    await expect.poll(async () => Number(
      await page.locator('html').getAttribute('data-runtime-refresh-count'),
    )).toBeGreaterThan(refreshBefore)
    await page.waitForTimeout(500)

    await expect(source).toHaveJSProperty('paused', true)
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(heldSourceTime, 3)
    await expect(viewer.getByRole('button', { name: 'Play' })).toBeVisible()
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

for (const playbackRate of [0.01, 32]) {
  test(`installed Chrome disables native playback for legal protocol rate ${playbackRate}`, async ({ page }) => {
    test.setTimeout(30_000)
    const root = await createPlaybackRateProjectFixture(playbackRate)
    const isolated = await startSidecar(root)
    try {
      await page.goto(await armLaunch(isolated))
      await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

      const viewer = page.getByRole('region', { name: 'Viewer', exact: true })
      const source = viewer.locator('video[aria-label="source.mp4"]')
      const play = viewer.getByRole('button', { name: 'Play' })
      await expect(play).toBeDisabled()
      await expect(play).toHaveAttribute('title', new RegExp(`${playbackRate}.*browser`, 'i'))
      await expect(source).toBeVisible()

      await page.locator('[data-timeline-surface]').click({ position: { x: 300, y: 40 } })
      await expect(source).not.toHaveJSProperty('currentTime', Number.NaN)
      await expect(viewer.getByLabel('Playhead time')).not.toBeEmpty()
    } finally {
      await page.close()
      await stopSidecar(isolated.process)
      await rm(root, { recursive: true, force: true })
    }
  })
}

test('mutation routes forward only typed protocol commands and return conflicts', async () => {
  const isolated = await authenticatedSidecar()
  try {
    const response = await isolated.client.post(
      `/v1/projects/${isolated.ready.projectId}/transactions`,
      {
        data: { operation: 'captions', readSet: {}, patch: { revision: 99 } },
        headers: { Origin: isolatedURL(isolated.ready) },
      },
    )
    expect(response.status()).toBe(400)
    expect(await response.json()).toEqual({ ok: false, error: 'plan.update accepts only a typed operation update' })

    const review = await isolated.client.post(
      `/v1/projects/${isolated.ready.projectId}/reviews/decision`,
      {
        data: { operation: 'video-cut', readSet: {}, decision: { decision: 'approved' } },
        headers: { Origin: isolatedURL(isolated.ready) },
      },
    )
    expect(review.status()).toBe(400)
    expect(await review.json()).toEqual({ ok: false, error: 'unsupported operation' })
  } finally {
    await isolated.client.dispose()
    await stopSidecar(isolated.process)
  }
})

test('content cards save commits through sidecar and stale read sets return 409', async () => {
  test.setTimeout(20_000)
  const root = await createContentCardsProjectFixture()
  const isolated = await startSidecar(root)
  const client = await request.newContext({ baseURL: isolatedURL(isolated.ready) })
  try {
    await browserNavigation(client, await armLaunch(isolated))
    const loaded = await client.get(`/v1/projects/${isolated.ready.projectId}/snapshot`)
    const { snapshot } = await loaded.json()
    expect(snapshot.read_only, `loaded:${JSON.stringify(snapshot.errors)}`).toBe(false)
    const operation = snapshot.view.operations.find((item: { id: string }) => item.id === 'content-cards')
    const readSet = {
      project: snapshot.resources.find((item: { kind: string }) => item.kind === 'project').etag,
      operation: operation.etag,
      plan: snapshot.resources.find((item: { operation_id?: string }) => item.operation_id === 'content-cards').etag,
    }
    const body = {
      operation: 'content-cards', readSet,
      review: { schema_version: 1, cards: [{ id: 'card-001', selected: true, copy: 'Saved locally', placement: 'top', visual_treatment: 'default' }] },
    }
    const saved = await client.post(`/v1/projects/${isolated.ready.projectId}/transactions`, {
      data: body, headers: { Origin: isolatedURL(isolated.ready) },
    })
    const savedBody = await saved.json()
    expect(saved.status(), `saved:${JSON.stringify(savedBody)}`).toBe(200)
    expect(savedBody).toMatchObject({
      ok: true,
      result: 'committed',
      snapshot: { media: expect.any(Array), artifacts: expect.any(Array) },
    })
    const project = JSON.parse(await readFile(path.join(root, 'work', 'project.json'), 'utf8'))
    expect(project.operations[0]).toMatchObject({ revision: 2, status: 'stale' })
    expect(project.render.status).toBe('draft')

    const conflict = await client.post(`/v1/projects/${isolated.ready.projectId}/transactions`, {
      data: body, headers: { Origin: isolatedURL(isolated.ready) },
    })
    const conflictBody = await conflict.json()
    expect(conflict.status(), `conflict:${JSON.stringify(conflictBody)}`).toBe(409)
    expect(conflictBody).toMatchObject({
      ok: false,
      error: 'conflict',
      snapshot: { media: expect.any(Array), artifacts: expect.any(Array) },
    })
  } finally {
    await client.dispose()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('content card Inspector updates the second cue without overwriting the first', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createTwoContentCardsProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    await page.getByRole('tab', { name: 'Cards' }).click()
    await page.getByRole('button', { name: /Second original/ }).click()
    await expect(page.getByLabel('Content card copy')).toHaveValue('Second original')

    await page.getByLabel('Content card copy').fill('Second updated in editor')
    await page.getByRole('button', { name: 'Save All' }).click()

    await expect.poll(async () => {
      const plan = JSON.parse(await readFile(path.join(root, 'work', 'content-cards', 'cards-plan.json'), 'utf8'))
      return plan.cards.map((card: { copy: { text?: string; suggested_text?: string } }) => card.copy.text ?? card.copy.suggested_text)
    }).toEqual(['Original copy', 'Second updated in editor'])
    await expect(page.getByLabel('Content card copy')).toHaveValue('Second updated in editor')
    await expect(page.getByRole('button', { name: 'Insert content card' })).toHaveCount(0)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('caption Inspector updates the second cue and keeps the first cue unchanged', async ({ page }) => {
  test.setTimeout(30_000)
  const root = await createCaptionsProjectFixture()
  const isolated = await startSidecar(root)
  try {
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    await page.getByRole('tab', { name: 'Captions' }).click()
    await page.getByRole('button', { name: /Second real caption/ }).click()
    await expect(page.getByLabel('Caption text')).toHaveValue('Second real caption')

    await page.getByLabel('Caption text').fill('Second caption updated in editor')
    await page.getByRole('button', { name: 'Save All' }).click()

    await expect.poll(async () => {
      const plan = JSON.parse(await readFile(path.join(root, 'work', 'captions', 'captions-plan.json'), 'utf8'))
      return plan.cues.map((cue: { text: string }) => cue.text)
    }).toEqual(['First real caption', 'Second caption updated in editor'])
    await expect(page.getByLabel('Caption text')).toHaveValue('Second caption updated in editor')
    await expect(page.getByPlaceholder('Search caption styles')).toHaveCount(0)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('real 42-sol Graphic Motion cue can be disabled, saved, and locally discarded', async ({ page }) => {
  const sourceRoot = process.env.CAC_REAL_EDITOR_PROJECT
  test.skip(!sourceRoot, 'Set CAC_REAL_EDITOR_PROJECT to the 42-sol project root')
  test.setTimeout(180_000)
  const root = await mkdtemp(path.join(tmpdir(), 'cut-editor-real-project-'))
  await cp(sourceRoot!, root, { recursive: true, preserveTimestamps: true })
  await refreshSourceFingerprint(root)
  const isolated = await startSidecar(root)
  try {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    const opened = await page.evaluate(async (projectId) => {
      const response = await fetch(`/v1/projects/${projectId}/snapshot`)
      return response.json()
    }, isolated.ready.projectId)
    expect(opened.snapshot.read_only, JSON.stringify(opened.snapshot.errors)).toBe(false)
    await expect(page.locator('[data-runtime-project-status]')).toContainText(isolated.ready.projectId)
    await expect(page.getByText('original-video.mp4', { exact: true })).toBeVisible()
    await expect(page.getByText('City Walk', { exact: true })).toHaveCount(0)

    await page.getByRole('tab', { name: 'Graphic Motion' }).click()
    await page.getByRole('button', { name: /THE REAL TONY STARK/ }).click()
    const enabled = page.getByLabel('Graphic Motion enabled')
    await expect(enabled).toBeChecked()
    await expect(page.getByText('License: unknown', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Insert motion' })).toHaveCount(0)

    await enabled.uncheck()
    const transaction = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().endsWith('/transactions'),
    )
    await page.getByRole('button', { name: 'Save All' }).click()
    const transactionResponse = await transaction
    const transactionBody = await transactionResponse.json()
    expect(transactionResponse.status(), JSON.stringify(transactionBody)).toBe(200)
    expect(transactionBody, JSON.stringify(transactionBody)).toMatchObject({
      ok: true,
      result: 'committed',
      snapshot: { media: expect.any(Array), artifacts: expect.any(Array) },
    })
    await expect.poll(async () => {
      const plan = JSON.parse(await readFile(path.join(root, 'work', 'graphic-motion', 'graphic-motion-plan.json'), 'utf8'))
      return plan.cues[0].status
    }).toBe('skipped')
    await expect(enabled).not.toBeChecked()

    await enabled.click()
    const localEditState = {
      checked: await enabled.isChecked(),
      status: await page.getByRole('status', { name: 'Graphic Motion review status' }).textContent(),
    }
    expect(localEditState, JSON.stringify(localEditState)).toMatchObject({ checked: true })
    await expect(page.getByRole('button', { name: 'Save All' })).toBeEnabled()
    await page.getByRole('button', { name: 'Discard changes' }).click()
    await expect(enabled).not.toBeChecked()
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('real project saves a transformed Graphic Motion layer without rendering and exports only on demand', async ({ page }) => {
  const sourceRoot = process.env.CAC_REAL_EDITOR_PROJECT
  test.skip(!sourceRoot || process.env.CAC_REAL_EXPORT_E2E !== '1', 'Set CAC_REAL_EDITOR_PROJECT and CAC_REAL_EXPORT_E2E=1')
  test.setTimeout(600_000)
  const preisolated = process.env.CAC_REAL_EDITOR_PROJECT_ISOLATED === '1'
  const root = preisolated ? sourceRoot! : await mkdtemp(path.join(tmpdir(), 'cut-editor-real-export-'))
  const skippedCaches = new Set(['faster-whisper-medium-local', 'npm', 'python-deps'])
  if (!preisolated) await cp(sourceRoot!, root, {
    recursive: true,
    preserveTimestamps: true,
    filter: (source) => {
      const relative = path.relative(sourceRoot!, source)
      const parts = relative.split(path.sep)
      return !(parts[0] === 'work' && parts[1] === 'cache' && skippedCaches.has(parts[2]))
    },
  })
  await refreshSourceFingerprint(root)
  const motionPlan = JSON.parse(await readFile(path.join(root, 'work', 'graphic-motion', 'graphic-motion-plan.json'), 'utf8'))
  const motionCue = motionPlan.cues.find((cue: { status?: string }) => cue.status === 'verified')
  expect(motionCue).toBeTruthy()
  const finalPath = path.join(root, 'final', 'final-video.mp4')
  const beforeSave = {
    hash: await sha256File(finalPath),
    stat: await stat(finalPath),
  }
  const isolated = await startSidecar(root)
  let exportRequests = 0
  page.on('request', (request) => {
    if (/\/exports(?:\/status)?$/.test(new URL(request.url()).pathname)) exportRequests += 1
  })
  try {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const timelineSurface = page.locator('[data-timeline-surface]')
    const timelineSurfaceBox = await timelineSurface.boundingBox()
    expect(timelineSurfaceBox).not.toBeNull()
    const projectManifest = JSON.parse(await readFile(path.join(root, 'work', 'project.json'), 'utf8'))
    const timeline = JSON.parse(await readFile(path.join(root, 'work', 'timeline.json'), 'utf8'))
    expect(projectManifest.project_id).toBeTruthy()
    await timelineSurface.click({
      position: {
        x: timelineSurfaceBox!.width * (motionCue.program_range.start_s + 0.1) / timeline.program_duration_s,
        y: 40,
      },
    })
    await page.getByRole('tab', { name: 'Graphic Motion' }).click()
    await page.getByRole('button', { name: new RegExp(motionCue.intent.content.slice(0, 24), 'i') }).click()

    const layer = page.locator('[data-viewer-layer="graphic-motion"]')
    await expect(layer).toBeVisible()
    const initialTransform = await layer.evaluate((element) => ({
      x: Number(element.getAttribute('data-layer-x')),
      y: Number(element.getAttribute('data-layer-y')),
      scale_x: Number(element.getAttribute('data-layer-scale-x')),
      scale_y: Number(element.getAttribute('data-layer-scale-y')),
    }))
    const layerBox = await layer.boundingBox()
    expect(layerBox).not.toBeNull()
    await page.mouse.move(layerBox!.x + layerBox!.width / 2, layerBox!.y + layerBox!.height / 2)
    await page.mouse.down()
    await page.mouse.move(layerBox!.x + layerBox!.width / 2 + 72, layerBox!.y + layerBox!.height / 2 + 36)
    await page.mouse.up()

    const scaleHandle = layer.getByRole('button', { name: 'Resize east', exact: true })
    const scaleBox = await scaleHandle.boundingBox()
    expect(scaleBox).not.toBeNull()
    await page.mouse.move(scaleBox!.x + scaleBox!.width / 2, scaleBox!.y + scaleBox!.height / 2)
    await page.mouse.down()
    await page.mouse.move(scaleBox!.x + scaleBox!.width / 2 + 36, scaleBox!.y + scaleBox!.height / 2 + 18)
    await page.mouse.up()

    const editedTransform = await layer.evaluate((element) => ({
      x: Number(element.getAttribute('data-layer-x')),
      y: Number(element.getAttribute('data-layer-y')),
      scale_x: Number(element.getAttribute('data-layer-scale-x')),
      scale_y: Number(element.getAttribute('data-layer-scale-y')),
    }))
    expect(editedTransform.x).not.toBe(initialTransform.x)
    expect(editedTransform.y).not.toBe(initialTransform.y)
    expect(editedTransform.scale_x).not.toBe(initialTransform.scale_x)
    expect(editedTransform.scale_y).toBe(initialTransform.scale_y)
    expect(exportRequests).toBe(0)

    const transaction = page.waitForResponse((response) =>
      response.request().method() === 'POST' && response.url().endsWith('/transactions'),
    )
    await page.getByRole('button', { name: 'Save All' }).click()
    const transactionResponse = await transaction
    const transactionBody = await transactionResponse.json()
    expect(transactionResponse.status(), JSON.stringify({ transactionBody, editedTransform })).toBe(200)
    await expect.poll(async () => {
      const plan = JSON.parse(await readFile(path.join(root, 'work', 'graphic-motion', 'graphic-motion-plan.json'), 'utf8'))
      return plan.cues.find((cue: { id: string }) => cue.id === motionCue.id)?.editor_transform
    }).toEqual(editedTransform)

    const afterSaveStat = await stat(finalPath)
    expect(await sha256File(finalPath)).toBe(beforeSave.hash)
    expect(afterSaveStat.size).toBe(beforeSave.stat.size)
    expect(afterSaveStat.mtimeMs).toBe(beforeSave.stat.mtimeMs)
    expect(exportRequests).toBe(0)
    const savedProject = JSON.parse(await readFile(path.join(root, 'work', 'project.json'), 'utf8'))
    expect(savedProject.render.status).toBe('draft')

    await page.getByRole('button', { name: 'Export Video' }).click()
    let terminalJob: { status?: string; error?: string } | undefined
    await expect.poll(async () => {
      terminalJob = await page.evaluate(async (projectId) => {
        const response = await fetch(`/v1/projects/${projectId}/exports/status`)
        return (await response.json()).job
      }, isolated.ready.projectId)
      return terminalJob?.status
    }, { timeout: 480_000, intervals: [250, 500, 1_000] }).toMatch(/^(succeeded|failed)$/)
    expect(terminalJob, isolated.getStderr()).toMatchObject({ status: 'succeeded' })
    await expect(page.getByRole('status', { name: 'Export status' })).toHaveText('Export complete')
    expect(exportRequests).toBeGreaterThan(1)

    const afterExportStat = await stat(finalPath)
    expect(afterExportStat.size).toBeGreaterThan(0)
    expect(afterExportStat.mtimeMs).toBeGreaterThan(beforeSave.stat.mtimeMs)
    expect(await sha256File(finalPath)).not.toBe(beforeSave.hash)
    const exportedProject = JSON.parse(await readFile(path.join(root, 'work', 'project.json'), 'utf8'))
    expect(exportedProject.render.status).toBe('verified')

    const { stdout } = await execFileAsync('ffprobe', [
      '-v', 'error', '-show_entries', 'stream=codec_type,width,height:format=duration', '-of', 'json', finalPath,
    ])
    const probe = JSON.parse(stdout)
    expect(probe.streams).toEqual(expect.arrayContaining([
      expect.objectContaining({ codec_type: 'video', width: 1280, height: 720 }),
    ]))
    expect(Number(probe.format.duration)).toBeCloseTo(167.973152, 1)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    if (!preisolated) await rm(root, { recursive: true, force: true })
  }
})

test('real 42-sol workspace passes the desktop viewport and visual audit', async ({ page }) => {
  const sourceRoot = process.env.CAC_REAL_EDITOR_PROJECT
  const visualOutput = process.env.CAC_EDITOR_VISUAL_OUTPUT
  test.skip(!sourceRoot || !visualOutput, 'Set CAC_REAL_EDITOR_PROJECT and CAC_EDITOR_VISUAL_OUTPUT')
  test.setTimeout(180_000)
  const root = await mkdtemp(path.join(tmpdir(), 'cut-editor-real-visual-'))
  await cp(sourceRoot!, root, { recursive: true, preserveTimestamps: true })
  await refreshSourceFingerprint(root)
  await mkdir(visualOutput!, { recursive: true })
  const isolated = await startSidecar(root)
  try {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')
    await page.getByRole('tab', { name: 'Graphic Motion' }).click()
    await page.getByRole('button', { name: /THE REAL TONY STARK/ }).click()
    await expect(page.locator('.viewer-selection-toolbar')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Volume' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Capture frame' })).toHaveCount(0)

    const source = page.locator('video[data-project-media]')
    await expect.poll(() => source.evaluate((video) => video.readyState)).toBeGreaterThanOrEqual(2)
    const timelineSurface = page.locator('[data-timeline-surface]')
    const timelineSurfaceBox = await timelineSurface.boundingBox()
    expect(timelineSurfaceBox).not.toBeNull()
    await timelineSurface.click({ position: { x: timelineSurfaceBox!.width * 2 / 167.973152, y: 40 } })
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(2, 0)
    const graphicMotion = page.locator('[data-viewer-layer="graphic-motion"]')
    await expect(graphicMotion).toBeVisible()
    const motionFrame = graphicMotion.locator('img')
    await expect(motionFrame).toHaveAttribute('src', /\/layers\/layer_[a-f0-9]+\/frames\/60$/)
    const motionPixels = await motionFrame.evaluate(async (image: HTMLImageElement) => {
      await image.decode()
      const canvas = document.createElement('canvas')
      canvas.width = image.naturalWidth
      canvas.height = image.naturalHeight
      const context = canvas.getContext('2d', { willReadFrequently: true })!
      context.drawImage(image, 0, 0)
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
      let nonTransparent = 0
      for (let index = 3; index < pixels.length; index += 4) {
        if (pixels[index]) nonTransparent += 1
      }
      return { width: canvas.width, height: canvas.height, nonTransparent }
    })
    expect(motionPixels).toMatchObject({ width: 1280, height: 720 })
    expect(motionPixels.nonTransparent, JSON.stringify(motionPixels)).toBeGreaterThan(0)
    await page.screenshot({
      path: path.join(visualOutput!, 'real-42-sol-layered-2s.png'),
      fullPage: false,
    })

    await timelineSurface.click({ position: { x: timelineSurfaceBox!.width * 30 / 167.973152, y: 40 } })
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeCloseTo(30, 0)
    await page.getByRole('button', { name: 'Play' }).click()
    await expect.poll(() => source.evaluate((video) => video.currentTime)).toBeGreaterThan(30.1)
    await page.getByRole('button', { name: 'Pause' }).click()
    const decoded = await source.evaluate((video) => {
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const context = canvas.getContext('2d', { willReadFrequently: true })!
      context.drawImage(video, 0, 0)
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
      let nonBlack = 0
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index] || pixels[index + 1] || pixels[index + 2]) nonBlack += 1
      }
      return {
        width: video.videoWidth,
        height: video.videoHeight,
        nonBlack,
        currentTime: video.currentTime,
        readyState: video.readyState,
        networkState: video.networkState,
        error: video.error?.message,
        presentedFrames: video.getVideoPlaybackQuality().totalVideoFrames,
      }
    })
    expect(decoded).toMatchObject({ width: 1280, height: 720 })
    expect(decoded.nonBlack, JSON.stringify(decoded)).toBeGreaterThan(0)

    for (const viewport of [
      { width: 1366, height: 768 },
      { width: 1440, height: 900 },
      { width: 1920, height: 1080 },
      { width: 2560, height: 1440 },
    ]) {
      await page.setViewportSize(viewport)
      await expect(page.locator('.viewer-canvas')).toHaveAttribute('data-sequence-width', '1280')
      await expect.poll(async () => page.evaluate(() => {
        const surface = document.querySelector<HTMLElement>('[data-timeline-surface]')!
        const content = document.querySelector<HTMLElement>('.timeline-content')!
        return Math.abs(surface.clientWidth - content.getBoundingClientRect().width)
      })).toBeLessThanOrEqual(1)
      const geometry = await page.evaluate(() => {
        const rect = (selector: string) => {
          const box = document.querySelector(selector)!.getBoundingClientRect()
          return { left: box.left, top: box.top, right: box.right, bottom: box.bottom, width: box.width, height: box.height }
        }
        const inspector = document.querySelector<HTMLElement>('.library-inspector-fields')!
        const rulerLabels = [...document.querySelectorAll<HTMLElement>('.timeline-ruler span')]
          .map((element) => element.getBoundingClientRect())
          .sort((left, right) => left.left - right.left)
        return {
          viewport: { width: innerWidth, height: innerHeight },
          document: {
            scrollWidth: document.documentElement.scrollWidth,
            scrollHeight: document.documentElement.scrollHeight,
            bodyScrollWidth: document.body.scrollWidth,
            bodyScrollHeight: document.body.scrollHeight,
          },
          shell: rect('[data-editor-shell]'),
          review: rect('.workspace-review'),
          primary: rect('.workspace-primary'),
          library: rect('.library-panel'),
          viewer: rect('.viewer-panel'),
          stage: rect('.viewer-stage'),
          canvas: rect('.viewer-canvas'),
          timeline: rect('.workspace-timeline'),
          rulerLabelsOverlap: rulerLabels.some((label, index) => index > 0 && label.left < rulerLabels[index - 1]!.right),
          inspector: {
            clientWidth: inspector.clientWidth,
            scrollWidth: inspector.scrollWidth,
          },
        }
      })
      expect(geometry.document).toEqual({
        scrollWidth: viewport.width,
        scrollHeight: viewport.height,
        bodyScrollWidth: viewport.width,
        bodyScrollHeight: viewport.height,
      })
      expect(geometry.shell).toMatchObject({ left: 0, top: 0, width: viewport.width, height: viewport.height })
      expect(geometry.review.bottom).toBeLessThanOrEqual(geometry.primary.top + 1)
      expect(geometry.primary.bottom).toBeLessThanOrEqual(geometry.timeline.top + 1)
      for (const panel of [geometry.library, geometry.viewer, geometry.timeline]) {
        expect(panel.left).toBeGreaterThanOrEqual(0)
        expect(panel.top).toBeGreaterThanOrEqual(0)
        expect(panel.right).toBeLessThanOrEqual(viewport.width + 1)
        expect(panel.bottom).toBeLessThanOrEqual(viewport.height + 1)
        expect(panel.width).toBeGreaterThan(0)
        expect(panel.height).toBeGreaterThan(0)
      }
      expect(Math.abs(geometry.canvas.width / geometry.canvas.height - 16 / 9)).toBeLessThan(0.01)
      expect(geometry.canvas.width).toBeLessThanOrEqual(geometry.stage.width)
      expect(geometry.canvas.height).toBeLessThanOrEqual(geometry.stage.height)
      expect(geometry.rulerLabelsOverlap).toBe(false)
      expect(geometry.inspector.scrollWidth).toBeLessThanOrEqual(geometry.inspector.clientWidth + 1)
      await page.screenshot({
        path: path.join(visualOutput!, `real-42-sol-${viewport.width}x${viewport.height}.png`),
        fullPage: false,
      })
    }
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

test('real 46-sol workspace satisfies the scoped UI review', async ({ page }) => {
  const sourceRoot = process.env.CAC_REAL_UI_REVIEW_PROJECT
  const visualOutput = process.env.CAC_EDITOR_VISUAL_OUTPUT
  test.skip(!sourceRoot || !visualOutput, 'Set CAC_REAL_UI_REVIEW_PROJECT and CAC_EDITOR_VISUAL_OUTPUT')
  test.setTimeout(180_000)
  await mkdir(visualOutput!, { recursive: true })
  const isolated = await startSidecar(sourceRoot!)
  try {
    await page.setViewportSize({ width: 1384, height: 865 })
    await page.goto(await armLaunch(isolated))
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const status = page.locator('[data-runtime-project-status]')
    await expect(status.getByText('main', { exact: true })).toHaveCount(0)
    await expect(status.getByText('Writable', { exact: true })).toHaveCount(0)
    await expect(status.getByText('5 resources', { exact: true })).toHaveCount(0)

    const palette = await page.evaluate(() => {
      const root = getComputedStyle(document.documentElement)
      return {
        accent: root.getPropertyValue('--color-accent').trim(),
        selection: root.getPropertyValue('--color-selection').trim(),
        focus: root.getPropertyValue('--color-focus').trim(),
      }
    })
    expect(palette).toEqual({ accent: '#3e8b82', selection: '#294e4a', focus: '#79b7a7' })
    await page.screenshot({ path: path.join(visualOutput!, '46-sol-main.png'), fullPage: false })

    await page.getByRole('tab', { name: 'Cards' }).click()
    await expect(page.locator('.library-tile').filter({ hasText: 'WARMING A PLANET' })).toHaveCount(1)
    await expect(page.getByRole('group', { name: 'Content Card fields' })).toHaveCount(0)
    await expect(page.getByLabel('Content card copy')).toHaveCount(0)
    await page.screenshot({ path: path.join(visualOutput!, '46-sol-cards.png'), fullPage: false })

    await page.getByRole('tab', { name: 'Graphic Motion' }).click()
    await expect(page.locator('.library-tile').filter({ hasText: 'Automatic snake charger plugs itself into the Tesla.' })).toHaveCount(1)
    await expect(page.getByRole('group', { name: 'Graphic Motion fields' })).toHaveCount(0)
    await expect(page.getByText('Recipe: xyz-fade-up', { exact: true })).toHaveCount(0)
    await page.screenshot({ path: path.join(visualOutput!, '46-sol-graphic-motion.png'), fullPage: false })
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
  }
})

async function authenticatedSidecar() {
  return authenticatedSidecarFor(projectRoot)
}

async function authenticatedSidecarFor(root: string) {
  const isolated = await startSidecar(root)
  const isolatedURLValue = isolatedURL(isolated.ready)
  const client = await request.newContext({ baseURL: isolatedURLValue })
  const launch = await armLaunch(isolated)
  const response = await browserNavigation(client, launch)
  expect(response.status()).toBe(303)
  const clean = await client.get(response.headers().location!)
  expect(clean.status()).toBe(200)
  return { ...isolated, client }
}

function browserNavigation(client: APIRequestContext, url: string) {
  return client.get(url, {
    maxRedirects: 0,
    headers: { 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Site': 'none' },
  })
}

function isolatedURL(message: ReadyMessage) {
  return `http://${message.host}:${message.port}`
}

async function startSidecar(root: string): Promise<StartedSidecar> {
  const dataRoot = path.join(root, '.editor-data')
  await mkdir(dataRoot, { recursive: true })
  const child = spawn(process.execPath, [
    path.join(repositoryRoot, 'runtime', 'sidecar.cjs'),
    '--project-root', root,
    '--ui-root', path.join(uiRoot, 'dist'),
    '--data-root', dataRoot,
  ], {
    cwd: repositoryRoot,
    env: { ...process.env, CAC_PYTHON: process.env.CAC_PYTHON ?? bundledPython },
    stdio: ['pipe', 'pipe', 'pipe'],
  })

  const queuedLines: string[] = []
  const lineWaiters: Array<(line: string) => void> = []
  let stdout = ''
  let stderr = ''
  child.stdout.on('data', (chunk) => {
    stdout += chunk.toString()
    while (stdout.includes('\n')) {
      const newline = stdout.indexOf('\n')
      const line = stdout.slice(0, newline)
      stdout = stdout.slice(newline + 1)
      const waiter = lineWaiters.shift()
      if (waiter) waiter(line)
      else queuedLines.push(line)
    }
  })
  child.stderr.on('data', (chunk) => { stderr += chunk.toString() })
  const readLine = () => new Promise<string>((resolve) => {
    const line = queuedLines.shift()
    if (line !== undefined) resolve(line)
    else lineWaiters.push(resolve)
  })
  const message = await new Promise<ReadyMessage>((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`sidecar startup timed out: ${stderr}`)), 30_000)
    void readLine().then((line) => {
      clearTimeout(timeout)
      resolve(JSON.parse(line))
    })
    child.once('exit', (code) => {
      clearTimeout(timeout)
      reject(new Error(`sidecar exited ${code}: ${stderr}`))
    })
    child.once('error', reject)
  }).catch((error) => {
    child.kill()
    return waitForExit(child, 2_000).then(() => { throw error })
  })
  return { process: child, ready: message, readLine, getStderr: () => stderr }
}

let controlRequestId = 0

async function armLaunch(sidecar: StartedSidecar) {
  const id = ++controlRequestId
  sidecar.process.stdin.write(`${JSON.stringify({ id, command: 'arm_launch' })}\n`)
  const response = JSON.parse(await sidecar.readLine())
  expect(response).toMatchObject({ id, ok: true })
  return response.url as string
}

async function stopSidecar(child: ChildProcessWithoutNullStreams) {
  if (child.exitCode !== null) return
  child.stdin.end()
  if (!await waitForExit(child, 3_000)) {
    child.kill()
    await waitForExit(child, 2_000)
  }
  child.stdout.destroy()
  child.stderr.destroy()
}

function waitForExit(child: ChildProcessWithoutNullStreams, timeoutMs: number) {
  if (child.exitCode !== null) return Promise.resolve(true)
  return new Promise<boolean>((resolve) => {
    const timeout = setTimeout(() => {
      child.off('exit', onExit)
      resolve(false)
    }, timeoutMs)
    const onExit = () => {
      clearTimeout(timeout)
      resolve(true)
    }
    child.once('exit', onExit)
  })
}

async function createProjectFixture() {
  const root = await mkdtemp(path.join(tmpdir(), 'cut-editor-sidecar-'))
  await mkdir(path.join(root, 'work', 'captions'), { recursive: true })
  await mkdir(path.join(root, 'input'), { recursive: true })
  await mkdir(path.join(root, 'review'), { recursive: true })
  const source = path.join(root, 'input', 'source.mp4')
  await execFileAsync('ffmpeg', [
    '-y', '-f', 'lavfi', '-i', 'testsrc2=size=96x64:rate=30', '-t', '1',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', source,
  ])
  await writeFile(path.join(root, 'input', 'aaa-derived.mp4'), 'not-a-video')
  await writeFile(path.join(root, 'review', 'preview.txt'), 'agent preview')
  await writeFile(path.join(root, 'work', 'captions', 'captions-plan.json'), '{"cues":[]}\n')
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1,
    source_duration_s: 1,
    program_duration_s: 0.6,
    fps: { num: 30, den: 1 },
    clips: [{
      id: 'clip-1',
      source_range: { start_s: 0.2, end_s: 0.8 },
      program_range: { start_s: 0, end_s: 0.6 },
      speed: 1,
    }],
  }))
  await writeFile(path.join(root, 'work', 'project.json'), JSON.stringify({
    schema_version: 1,
    project_id: 'fixture',
    revision: 1,
    source: { path: '../input/source.mp4' },
    active_sequence: 'main',
    sequences: { main: { timeline: 'timeline.json', operations: ['captions'] } },
    operations: [{
      id: 'captions',
      revision: 1,
      status: 'draft',
      target: { sequence: 'main', scope: 'full' },
      effects: ['overlay'],
      plan: 'captions/captions-plan.json',
      based_on: {},
      render_contributions: [],
    }],
    reviews: [],
    render: { status: 'draft' },
  }))
  return root
}

async function createGraphicMotionLayerProjectFixture() {
  const root = await mkdtemp(path.join(tmpdir(), 'cut-editor-layer-'))
  const frameRoot = path.join(root, 'work', 'cache', 'graphic-motion', 'rendered', 'motion-001')
  await mkdir(frameRoot, { recursive: true })
  await mkdir(path.join(root, 'work', 'graphic-motion'), { recursive: true })
  await mkdir(path.join(root, 'input'), { recursive: true })
  const frame = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')
  const framePath = path.join(frameRoot, 'frame_000001.png')
  await writeFile(framePath, frame)
  await writeFile(path.join(root, 'input', 'source.mp4'), 'video')
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1,
    timeline_id: 'main',
    source_duration_s: 1,
    program_duration_s: 1,
    fps: { num: 30, den: 1 },
    clips: [{
      id: 'clip-1', source_range: { start_s: 0, end_s: 1 },
      program_range: { start_s: 0, end_s: 1 }, speed: 1,
    }],
  }))
  await writeFile(path.join(root, 'work', 'graphic-motion', 'graphic-motion-plan.json'), JSON.stringify({
    schema_version: 3,
    cues: [{
      id: 'motion-001', status: 'verified', program_range: { start_s: 0, end_s: 1 },
      intent: { content: 'Bound motion' }, selection: { chosen_recipe_id: 'fixture' },
      recipe: {}, review: {},
      render: {
        kind: 'overlay', asset: 'cache/graphic-motion/rendered/motion-001',
        asset_type: 'image-sequence', pattern: 'frame_%06d.png', start_number: 1,
        fps: { num: 30, den: 1 }, start_s: 0, duration_s: 1,
        frames: [{
          path: 'work/cache/graphic-motion/rendered/motion-001/frame_000001.png',
          sha256: createHash('sha256').update(frame).digest('hex'),
        }],
      },
    }],
  }))
  await writeFile(path.join(root, 'work', 'project.json'), JSON.stringify({
    schema_version: 1,
    project_id: 'layer-fixture',
    source: { path: '../input/source.mp4' },
    active_sequence: 'main',
    sequences: { main: { timeline: 'timeline.json', operations: ['graphic-motion'] } },
    operations: [{
      id: 'graphic-motion', revision: 1, status: 'verified',
      plan: 'graphic-motion/graphic-motion-plan.json', depends_on: [], based_on: {},
    }],
    reviews: [], render: { status: 'draft' },
  }))
  return root
}

async function createRetimedProjectFixture() {
  const root = await createProjectFixture()
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1,
    source_duration_s: 1,
    program_duration_s: 0.2,
    fps: { num: 30, den: 1 },
    clips: [
      {
        id: 'clip-fast-a',
        source_range: { start_s: 0.2, end_s: 0.4 },
        program_range: { start_s: 0, end_s: 0.1 },
        speed: 2,
      },
      {
        id: 'clip-fast-b',
        source_range: { start_s: 0.6, end_s: 0.8 },
        program_range: { start_s: 0.1, end_s: 0.2 },
        speed: 2,
      },
    ],
  }))
  return root
}

async function createOverlappingProjectFixture() {
  const root = await createProjectFixture()
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1,
    source_duration_s: 1,
    program_duration_s: 0.6333333333333333,
    fps: { num: 30, den: 1 },
    clips: [
      {
        id: 'clip-overlap-a',
        source_range: { start_s: 0.2, end_s: 0.6 },
        program_range: { start_s: 0, end_s: 0.4 },
        speed: 1,
      },
      {
        id: 'clip-overlap-b',
        source_range: { start_s: 0.5666666666666667, end_s: 0.8 },
        program_range: { start_s: 0.4, end_s: 0.6333333333333333 },
        speed: 1,
      },
    ],
  }))
  return root
}

async function createSlowBoundaryHoldProjectFixture(speed = 0.1, fps = 30) {
  const root = await createProjectFixture()
  const clipProgramDurationS = 0.2 / speed
  if (fps !== 30) {
    await execFileAsync('ffmpeg', [
      '-y', '-f', 'lavfi', '-i', `testsrc2=size=96x64:rate=${fps}`, '-t', '1',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
      path.join(root, 'input', 'source.mp4'),
    ])
  }
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1,
    source_duration_s: 1,
    program_duration_s: clipProgramDurationS * 2,
    fps: { num: fps, den: 1 },
    clips: [
      {
        id: 'clip-slow-a',
        source_range: { start_s: 0.2, end_s: 0.4 },
        program_range: { start_s: 0, end_s: clipProgramDurationS },
        speed,
      },
      {
        id: 'clip-slow-b',
        source_range: { start_s: 0.6, end_s: 0.8 },
        program_range: { start_s: clipProgramDurationS, end_s: clipProgramDurationS * 2 },
        speed,
      },
    ],
  }))
  return root
}

async function createSlowOverlappingBoundaryHoldProjectFixture() {
  const root = await createProjectFixture()
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1,
    source_duration_s: 1,
    program_duration_s: 4,
    fps: { num: 30, den: 1 },
    clips: [
      {
        id: 'clip-slow-overlap-a',
        source_range: { start_s: 0.2, end_s: 0.4 },
        program_range: { start_s: 0, end_s: 2 },
        speed: 0.1,
      },
      {
        id: 'clip-slow-overlap-b',
        source_range: { start_s: 0.3666666666666667, end_s: 0.5666666666666667 },
        program_range: { start_s: 2, end_s: 4 },
        speed: 0.1,
      },
    ],
  }))
  return root
}

async function createPlaybackRateProjectFixture(playbackRate: number) {
  const root = await createProjectFixture()
  const sourceStartS = playbackRate < 1 ? 0.2 : 0
  const sourceDurationS = playbackRate < 1 ? 0.01 : 0.96
  const programDurationS = sourceDurationS / playbackRate
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1,
    source_duration_s: 1,
    program_duration_s: programDurationS,
    fps: { num: 30, den: 1 },
    clips: [{
      id: `clip-rate-${playbackRate}`,
      source_range: { start_s: sourceStartS, end_s: sourceStartS + sourceDurationS },
      program_range: { start_s: 0, end_s: programDurationS },
      speed: playbackRate,
    }],
  }))
  return root
}

async function createLongRetimedProjectFixture() {
  const root = await createProjectFixture()
  await execFileAsync('ffmpeg', [
    '-y', '-f', 'lavfi', '-i', 'testsrc2=size=96x64:rate=30', '-t', '2',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    path.join(root, 'input', 'source.mp4'),
  ])
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1,
    source_duration_s: 2,
    program_duration_s: 0.6,
    fps: { num: 30, den: 1 },
    clips: [
      {
        id: 'clip-long-a',
        source_range: { start_s: 0.2, end_s: 0.8 },
        program_range: { start_s: 0, end_s: 0.3 },
        speed: 2,
      },
      {
        id: 'clip-long-b',
        source_range: { start_s: 1, end_s: 1.6 },
        program_range: { start_s: 0.3, end_s: 0.6 },
        speed: 2,
      },
    ],
  }))
  return root
}

async function createContentCardsProjectFixture() {
  const root = await mkdtemp(path.join(tmpdir(), 'cut-editor-cards-'))
  await mkdir(path.join(root, 'work', 'content-cards'), { recursive: true })
  await mkdir(path.join(root, 'input'), { recursive: true })
  const sourcePath = path.join(root, 'input', 'source.mp4')
  await writeFile(sourcePath, 'video')
  await utimes(sourcePath, 1_700_000_000, 1_700_000_000)
  await writeFile(path.join(root, 'work', 'timeline.json'), JSON.stringify({
    schema_version: 1, source_duration_s: 1, program_duration_s: 1,
    fps: { num: 30, den: 1 }, clips: [{ id: 'clip-1', source_range: { start_s: 0, end_s: 1 }, program_range: { start_s: 0, end_s: 1 }, speed: 1 }],
  }))
  await writeFile(path.join(root, 'work', 'content-cards', 'cards-plan.json'), JSON.stringify({
    schema_version: 1, target: 'overlay', timeline_id: 'main',
    brief: { theme: 'almanac', target_card_count: 1 }, cards: [{
      id: 'card-001', card_type: 'intro', evidence_refs: ['moment-1'],
      copy: { status: 'draft', suggested_text: 'Original copy', display: { title: null } },
      placement: { status: 'draft', region: null }, visual_treatment: { status: 'draft', layout: 'default' },
    }],
  }))
  const { stdout: sourceStat } = await execFileAsync(bundledPython, ['-c',
    'import os,sys; s=os.stat(sys.argv[1]); print(f"{s.st_size} {s.st_mtime_ns}")',
    sourcePath])
  const [sourceSize, sourceModifiedNs] = sourceStat.trim().split(' ')
  const projectJson = JSON.stringify({
    schema_version: 1,
    source: { path: '../input/source.mp4', fingerprint: { size: Number(sourceSize), modified_ns: '__MTIME__', duration_s: 1 } },
    active_sequence: 'main', sequences: { main: { timeline: 'timeline.json', operations: ['content-cards'] } },
    operations: [{ id: 'content-cards', revision: 1, status: 'approved', depends_on: [], based_on: {},
      target: { sequence: 'main', scope: 'full' }, effects: { changes_timeline: false, changes_geometry: false, changes_video_pixels: true, changes_audio: false },
      plan: 'content-cards/cards-plan.json', outputs: [] }], reviews: [], render: { status: 'verified' },
  }).replace('"__MTIME__"', sourceModifiedNs)
  await writeFile(path.join(root, 'work', 'project.json'), projectJson)
  return root
}

async function createTwoContentCardsProjectFixture() {
  const root = await createContentCardsProjectFixture()
  const planPath = path.join(root, 'work', 'content-cards', 'cards-plan.json')
  const plan = JSON.parse(await readFile(planPath, 'utf8'))
  plan.brief.target_card_count = 2
  plan.cards.push({
    ...plan.cards[0],
    id: 'card-002',
    copy: { ...plan.cards[0].copy, suggested_text: 'Second original' },
    program_start_s: 0.5,
    duration_s: 0.4,
  })
  await writeFile(planPath, `${JSON.stringify(plan)}\n`)
  return root
}

async function createCaptionsProjectFixture() {
  const root = await createContentCardsProjectFixture()
  await mkdir(path.join(root, 'work', 'captions'), { recursive: true })
  await writeFile(path.join(root, 'work', 'captions', 'captions-plan.json'), JSON.stringify({
    schema_version: 1,
    target: 'overlay',
    timeline_id: 'main',
    timebase: 'program',
    program_duration_s: 1,
    style: { status: 'approved', preset: 'clean' },
    review: { status: 'approved', evidence: ['previous'] },
    cues: [
      { id: 'cue-001', index: 1, start: 0, end: 0.4, text: 'First real caption', lines: ['First real caption'], program_range: { start_s: 0, end_s: 0.4 } },
      { id: 'cue-002', index: 2, start: 0.5, end: 0.9, text: 'Second real caption', lines: ['Second real caption'], program_range: { start_s: 0.5, end_s: 0.9 } },
    ],
  }))
  const projectPath = path.join(root, 'work', 'project.json')
  const project = JSON.parse(await readFile(projectPath, 'utf8'))
  project.sequences.main.operations = ['captions']
  project.operations = [{
    ...project.operations[0],
    id: 'captions',
    plan: 'captions/captions-plan.json',
  }]
  await writeFile(projectPath, `${JSON.stringify(project)}\n`)
  return root
}

async function refreshSourceFingerprint(root: string) {
  await execFileAsync(bundledPython, [
    '-c',
    [
      'import json,sys',
      'from pathlib import Path',
      'root=Path(sys.argv[1])',
      'path=root/"work"/"project.json"',
      'project=json.loads(path.read_text(encoding="utf-8"))',
      'source=(root/"work"/project["source"]["path"]).resolve()',
      'stat=source.stat()',
      'project["source"]["fingerprint"]["size"]=stat.st_size',
      'project["source"]["fingerprint"]["modified_ns"]=stat.st_mtime_ns',
      'path.write_text(json.dumps(project, indent=2)+"\\n", encoding="utf-8")',
    ].join(';'),
    root,
  ])
}

async function createContentCardsArtifactProjectFixture() {
  const root = await createContentCardsProjectFixture()
  const reviewRoot = path.join(root, 'review', '03-content-cards')
  await mkdir(reviewRoot, { recursive: true })
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64')
  const artifacts = [
    ['review-still.png', png],
    ['review-preview.mp4', Buffer.from('not-a-decodable-video-but-a-real-served-video-artifact')],
    ['review-board.html', Buffer.from('<!doctype html><title>Agent review</title><p>Current evidence</p>')],
  ] as const
  const hashes: string[] = []
  for (const [name, content] of artifacts) {
    await writeFile(path.join(reviewRoot, name), content)
    hashes.push(`sha256:${await sha256Bytes(content)}`)
  }
  const projectPath = path.join(root, 'work', 'project.json')
  const project = JSON.parse(await readFile(projectPath, 'utf8'))
  project.reviews = [{
    id: 'content-cards-preview-r1', revision: 1, status: 'draft', depends_on: ['content-cards'],
    based_on: { 'content-cards': 1 }, snapshot_etag: '', evidence_hashes: hashes,
  }]
  await writeFile(projectPath, `${JSON.stringify(project)}\n`)
  project.reviews[0].snapshot_etag = await authoritativeSnapshotEtag(root)
  await writeFile(projectPath, `${JSON.stringify(project)}\n`)
  return root
}

async function sha256Bytes(content: Buffer) {
  const { createHash } = await import('node:crypto')
  return createHash('sha256').update(content).digest('hex')
}

async function sha256File(file: string) {
  return createHash('sha256').update(await readFile(file)).digest('hex')
}

async function authoritativeSnapshotEtag(root: string) {
  const { stdout } = await execFileAsync(process.env.CAC_PYTHON ?? bundledPython, [
    '-c',
    'import sys; sys.path.insert(0, sys.argv[1]); from project_snapshot import build_snapshot; print(build_snapshot(sys.argv[2])["snapshot_etag"])',
    path.join(repositoryRoot, 'runtime'),
    root,
  ])
  return stdout.trim()
}
