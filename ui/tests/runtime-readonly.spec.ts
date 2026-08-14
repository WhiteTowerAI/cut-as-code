import { expect, request, test, type APIRequestContext } from '@playwright/test'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { mkdtemp, mkdir, readFile, rm, symlink, writeFile } from 'node:fs/promises'
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

test('binds to loopback and arms one credential-free browser launch at a time', async () => {
  expect(ready.host).toBe('127.0.0.1')
  expect(ready.port).toBeGreaterThan(0)
  expect(ready.projectId).toMatch(/^project_[a-f0-9]+$/)

  const first = await request.newContext({ baseURL })
  const launch = await armLaunch(startedSidecar)
  expect(launch).toBe(`${baseURL}/?project=${encodeURIComponent(ready.projectId)}`)
  const opened = await browserNavigation(first, launch)
  expect(opened.status()).toBe(200)
  expect(await opened.text()).toContain('<div id="root">')

  const replay = await request.newContext({ baseURL })
  const rejected = await browserNavigation(replay, launch)
  expect(rejected.status()).toBe(401)
  await first.dispose()
  await replay.dispose()
})

test('rejects unarmed launches and forged hosts without consuming an armed launch', async () => {
  const isolated = await startSidecar(projectRoot)
  const isolatedURL = `http://${isolated.ready.host}:${isolated.ready.port}`
  const client = await request.newContext({ baseURL: isolatedURL })
  try {
    const launch = `${isolatedURL}/?project=${encodeURIComponent(isolated.ready.projectId)}`
    expect((await browserNavigation(client, launch)).status()).toBe(401)

    await armLaunch(isolated)

    const badHost = await client.get(launch, {
      headers: { Host: 'attacker.invalid', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document' },
    })
    expect(badHost.status()).toBe(400)
    expect((await browserNavigation(client, launch)).status()).toBe(200)
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
    expect(page.url()).toBe(launch)
    await expect(page.locator('[data-editor-shell]')).toBeVisible()
    const status = page.locator('[data-runtime-project-status]')
    await expect(status).toBeVisible()
    await expect(status.getByText(isolated.ready.projectId, { exact: true })).toBeVisible()
    await expect(status.getByText('main', { exact: true })).toBeVisible()
    await expect(status.getByText('Read only', { exact: true })).toBeVisible()
    await expect(status.getByText('3 resources', { exact: true })).toBeVisible()
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

test('keeps the primary workspace visible while project data is collapsed', async ({ page }) => {
  const isolated = await startSidecar(projectRoot)
  try {
    await page.setViewportSize({ width: 1440, height: 900 })
    const launch = await armLaunch(isolated)
    await page.goto(launch)
    await expect.poll(() => page.locator('html').getAttribute('data-runtime-state')).toBe('ready')

    const projectData = page.getByText('Project data', { exact: true })
    await expect(projectData).toBeVisible()
    await expect(page.getByRole('region', { name: 'Protocol resources' })).toBeHidden()

    const geometry = await page.locator('.workspace-primary').evaluate((element) => {
      const rect = element.getBoundingClientRect()
      return { top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height }
    })
    expect(geometry.top).toBeGreaterThanOrEqual(52)
    expect(geometry.top).toBeLessThan(100)
    expect(geometry.bottom).toBeLessThanOrEqual(800)
    expect(geometry.width).toBeGreaterThan(1000)
    expect(geometry.height).toBeGreaterThan(600)

    await expect(page.getByRole('region', { name: 'Library', exact: true })).toBeVisible()
    await expect(page.getByRole('region', { name: 'Viewer', exact: true })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Graphic Motion', exact: true })).toBeVisible()
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
  }
})

test('browser inspects every registered protocol resource by its server-issued ID', async ({ page }) => {
  const isolated = await startSidecar(projectRoot)
  try {
    const launch = await armLaunch(isolated)
    await page.goto(launch)
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

    const observedFrames = source.evaluate(async (video) => await new Promise<{
      playbackRate: number
      sourceTimes: number[]
    }>((resolve, reject) => {
      const sourceTimes: number[] = []
      const timeout = window.setTimeout(() => reject(new Error('did not reach second source clip')), 5_000)
      const observe = () => {
        sourceTimes.push(video.currentTime)
        if (video.currentTime >= 0.65) {
          window.clearTimeout(timeout)
          resolve({ playbackRate: video.playbackRate, sourceTimes })
          return
        }
        if ('requestVideoFrameCallback' in video) video.requestVideoFrameCallback(observe)
        else window.requestAnimationFrame(observe)
      }
      if ('requestVideoFrameCallback' in video) video.requestVideoFrameCallback(observe)
      else window.requestAnimationFrame(observe)
    }))

    await viewer.getByRole('button', { name: 'Play' }).click()
    const observed = await observedFrames
    await source.evaluate((video) => video.pause())

    expect(observed.playbackRate).toBeCloseTo(2, 5)
    expect(observed.sourceTimes.some((timeS) => timeS >= 0.4 && timeS < 0.6)).toBe(false)
    await expect.poll(() => page.evaluate(() => {
      const video = document.querySelector<HTMLVideoElement>('video[data-project-media]')!
      const timecode = document.querySelector('[aria-label="Playhead time"]')!.textContent!.split(' / ')[0]
      const [hours, minutes, seconds, frames] = timecode.split(':').map(Number)
      const programTime = hours * 3600 + minutes * 60 + seconds + frames / 30
      return Math.abs(programTime - (0.1 + (video.currentTime - 0.6) / 2))
    })).toBeLessThan(0.08)
  } finally {
    await page.close()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
  }
})

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
    expect(await response.json()).toEqual({ ok: false, error: 'plan.update accepts only a typed content-cards review' })

    const review = await isolated.client.post(
      `/v1/projects/${isolated.ready.projectId}/reviews/decision`,
      {
        data: { operation: 'captions', readSet: {}, decision: { decision: 'approved' } },
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
    await armLaunch(isolated)
    await browserNavigation(client, `${isolatedURL(isolated.ready)}/?project=${encodeURIComponent(isolated.ready.projectId)}`)
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
    expect(savedBody).toMatchObject({ ok: true, result: 'committed' })
    const project = JSON.parse(await readFile(path.join(root, 'work', 'project.json'), 'utf8'))
    expect(project.operations[0]).toMatchObject({ revision: 2, status: 'stale' })
    expect(project.render.status).toBe('draft')

    const conflict = await client.post(`/v1/projects/${isolated.ready.projectId}/transactions`, {
      data: body, headers: { Origin: isolatedURL(isolated.ready) },
    })
    expect(conflict.status(), `conflict:${await conflict.text()}`).toBe(409)
  } finally {
    await client.dispose()
    await stopSidecar(isolated.process)
    await rm(root, { recursive: true, force: true })
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
  expect(response.status()).toBe(200)
  return { ...isolated, client }
}

function browserNavigation(client: APIRequestContext, url: string) {
  return client.get(url, {
    headers: { 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Site': 'none' },
  })
}

function isolatedURL(message: ReadyMessage) {
  return `http://${message.host}:${message.port}`
}

async function startSidecar(root: string): Promise<StartedSidecar> {
  const child = spawn(process.execPath, [
    path.join(repositoryRoot, 'runtime', 'sidecar.cjs'),
    '--project-root', root,
    '--ui-root', path.join(uiRoot, 'dist'),
  ], {
    cwd: repositoryRoot,
    env: { ...process.env, CAC_PYTHON: process.env.CAC_PYTHON ?? bundledPython },
    stdio: ['pipe', 'pipe', 'pipe'],
  })

  const queuedLines: string[] = []
  const lineWaiters: Array<(line: string) => void> = []
  let stdout = ''
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
  const readLine = () => new Promise<string>((resolve) => {
    const line = queuedLines.shift()
    if (line !== undefined) resolve(line)
    else lineWaiters.push(resolve)
  })
  const message = await new Promise<ReadyMessage>((resolve, reject) => {
    let stderr = ''
    const timeout = setTimeout(() => reject(new Error(`sidecar startup timed out: ${stderr}`)), 10_000)
    void readLine().then((line) => {
      clearTimeout(timeout)
      resolve(JSON.parse(line))
    })
    child.stderr.on('data', (chunk) => { stderr += chunk.toString() })
    child.once('exit', (code) => {
      clearTimeout(timeout)
      reject(new Error(`sidecar exited ${code}: ${stderr}`))
    })
    child.once('error', reject)
  }).catch((error) => {
    child.kill()
    return waitForExit(child, 2_000).then(() => { throw error })
  })
  return { process: child, ready: message, readLine }
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

async function createContentCardsProjectFixture() {
  const root = await mkdtemp(path.join(tmpdir(), 'cut-editor-cards-'))
  await mkdir(path.join(root, 'work', 'content-cards'), { recursive: true })
  await mkdir(path.join(root, 'input'), { recursive: true })
  await writeFile(path.join(root, 'input', 'source.mp4'), 'video')
  const { stdout: sourceStat } = await execFileAsync(bundledPython, ['-c',
    'import os,sys; s=os.stat(sys.argv[1]); print(f"{s.st_size} {s.st_mtime_ns}")',
    path.join(root, 'input', 'source.mp4')])
  const [sourceSize, sourceModifiedNs] = sourceStat.trim().split(' ')
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

async function authoritativeSnapshotEtag(root: string) {
  const { stdout } = await execFileAsync(process.env.CAC_PYTHON ?? bundledPython, [
    '-c',
    'import sys; sys.path.insert(0, sys.argv[1]); from project_snapshot import build_snapshot; print(build_snapshot(sys.argv[2])["snapshot_etag"])',
    path.join(repositoryRoot, 'runtime'),
    root,
  ])
  return stdout.trim()
}
