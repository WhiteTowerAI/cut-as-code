'use strict'

const crypto = require('node:crypto')
const fs = require('node:fs')
const fsp = require('node:fs/promises')
const http = require('node:http')
const path = require('node:path')
const { spawn } = require('node:child_process')
const readline = require('node:readline')

const LOOPBACK = '127.0.0.1'
const LAUNCH_TTL_MS = 60_000
const PROTOCOL_CALL_TIMEOUT_MS = 30_000
const MAX_IMPORT_BYTES = 2 * 1024 * 1024 * 1024
const IMPORT_EXTENSIONS = new Set(['.mp4', '.mov', '.webm', '.mp3', '.wav', '.jpg', '.jpeg', '.png', '.webp', '.gif'])
const HTTP_ROUTE_ALLOWLIST = Object.freeze([
  Object.freeze({ id: 'launch', methods: Object.freeze(['GET']), pattern: /^\/$/ }),
  Object.freeze({ id: 'meta', methods: Object.freeze(['GET']), pattern: /^\/v1\/meta$/ }),
  Object.freeze({ id: 'snapshot', methods: Object.freeze(['GET']), pattern: /^\/v1\/projects\/([^/]+)\/snapshot$/ }),
  Object.freeze({ id: 'transaction', methods: Object.freeze(['POST']), pattern: /^\/v1\/projects\/([^/]+)\/transactions$/ }),
  Object.freeze({ id: 'review', methods: Object.freeze(['POST']), pattern: /^\/v1\/projects\/([^/]+)\/reviews\/decision$/ }),
  Object.freeze({ id: 'export-start', methods: Object.freeze(['POST']), pattern: /^\/v1\/projects\/([^/]+)\/exports$/ }),
  Object.freeze({ id: 'export-status', methods: Object.freeze(['GET']), pattern: /^\/v1\/projects\/([^/]+)\/exports\/status$/ }),
  Object.freeze({ id: 'export-action', methods: Object.freeze(['POST']), pattern: /^\/v1\/projects\/([^/]+)\/exports\/(open|reveal)$/ }),
  Object.freeze({ id: 'resource', methods: Object.freeze(['GET']), pattern: /^\/v1\/projects\/([^/]+)\/resources\/(res_[a-f0-9]+)$/ }),
  Object.freeze({ id: 'import', methods: Object.freeze(['POST']), pattern: /^\/v1\/projects\/([^/]+)\/imports$/ }),
  Object.freeze({ id: 'file', methods: Object.freeze(['GET']), pattern: /^\/v1\/projects\/([^/]+)\/(media|artifacts)\/((?:asset|artifact)_[a-f0-9]+)$/ }),
  Object.freeze({ id: 'layer-frame', methods: Object.freeze(['GET', 'HEAD']), pattern: /^\/v1\/projects\/([^/]+)\/layers\/(layer_[a-f0-9]+)\/frames\/(\d+)$/ }),
  Object.freeze({ id: 'events', methods: Object.freeze(['GET']), pattern: /^\/v1\/projects\/([^/]+)\/events$/ }),
  Object.freeze({ id: 'static', methods: Object.freeze(['GET', 'HEAD']), pattern: /^(?!\/v1(?:\/|$)).+$/ }),
])
const PROTOCOL_VERB_ALLOWLIST = Object.freeze(['open_project', 'get_snapshot', 'get_resource', 'plan.update', 'review.record'])

async function main() {
  const options = parseArguments(process.argv.slice(2))
  const root = await canonicalDirectory(options.projectRoot)
  const uiRoot = await canonicalDirectory(options.uiRoot)
  const protocol = await startProtocolService(__dirname)
  const opened = await protocol.call({ verb: 'open_project', project_root: root })
  if (!opened.ok) throw new Error(opened.error || 'could not open project')

  const state = {
    root,
    uiRoot,
    protocol,
    projectId: opened.project_id,
    launches: new Map(),
    sessions: new Set(),
    clients: new Set(),
    media: new Map(),
    artifacts: new Map(),
    layers: new Map(),
    exportJob: { status: 'idle' },
    exportProcess: null,
  }
  await refreshFiles(state, false)

  const server = http.createServer((request, response) => {
    handleRequest(state, request, response).catch((error) => {
      process.stderr.write(`${error instanceof Error ? error.stack || error.message : String(error)}\n`)
      json(response, 500, { ok: false, error: 'internal error' })
    })
  })
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, LOOPBACK, resolve)
  })
  const address = server.address()
  const origin = `http://${LOOPBACK}:${address.port}`
  state.origin = origin
  state.host = `${LOOPBACK}:${address.port}`
  state.server = server
  state.watcher = watchProject(state)

  const ready = {
    host: LOOPBACK,
    port: address.port,
    projectId: state.projectId,
  }
  process.stdout.write(JSON.stringify(ready) + '\n')
  void refreshLayerSequences(state)

  const control = readline.createInterface({ input: process.stdin, crlfDelay: Infinity })
  control.on('line', (line) => handleControl(state, line))

  let closing = false
  const close = async () => {
    if (closing) return
    closing = true
    state.watcher?.close()
    state.exportProcess?.kill()
    for (const client of state.clients) client.end()
    await protocol.close()
    server.close(() => process.exit(0))
    setTimeout(() => process.exit(0), 2_000).unref()
  }
  process.once('SIGINT', close)
  process.once('SIGTERM', close)
  process.stdin.once('end', close)
}

async function handleRequest(state, request, response) {
  if (request.headers.host !== state.host) return json(response, 400, { ok: false, error: 'invalid host' })
  const url = new URL(request.url, state.origin)
  const route = routeForRequest(request.method, url.pathname)
  if (!route) return json(response, 404, { ok: false, error: 'not found' })

  if (route.id === 'launch') {
    if (url.searchParams.size === 0) {
      if (authorized(state, request)) return serveStatic(state.uiRoot, url.pathname, request.method, response)
      return launchError(response)
    }
    const authorizedProjectNavigation = authorized(state, request)
      && url.searchParams.get('project') === state.projectId
      && (
        url.searchParams.size === 1
        || (url.searchParams.size === 2 && url.searchParams.get('debug') === '1')
      )
      && [...url.searchParams.keys()].every((key) => key === 'project' || key === 'debug')
    if (authorizedProjectNavigation) {
      return serveStatic(state.uiRoot, url.pathname, request.method, response)
    }
    const projectId = url.searchParams.get('project')
    const token = url.searchParams.get('launch')
    const now = Date.now()
    const launch = typeof token === 'string' ? state.launches.get(token) : null
    const directNavigation = request.headers['sec-fetch-mode'] === 'navigate'
      && request.headers['sec-fetch-dest'] === 'document'
      && request.headers['sec-fetch-site'] === 'none'
    for (const [launchToken, value] of state.launches) {
      if (launchIsExpired(value, now)) state.launches.delete(launchToken)
    }
    if (!directNavigation || url.searchParams.size !== 2 || projectId !== state.projectId || !launch || launch.projectId !== projectId || launchIsExpired(launch, now)) {
      return launchError(response)
    }
    state.launches.delete(token)
    const session = crypto.randomBytes(32).toString('base64url')
    state.sessions.add(session)
    response.setHeader('Set-Cookie', `cut_session=${session}; HttpOnly; SameSite=Strict; Path=/`)
    response.writeHead(303, { Location: `/?project=${encodeURIComponent(state.projectId)}`, 'Cache-Control': 'no-store' })
    return response.end()
  }

  if (route.id !== 'static') {
    if (!authorized(state, request)) return json(response, 401, { ok: false, error: 'unauthorized' })
    if (route.id === 'meta') {
      return json(response, 200, { ok: true, projectId: state.projectId, readOnly: true })
    }
    const match = route.match
    if (route.id === 'snapshot' && match[1] === state.projectId) {
      await refreshFiles(state, false)
      const result = await state.protocol.call({ verb: 'get_snapshot', project_id: state.projectId })
      attachPublicFiles(state, result)
      return json(response, result.ok ? 200 : 400, result)
    }
    if (route.id === 'transaction' && match[1] === state.projectId) {
      if (request.headers.origin !== state.origin) return json(response, 403, { ok: false, error: 'invalid origin' })
      const body = await readJson(request)
      const result = await state.protocol.call({
        verb: 'plan.update', project_id: state.projectId, operation: body.operation,
        read_set: body.readSet, review: body.review,
      })
      attachPublicFiles(state, result)
      return json(response, result.status || (result.ok ? 200 : 400), result)
    }
    if (route.id === 'review' && match[1] === state.projectId) {
      if (request.headers.origin !== state.origin) return json(response, 403, { ok: false, error: 'invalid origin' })
      const body = await readJson(request)
      const result = await state.protocol.call({
        verb: 'review.record', project_id: state.projectId, operation: body.operation,
        read_set: body.readSet, decision: body.decision,
      })
      attachPublicFiles(state, result)
      return json(response, result.status || (result.ok ? 200 : 400), result)
    }
    if (route.id === 'export-start' && match[1] === state.projectId) {
      if (request.headers.origin !== state.origin) return json(response, 403, { ok: false, error: 'invalid origin' })
      const body = await readJson(request)
      if (!body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).length !== 0) {
        return json(response, 400, { ok: false, error: 'export accepts no parameters' })
      }
      if (state.exportJob.status === 'running') {
        return json(response, 409, { ok: false, error: 'export is already running', job: publicExportJob(state.exportJob) })
      }
      const job = startExport(state)
      return json(response, 202, { ok: true, job: publicExportJob(job) })
    }
    if (route.id === 'export-status' && match[1] === state.projectId) {
      return json(response, 200, { ok: true, job: publicExportJob(state.exportJob) })
    }
    if (route.id === 'export-action' && match[1] === state.projectId) {
      if (request.headers.origin !== state.origin) return json(response, 403, { ok: false, error: 'invalid origin' })
      const body = await readJson(request)
      if (!body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).length !== 0) {
        return json(response, 400, { ok: false, error: 'export action accepts no parameters' })
      }
      if (state.exportJob.status !== 'succeeded' || typeof state.exportJob.output !== 'string') {
        return json(response, 409, { ok: false, error: 'no completed export is available' })
      }
      const output = await fsp.realpath(path.resolve(state.exportJob.output)).catch(() => null)
      if (!output || !isContained(state.root, output) || !(await isFile(output))) {
        return json(response, 409, { ok: false, error: 'the exported video is unavailable' })
      }
      try {
        await openExportPath(output, match[2])
        return json(response, 200, { ok: true })
      } catch {
        return json(response, 503, { ok: false, error: 'the system could not open the exported video' })
      }
    }
    if (route.id === 'resource' && match[1] === state.projectId) {
      const result = await state.protocol.call({
        verb: 'get_resource', project_id: state.projectId, resource_id: match[2],
      })
      return json(response, result.ok ? 200 : 404, result)
    }
    if (route.id === 'import' && match[1] === state.projectId) {
      if (request.headers.origin !== state.origin) return json(response, 403, { ok: false, error: 'invalid origin' })
      try {
        const imported = await writeMultipartImportedFile(state.root, request)
        await refreshFiles(state, false)
        const result = await state.protocol.call({ verb: 'get_snapshot', project_id: state.projectId })
        attachPublicFiles(state, result)
        notifyProjectChange(state)
        return json(response, result.ok ? 201 : 400, { ...result, import: imported })
      } catch (error) {
        return json(response, 400, { ok: false, error: error instanceof Error ? error.message : 'could not import file' })
      }
    }
    if (route.id === 'file' && match[1] === state.projectId) {
      const registry = match[2] === 'media' ? state.media : state.artifacts
      const item = registry.get(match[3])
      if (!item) return json(response, 404, { ok: false, error: 'unknown resource' })
      return streamFile(state, request, response, item)
    }
    if (route.id === 'layer-frame' && match[1] === state.projectId) {
      const layer = state.layers.get(match[2])
      const frameNumber = Number(match[3])
      const item = Number.isSafeInteger(frameNumber) ? layer?.frames.get(frameNumber) : null
      if (!item) return json(response, 404, { ok: false, error: 'unknown resource' })
      return streamFile(state, request, response, item)
    }
    if (route.id === 'events' && match[1] === state.projectId) {
      response.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      })
      response.write('event: ready\ndata: {}\n\n')
      state.clients.add(response)
      request.once('close', () => state.clients.delete(response))
      return
    }
    return json(response, 404, { ok: false, error: 'not found' })
  }

  if (!authorized(state, request)) return json(response, 401, { ok: false, error: 'unauthorized' })
  return serveStatic(state.uiRoot, url.pathname, request.method, response)
}

function startExport(state) {
  const job = {
    id: `export_${crypto.randomBytes(12).toString('hex')}`,
    status: 'running',
    stage: 'rendering',
    startedAt: new Date().toISOString(),
  }
  state.exportJob = job
  const executable = process.env.CAC_PYTHON || 'python'
  const script = path.join(__dirname, 'export_project.py')
  const child = spawn(executable, [script, state.root], {
    cwd: __dirname,
    env: process.env,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  state.exportProcess = child
  let stdout = ''
  let stderr = ''
  const append = (current, chunk) => (current + chunk.toString()).slice(-65_536)
  child.stdout.on('data', (chunk) => { stdout = append(stdout, chunk) })
  child.stderr.on('data', (chunk) => { stderr = append(stderr, chunk) })
  child.once('error', () => {
    if (state.exportJob.id !== job.id) return
    state.exportProcess = null
    state.exportJob = {
      ...job,
      status: 'failed',
      finishedAt: new Date().toISOString(),
      error: 'Export worker could not start',
    }
  })
  child.once('exit', (code) => {
    if (state.exportJob.id !== job.id) return
    state.exportProcess = null
    const line = stdout.trim().split(/\r?\n/).filter(Boolean).at(-1)
    let result
    try { result = line ? JSON.parse(line) : null } catch { result = null }
    if (!(code === 0 && result?.ok)) {
      const detail = stderr.trim() || stdout.trim() || `export worker exited with code ${code}`
      process.stderr.write(`[${job.id}] ${detail}\n`)
    }
    state.exportJob = code === 0 && result?.ok
      ? {
          ...job,
          status: 'succeeded',
          stage: 'complete',
          finishedAt: new Date().toISOString(),
          output: result.output,
          size: result.size,
        }
      : {
          ...job,
          status: 'failed',
          finishedAt: new Date().toISOString(),
          error: summarizeExportFailure(stderr || stdout, state.root),
          _log: stderr,
        }
  })
  return job
}

function summarizeExportFailure(output, projectRoot) {
  const lines = String(output || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  const fallback = 'Export failed. Review the project render state.'
  const summary = lines.at(-1) || fallback
  const escapedRoot = String(projectRoot || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return summary
    .replace(escapedRoot ? new RegExp(escapedRoot, 'gi') : /$^/, '[project]')
    .replace(/[A-Za-z]:(?:\\\\|\\)[^'"\r\n]+/g, '[local path]')
    .replace(/[A-Za-z]:\\(?:[^\\\s:]+\\)*[^\\\s:]*/g, '[local path]')
    .replace(/\/(?:[^/\s:]+\/)+[^/\s:]*/g, '[local path]')
    .slice(0, 500)
}

function openExportPath(output, action, spawnProcess = spawn, platform = process.platform) {
  let command
  let args
  if (platform === 'win32') {
    command = action === 'reveal' ? 'explorer.exe' : 'powershell.exe'
    args = action === 'reveal'
      ? ['/select,', output]
      : ['-NoProfile', '-NonInteractive', '-Command', 'Start-Process -FilePath $args[0]', output]
  } else if (platform === 'darwin') {
    command = 'open'
    args = action === 'reveal' ? ['-R', output] : [output]
  } else {
    command = action === 'reveal' ? 'xdg-open' : 'xdg-open'
    args = [action === 'reveal' ? path.dirname(output) : output]
  }
  return new Promise((resolve, reject) => {
    const child = spawnProcess(command, args, { detached: true, stdio: 'ignore', windowsHide: true })
    child.once('spawn', () => {
      child.unref()
      resolve()
    })
    child.once('error', reject)
  })
}

function publicExportJob(job) {
  if (!job || job.status === 'idle') return { status: 'idle' }
  return Object.fromEntries(Object.entries(job).filter(([key]) => !key.startsWith('_')))
}

function routeForRequest(method, pathname) {
  for (const route of HTTP_ROUTE_ALLOWLIST) {
    if (!route.methods.includes(method)) continue
    const match = route.pattern.exec(pathname)
    if (match) return { id: route.id, match }
  }
  return null
}

function handleControl(state, line) {
  let request
  try { request = JSON.parse(line) } catch { return process.stdout.write(`${JSON.stringify({ id: null, ok: false, error: 'invalid control message' })}\n`) }
  if (!Number.isInteger(request.id) || request.command !== 'arm_launch') {
    return process.stdout.write(`${JSON.stringify({ id: request.id ?? null, ok: false, error: 'unsupported control command' })}\n`)
  }
  const token = crypto.randomBytes(32).toString('base64url')
  state.launches.set(token, { projectId: state.projectId, expiresAt: Date.now() + LAUNCH_TTL_MS })
  const url = `${state.origin}/?project=${encodeURIComponent(state.projectId)}&launch=${token}`
  process.stdout.write(`${JSON.stringify({ id: request.id, ok: true, url })}\n`)
}

function watchProject(state) {
  let timer
  const changed = () => {
    clearTimeout(timer)
    timer = setTimeout(async () => {
      await refreshFiles(state).catch(() => {})
      notifyProjectChange(state)
    }, 50)
  }
  const watchers = []
  for (const name of ['work', 'input', 'review', 'final']) {
    const directory = path.join(state.root, name)
    if (!fs.existsSync(directory)) continue
    try { watchers.push(fs.watch(directory, { recursive: true }, changed)) } catch { watchers.push(fs.watch(directory, changed)) }
  }
  return { close: () => { clearTimeout(timer); for (const watcher of watchers) watcher.close() } }
}

function notifyProjectChange(state) {
  for (const client of state.clients) client.write(`event: project-change\ndata: ${JSON.stringify({ projectId: state.projectId })}\n\n`)
}

async function refreshFiles(state, refreshLayers = true) {
  state.media = await collectFiles(state.root, ['input'], 'asset')
  state.artifacts = await collectFiles(state.root, ['review'], 'artifact')
  if (refreshLayers) state.layers = await collectLayerSequences(state.root)
}

async function refreshLayerSequences(state) {
  try {
    state.layers = await collectLayerSequences(state.root)
  } catch {
    return
  }
  notifyProjectChange(state)
}

async function collectLayerSequences(root) {
  const result = new Map()
  const projectPath = path.join(root, 'work', 'project.json')
  let project
  try {
    project = await readBoundJson(root, projectPath)
  } catch {
    return result
  }
  const operations = Array.isArray(project.operations) ? project.operations : []
  for (const operation of operations) {
    if (!operation || !['captions', 'content-cards', 'graphic-motion'].includes(operation.id) || typeof operation.plan !== 'string') continue
    let plan
    try {
      plan = await readBoundJson(root, path.resolve(root, 'work', operation.plan))
    } catch {
      continue
    }
    if (operation.id === 'graphic-motion') {
      for (const cue of Array.isArray(plan.cues) ? plan.cues : []) {
        const render = cue?.render
        if (!cue || cue.status !== 'verified' || typeof cue.id !== 'string' || render?.asset_type !== 'image-sequence') continue
        const sequence = await collectLayerSequence(root, render)
        if (sequence) result.set(layerIdFor(operation.id, cue.id), sequence)
      }
      continue
    }
    const cues = operation.id === 'captions' ? plan.cues : plan.cards
    for (let index = 0; index < (Array.isArray(cues) ? cues.length : 0); index += 1) {
      const cue = cues[index]
      const cueId = cueIdFor(operation.id, cue, index)
      if (!cue || !cueId) continue
      const programRange = operation.id === 'captions'
        ? cue.program_range ?? { start_s: cue.start, end_s: cue.end }
        : { start_s: cue.program_start_s, end_s: cue.program_start_s + cue.duration_s }
      let render = Array.isArray(operation.render) ? operation.render[index] : operation.render
      if (operation.id === 'content-cards' && render?.asset_type !== 'image-sequence') {
        render = await materializeCardSequence(root, plan, cue, render)
      }
      const sequence = await collectCueSequence(root, render, programRange, operation.id === 'captions')
      if (sequence) result.set(layerIdFor(operation.id, cueId), sequence)
    }
  }
  await addSequenceBounds(result)
  return result
}

async function collectCueSequence(root, render, programRange, fullProgram) {
  if (!render || render.asset_type !== 'image-sequence' || typeof render.asset !== 'string'
      || typeof render.pattern !== 'string' || !render.fps || !programRange) return null
  const fps = Number(render.fps.num) / Number(render.fps.den)
  if (!(fps > 0) || !Number.isFinite(programRange.start_s) || !Number.isFinite(programRange.end_s)) return null
  const count = Math.max(1, Math.ceil((programRange.end_s - programRange.start_s) * fps))
  const sourceStart = Number.isInteger(render.start_number) ? render.start_number : 1
  const first = fullProgram ? sourceStart + Math.floor(programRange.start_s * fps) : sourceStart
  const assetRoot = path.resolve(root, 'work', render.asset)
  if (!isContained(root, assetRoot)) return null
  const frames = new Map()
  for (let index = 0; index < count; index += 1) {
    const sourceNumber = first + index
    const name = printfFrameName(render.pattern, sourceNumber)
    if (!name) return null
    const file = path.resolve(assetRoot, name)
    if (!isContained(assetRoot, file)) return null
    try {
      const real = await fsp.realpath(file)
      if (real !== file || (await fsp.lstat(file)).isSymbolicLink()) return null
      const stat = await fsp.stat(real)
      if (!stat.isFile()) return null
      frames.set(sourceStart + index, { id: `${sourceStart + index}`, name, size: stat.size, path: real, sha256: await hashFile(real), mediaType: 'image/png' })
    } catch { return null }
  }
  return { frames, pattern: render.pattern, startNumber: sourceStart, fps: render.fps, frameCount: frames.size }
}

async function materializeCardSequence(root, plan, cue, contribution) {
  if (!contribution || typeof contribution.asset !== 'string') return null
  const source = path.resolve(root, 'work', contribution.asset)
  if (!isContained(root, source) || !(await isFile(source))) return null
  const fps = cue.renderer?.fps ?? plan.renderer_recipe?.fps ?? { num: 30000, den: 1001 }
  const output = path.join(root, 'work', 'cache', 'editor-preview', 'content-cards', cue.id)
  await fsp.mkdir(output, { recursive: true })
  const pattern = 'frame_%06d.png'
  const expected = Math.max(1, Math.ceil(Number(cue.duration_s) * Number(fps.num) / Number(fps.den)))
  const existing = (await fsp.readdir(output).catch(() => [])).filter((name) => /^frame_\d{6}\.png$/.test(name))
  if (existing.length < expected) {
    await runProcess('ffmpeg', ['-y', '-i', source, '-vf', `fps=${fps.num}/${fps.den}`, '-frames:v', `${expected}`, path.join(output, pattern)])
  }
  return { asset_type: 'image-sequence', asset: path.relative(path.join(root, 'work'), output), pattern, start_number: 1, fps }
}

async function addSequenceBounds(sequences) {
  if (!sequences.size) return
  const groups = Object.fromEntries([...sequences].map(([id, sequence]) => [id, [...sequence.frames.values()].map((frame) => frame.path)]))
  const executable = process.env.CAC_PYTHON || 'python'
  const output = await runProcess(executable, [path.join(__dirname, 'sequence_bounds.py')], JSON.stringify(groups))
  const bounds = JSON.parse(output.stdout)
  for (const [id, sequence] of sequences) sequence.contentBounds = bounds[id]
}

function runProcess(command, args, input) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (chunk) => { stdout += chunk })
    child.stderr.on('data', (chunk) => { stderr += chunk })
    child.once('error', reject)
    child.once('exit', (code) => code === 0 ? resolve({ stdout, stderr }) : reject(new Error(stderr || `${command} exited ${code}`)))
    child.stdin.end(input ?? '')
  })
}

async function collectLayerSequence(root, render) {
  if (typeof render.asset !== 'string' || typeof render.pattern !== 'string'
      || !Number.isInteger(render.start_number) || render.start_number < 0
      || !Array.isArray(render.frames) || !render.frames.length) return null
  const assetRoot = path.resolve(root, 'work', render.asset)
  if (!isContained(root, assetRoot)) return null
  const frames = new Map()
  for (let index = 0; index < render.frames.length; index += 1) {
    const binding = render.frames[index]
    const frameNumber = render.start_number + index
    const name = printfFrameName(render.pattern, frameNumber)
    if (!name || !binding || typeof binding.path !== 'string' || !/^[a-f0-9]{64}$/.test(binding.sha256 ?? '')) return null
    const expected = path.resolve(assetRoot, name)
    const declared = path.resolve(root, binding.path)
    if (expected !== declared || !isContained(assetRoot, declared) || !isContained(root, declared)) return null
    try {
      const real = await fsp.realpath(declared)
      if (real !== declared || !isContained(assetRoot, real) || (await fsp.lstat(declared)).isSymbolicLink()) return null
      const stat = await fsp.stat(real)
      if (!stat.isFile() || await hashFile(real) !== binding.sha256) return null
      frames.set(frameNumber, {
        id: `${frameNumber}`,
        name,
        size: stat.size,
        path: real,
        sha256: binding.sha256,
        mediaType: 'image/png',
      })
    } catch {
      return null
    }
  }
  return { frames }
}

async function readBoundJson(root, file) {
  const resolved = path.resolve(file)
  if (!isContained(root, resolved)) throw new Error('outside project')
  const real = await fsp.realpath(resolved)
  if (real !== resolved || !isContained(root, real) || (await fsp.lstat(resolved)).isSymbolicLink()) {
    throw new Error('linked project JSON')
  }
  return JSON.parse(await fsp.readFile(real, 'utf8'))
}

function layerIdFor(operationId, cueId) {
  return `layer_${crypto.createHash('sha256').update(`${operationId}:${cueId}`).digest('hex').slice(0, 24)}`
}

function cueIdFor(operationId, cue, index) {
  if (typeof cue?.id === 'string' && cue.id) return cue.id
  return operationId === 'captions' ? `cue-${String(index + 1).padStart(3, '0')}` : null
}

function printfFrameName(pattern, frameNumber) {
  const match = /^([A-Za-z0-9._-]*)%0?([1-9][0-9]*)d([A-Za-z0-9._-]*)$/.exec(pattern)
  if (!match || path.basename(pattern) !== pattern) return null
  return `${match[1]}${String(frameNumber).padStart(Number(match[2]), '0')}${match[3]}`
}

async function collectFiles(root, directories, prefix) {
  const result = new Map()
  for (const directory of directories) {
    const base = path.join(root, directory)
    if (!fs.existsSync(base)) continue
    for await (const file of walk(base)) {
      const real = await fsp.realpath(file)
      if (!isContained(root, real)) continue
      const stat = await fsp.stat(real)
      if (!stat.isFile()) continue
      const relative = path.relative(root, real).split(path.sep).join('/')
      const id = `${prefix}_${crypto.createHash('sha256').update(relative).digest('hex').slice(0, 24)}`
      result.set(id, {
        id,
        name: path.basename(real),
        size: stat.size,
        path: real,
        sha256: await hashFile(real),
        mediaType: mediaType(real),
      })
    }
  }
  return result
}

async function* walk(directory) {
  for (const entry of await fsp.readdir(directory, { withFileTypes: true })) {
    const item = path.join(directory, entry.name)
    if (entry.isDirectory()) yield* walk(item)
    else if (entry.isFile() || entry.isSymbolicLink()) yield item
  }
}

function publicFiles(registry, projectId, collection) {
  return [...registry.values()].map(({ id, name, size, sha256, mediaType }) => ({
    id,
    name,
    size,
    sha256,
    media_type: mediaType,
    url: `/v1/projects/${encodeURIComponent(projectId)}/${collection}/${encodeURIComponent(id)}`,
  }))
}

function attachPublicFiles(state, result) {
  if (!result?.snapshot) return result
  result.snapshot.media = publicFiles(state.media, state.projectId, 'media')
  result.snapshot.artifacts = publicFiles(state.artifacts, state.projectId, 'artifacts')
  if (result.snapshot.view?.source_media_id && !state.media.has(result.snapshot.view.source_media_id)) {
    delete result.snapshot.view.source_media_id
  }
  if (Array.isArray(result.snapshot.view?.layers)) {
    result.snapshot.view.layers = result.snapshot.view.layers.map((layer) => {
      const sequence = state.layers.get(layer.id)
      if (!sequence) return layer
      return {
        ...layer,
        media_type: 'image-sequence',
        image_sequence: {
          pattern: sequence.pattern ?? layer.image_sequence?.pattern,
          start_number: sequence.startNumber ?? layer.image_sequence?.start_number,
          fps: sequence.fps ?? layer.image_sequence?.fps,
          frame_count: sequence.frameCount ?? layer.image_sequence?.frame_count,
          content_bounds: sequence.contentBounds ?? layer.image_sequence?.content_bounds,
          frame_url_template: `/v1/projects/${encodeURIComponent(state.projectId)}/layers/${encodeURIComponent(layer.id)}/frames/%d`,
        },
      }
    })
  }
  return result
}

function mediaType(file) {
  return ({
    '.html': 'text/html; charset=utf-8', '.htm': 'text/html; charset=utf-8',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
    '.gif': 'image/gif', '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
    '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.json': 'application/json; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8', '.md': 'text/plain; charset=utf-8',
  })[path.extname(file).toLowerCase()] ?? 'application/octet-stream'
}

async function hashFile(file) {
  const hash = crypto.createHash('sha256')
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk)
  return hash.digest('hex')
}

async function streamFile(state, request, response, item) {
  const prepared = await prepareStreamItem(state, item)
  if (!prepared) return json(response, 404, { ok: false, error: 'resource changed' })
  const { handle, size, mediaType: currentMediaType } = prepared
  const range = parseRange(request.headers.range, size)
  if (range === false) {
    await closeFileHandle(handle)
    response.writeHead(416, { 'Content-Range': `bytes */${size}` })
    return response.end()
  }
  const start = range?.start ?? 0
  const end = range?.end ?? size - 1
  response.writeHead(range ? 206 : 200, {
    'Accept-Ranges': 'bytes',
    'Content-Length': Math.max(0, end - start + 1),
    ...(range ? { 'Content-Range': `bytes ${start}-${end}/${size}` } : {}),
    'Content-Type': currentMediaType,
    'X-Content-Type-Options': 'nosniff',
    ...(currentMediaType.startsWith('text/html') ? {
      'Content-Security-Policy': "sandbox; default-src 'none'; img-src 'self' data:; media-src 'self'; style-src 'unsafe-inline'",
    } : {}),
  })
  if (request.method === 'HEAD' || size === 0) {
    await closeFileHandle(handle)
    return response.end()
  }
  const stream = fs.createReadStream(null, { fd: handle.fd, start, end, autoClose: false })
  let closed = false
  const close = () => {
    if (closed) return
    closed = true
    void closeFileHandle(handle)
  }
  stream.once('close', close)
  response.once('finish', close)
  response.once('close', close)
  stream.pipe(response)
}

async function prepareStreamItem(state, item) {
  let resolved
  try {
    resolved = await fsp.realpath(item.path)
    if (!isContained(state.root, resolved) || resolved !== item.path) return null
    if ((await fsp.lstat(item.path)).isSymbolicLink()) return null
    const handle = await fsp.open(resolved, 'r')
    let keepOpen = false
    try {
      const reopened = await fsp.realpath(item.path)
      if (!isContained(state.root, reopened) || reopened !== resolved) return null
      const stat = await handle.stat()
      const pathStat = await fsp.stat(reopened)
      if (!stat.isFile() || !sameFileIdentity(stat, pathStat) || stat.size !== item.size) return null
      const sha256 = await hashFileHandle(handle, stat.size)
      if (sha256 !== item.sha256) return null
      keepOpen = true
      return { handle, size: stat.size, mediaType: item.mediaType }
    } finally {
      if (!keepOpen) await closeFileHandle(handle)
    }
  } catch {
    return null
  }
}

function sameFileIdentity(left, right) {
  return left.dev === right.dev && left.ino === right.ino
}

async function hashFileHandle(handle, size) {
  const hash = crypto.createHash('sha256')
  const buffer = Buffer.allocUnsafe(64 * 1024)
  let position = 0
  while (position < size) {
    const length = Math.min(buffer.length, size - position)
    const result = await handle.read(buffer, 0, length, position)
    if (result.bytesRead === 0) throw new Error('file changed while reading')
    hash.update(buffer.subarray(0, result.bytesRead))
    position += result.bytesRead
  }
  return hash.digest('hex')
}

async function closeFileHandle(handle) {
  await handle.close().catch(() => {})
}

function parseRange(value, size) {
  if (!value) return null
  const match = /^bytes=(\d*)-(\d*)$/.exec(value)
  if (!match || size === 0) return false
  let start
  let end
  if (match[1] === '') {
    const suffix = Number(match[2])
    if (!Number.isInteger(suffix) || suffix <= 0) return false
    start = Math.max(0, size - suffix)
    end = size - 1
  } else {
    start = Number(match[1])
    end = match[2] === '' ? size - 1 : Number(match[2])
  }
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || start >= size || end < start) return false
  return { start, end: Math.min(end, size - 1) }
}

async function serveStatic(root, pathname, method, response) {
  let decoded
  try { decoded = decodeURIComponent(pathname) } catch { return json(response, 400, { ok: false, error: 'invalid path' }) }
  const relative = decoded === '/' ? 'index.html' : decoded.replace(/^\/+/, '')
  let target = path.resolve(root, relative)
  if (!isContained(root, target)) return json(response, 404, { ok: false, error: 'not found' })
  if (!await isFile(target)) target = path.join(root, 'index.html')
  if (!isContained(root, target) || !await isFile(target)) return json(response, 404, { ok: false, error: 'not found' })
  target = await fsp.realpath(target)
  if (!isContained(root, target)) return json(response, 404, { ok: false, error: 'not found' })
  const stat = await fsp.stat(target)
  const extension = path.extname(target)
  const contentTypes = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.woff': 'font/woff', '.woff2': 'font/woff2' }
  response.writeHead(200, { 'Content-Type': contentTypes[extension] || 'application/octet-stream', 'Content-Length': stat.size })
  if (method === 'HEAD') return response.end()
  fs.createReadStream(target).pipe(response)
}

function authorized(state, request) {
  const cookies = Object.fromEntries((request.headers.cookie || '').split(';').map((part) => part.trim().split('=')))
  return typeof cookies.cut_session === 'string' && state.sessions.has(cookies.cut_session)
}

function readJson(request) {
  return new Promise((resolve, reject) => {
    let body = ''
    request.setEncoding('utf8')
    request.on('data', (chunk) => {
      body += chunk
      if (body.length > 16_384) request.destroy()
    })
    request.once('end', () => {
      try { resolve(JSON.parse(body)) } catch { reject(new Error('invalid JSON')) }
    })
    request.once('error', reject)
  })
}

function importName(value) {
  if (typeof value !== 'string' || !value || value.length > 180 || value !== path.basename(value) || value === '.' || value === '..' || /[\0-\x1f]/.test(value)) {
    throw new Error('invalid import file name')
  }
  if (!IMPORT_EXTENSIONS.has(path.extname(value).toLowerCase())) throw new Error('unsupported import file type')
  return value
}

async function importDirectory(root) {
  const directory = path.join(root, 'input')
  await fsp.mkdir(directory, { recursive: true })
  const real = await fsp.realpath(directory)
  if (real !== directory || !isContained(root, real) || (await fsp.lstat(directory)).isSymbolicLink()) {
    throw new Error('project input directory is unsafe')
  }
  return real
}

async function createImportWriter(root, name) {
  const directory = await importDirectory(root)
  const safeName = importName(name)
  const temporary = path.join(directory, `.import-${crypto.randomBytes(16).toString('hex')}.tmp`)
  const handle = await fsp.open(temporary, 'wx')
  let size = 0
  let closed = false
  const close = async () => {
    if (closed) return
    closed = true
    await handle.close()
  }
  return {
    async write(chunk) {
      const value = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
      size += value.length
      if (size > MAX_IMPORT_BYTES) throw new Error('import file is too large')
      await handle.write(value)
    },
    async finish() {
      await close()
      const parsed = path.parse(safeName)
      try {
        for (let index = 1; ; index += 1) {
          const candidateName = index === 1 ? safeName : `${parsed.name}-${index}${parsed.ext}`
          const candidate = path.join(directory, candidateName)
          try {
            await fsp.link(temporary, candidate)
            return { name: candidateName, size, media_type: mediaType(candidate) }
          } catch (error) {
            if (error?.code !== 'EEXIST') throw error
          }
        }
      } finally {
        await fsp.unlink(temporary).catch(() => {})
      }
    },
    async abort() {
      await close().catch(() => {})
      await fsp.unlink(temporary).catch(() => {})
    },
  }
}

async function writeImportedFile(root, name, source) {
  const writer = await createImportWriter(root, name)
  try {
    for await (const chunk of source) await writer.write(chunk)
    return await writer.finish()
  } catch (error) {
    await writer.abort()
    throw error
  }
}

async function writeMultipartImportedFile(root, request) {
  const contentType = request.headers['content-type']
  const match = typeof contentType === 'string' ? /^multipart\/form-data;\s*boundary=(?:"([^"]+)"|([^;\s]+))/i.exec(contentType) : null
  const boundary = match?.[1] ?? match?.[2]
  if (!boundary) throw new Error('import must use multipart form data')
  const delimiter = Buffer.from(`\r\n--${boundary}`)
  const opening = Buffer.from(`--${boundary}\r\n`)
  let pending = Buffer.alloc(0)
  let writer = null
  let completed = false
  try {
    for await (const chunk of request) {
      pending = Buffer.concat([pending, Buffer.from(chunk)])
      if (!writer) {
        const headerEnd = pending.indexOf('\r\n\r\n')
        if (headerEnd < 0) {
          if (pending.length > 16_384) throw new Error('import headers are too large')
          continue
        }
        if (!pending.subarray(0, opening.length).equals(opening)) throw new Error('invalid import form data')
        const headers = pending.subarray(opening.length, headerEnd).toString('utf8')
        const disposition = /content-disposition:\s*form-data;\s*name="asset";\s*filename="([^"]+)"/i.exec(headers)
        if (!disposition) throw new Error('import requires one asset file')
        writer = await createImportWriter(root, disposition[1])
        pending = pending.subarray(headerEnd + 4)
      }
      const boundaryIndex = pending.indexOf(delimiter)
      if (boundaryIndex >= 0) {
        await writer.write(pending.subarray(0, boundaryIndex))
        pending = pending.subarray(boundaryIndex + delimiter.length)
        if (pending.length < 2) continue
        if (!pending.subarray(0, 2).equals(Buffer.from('--'))) throw new Error('only one import file is allowed')
        completed = true
        request.resume()
        break
      }
      const retained = delimiter.length + 4
      if (pending.length > retained) {
        await writer.write(pending.subarray(0, pending.length - retained))
        pending = pending.subarray(pending.length - retained)
      }
    }
    if (!writer || !completed) throw new Error('invalid import form data')
    return await writer.finish()
  } catch (error) {
    await writer?.abort()
    throw error
  }
}

function json(response, status, value) {
  if (response.headersSent) return response.end()
  const body = JSON.stringify(value)
  response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(body) })
  response.end(body)
}

function launchError(response) {
  const body = '<!doctype html><title>Editor launch unavailable</title><h1>Editor launch unavailable</h1><p>This editor launch link is invalid, expired, or has already been used. Return to Cut as Code and open the editor again.</p>'
  response.writeHead(401, { 'Content-Type': 'text/html; charset=utf-8', 'Content-Length': Buffer.byteLength(body), 'Cache-Control': 'no-store' })
  response.end(body)
}

function launchIsExpired(launch, now = Date.now()) {
  return launch.expiresAt <= now
}

function isContained(root, target) {
  const relative = path.relative(root, target)
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

async function canonicalDirectory(value) {
  if (!value) throw new Error('directory is required')
  const real = await fsp.realpath(path.resolve(value))
  if (!(await fsp.stat(real)).isDirectory()) throw new Error('directory is required')
  return real
}

async function isFile(value) {
  try { return (await fsp.stat(value)).isFile() } catch { return false }
}

function parseArguments(args) {
  const options = {}
  for (let index = 0; index < args.length; index += 2) {
    if (args[index] === '--project-root') options.projectRoot = args[index + 1]
    else if (args[index] === '--ui-root') options.uiRoot = args[index + 1]
    else throw new Error(`unknown argument: ${args[index]}`)
  }
  return options
}

async function startProtocolService(runtimeRoot) {
  const script = path.join(runtimeRoot, 'protocol_service.py')
  const candidates = [process.env.CAC_PYTHON, process.platform === 'win32' ? 'python.exe' : 'python3', 'python'].filter(Boolean)
  let child
  for (const executable of candidates) {
    try {
      child = spawn(executable, [script], { cwd: runtimeRoot, stdio: ['pipe', 'pipe', 'pipe'] })
      await new Promise((resolve, reject) => {
        child.once('spawn', resolve)
        child.once('error', reject)
      })
      break
    } catch { child = null }
  }
  if (!child) throw new Error('Python runtime unavailable')
  const lines = readline.createInterface({ input: child.stdout })
  child.stderr.pipe(process.stderr)
  const pending = []
  lines.on('line', (line) => {
    const request = pending.shift()
    if (!request) return
    clearTimeout(request.timer)
    try { request.resolve(JSON.parse(line)) } catch (error) { request.reject(error) }
  })
  child.once('exit', () => {
    while (pending.length) {
      const request = pending.shift()
      clearTimeout(request.timer)
      request.reject(new Error('protocol service stopped'))
    }
  })
  return {
    call(value) {
      if (!PROTOCOL_VERB_ALLOWLIST.includes(value.verb)) return Promise.reject(new Error('unsupported protocol verb'))
      return new Promise((resolve, reject) => {
        const request = { resolve, reject, timer: null }
        request.timer = setTimeout(() => {
          reject(new Error('protocol service timed out'))
          child.kill()
        }, PROTOCOL_CALL_TIMEOUT_MS)
        pending.push(request)
        child.stdin.write(JSON.stringify(value) + '\n')
      })
    },
    close() {
      if (child.exitCode !== null) return Promise.resolve()
      const exited = new Promise((resolve) => child.once('exit', resolve))
      lines.close()
      child.stdin.end()
      child.kill()
      return Promise.race([
        exited,
        new Promise((resolve) => setTimeout(resolve, 1_000)),
      ])
    },
  }
}

module.exports = { HTTP_ROUTE_ALLOWLIST, LAUNCH_TTL_MS, PROTOCOL_CALL_TIMEOUT_MS, MAX_IMPORT_BYTES, launchIsExpired, routeForRequest, openExportPath, summarizeExportFailure, cueIdFor, writeImportedFile }

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`)
    process.exitCode = 1
  })
}
