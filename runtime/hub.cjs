'use strict'

const crypto = require('node:crypto')
const fsp = require('node:fs/promises')
const http = require('node:http')
const path = require('node:path')
const readline = require('node:readline')
const { spawn } = require('node:child_process')
const { challengeProof, locatorProof } = require('./hub-trust.cjs')

const LOOPBACK = '127.0.0.1'
const LAUNCH_TTL_MS = 60_000
const IDLE_RUNTIME_TTL_MS = 30 * 60_000

async function main() {
  const options = parseArguments(process.argv.slice(2))
  const pluginRoot = await canonicalDirectory(options.pluginRoot)
  const dataRoot = path.resolve(options.dataRoot)
  const uiRoot = await canonicalDirectory(path.join(pluginRoot, 'ui', 'dist'))
  await fsp.mkdir(dataRoot, { recursive: true, mode: 0o700 })
  const lockPath = path.join(dataRoot, 'hub.lock')
  const canonicalLockPath = lockPath
  const canonicalLocatorPath = path.join(dataRoot, 'hub.json')
  const locatorPath = path.join(dataRoot, options.locatorName || 'hub.json')
  const activeLockPath = locatorPath === canonicalLocatorPath
    ? canonicalLockPath
    : locatorPath.replace(/\.json$/, '.lock')
  const lock = await readJson(activeLockPath)
  if (!lock || lock.token !== options.lockToken) throw new Error('editor Hub startup lock is unavailable')

  const state = {
    pluginRoot,
    dataRoot,
    uiRoot,
    lockPath: activeLockPath,
    canonicalLockPath,
    locatorPath,
    canonicalLocatorPath,
    candidate: locatorPath !== canonicalLocatorPath,
    registryPath: path.join(dataRoot, 'projects.json'),
    lockToken: options.lockToken,
    instanceId: crypto.randomBytes(16).toString('hex'),
    controlToken: crypto.randomBytes(32).toString('base64url'),
    protocolVersion: options.protocolVersion,
    runtimeVersion: options.runtimeVersion,
    capabilities: options.capabilities,
    updatePending: null,
    updateAttempting: false,
    handoffPreparing: false,
    sidecars: new Map(),
    startingSidecars: new Map(),
    launches: new Map(),
    sessions: new Set(),
    registry: await loadRegistry(path.join(dataRoot, 'projects.json')),
    closing: false,
  }
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
  state.server = server
  state.idleTimer = setInterval(() => { void reclaimIdleRuntimes(state) }, 60_000)
  state.idleTimer.unref()
  state.updateTimer = setInterval(() => { void maybeAdvancePendingUpdate(state) }, 1_000)
  state.updateTimer.unref()
  const address = server.address()
  state.host = `${LOOPBACK}:${address.port}`
  const locator = {
    schemaVersion: 2,
    host: LOOPBACK,
    port: address.port,
    pid: process.pid,
    instanceId: state.instanceId,
    controlToken: state.controlToken,
    protocolVersion: state.protocolVersion,
    runtimeVersion: state.runtimeVersion,
    capabilities: state.capabilities,
  }
  locator.startupProof = locatorProof(state.lockToken, locator)
  await writeJsonAtomic(locatorPath, locator)
  const close = () => closeHub(state)
  process.once('SIGINT', close)
  process.once('SIGTERM', close)
}

async function handleRequest(state, request, response) {
  if (request.headers.host !== state.host) return json(response, 400, { ok: false, error: 'invalid host' })
  const url = new URL(request.url, `http://${state.host}`)

  if (request.headers.authorization === `Bearer ${state.controlToken}`) {
    if (request.method === 'GET' && url.pathname === '/v1/health') {
      return json(response, 200, {
        ok: true, instanceId: state.instanceId, pid: process.pid,
        protocolVersion: state.protocolVersion, runtimeVersion: state.runtimeVersion,
        capabilities: state.capabilities,
      })
    }
    if (request.method === 'POST' && url.pathname === '/v1/challenge') {
      const body = await readRequestJson(request)
      if (!/^[A-Za-z0-9_-]{43}$/.test(body?.challenge || '')) {
        return json(response, 400, { ok: false, error: 'invalid challenge' })
      }
      return json(response, 200, {
        ok: true,
        instanceId: state.instanceId,
        pid: process.pid,
        proof: challengeProof(state.controlToken, body.challenge, state.instanceId, process.pid),
      })
    }
    if (request.method === 'POST' && url.pathname === '/v1/projects/open') {
      if (state.handoffPreparing) return json(response, 503, { ok: false, error: 'editor Hub is preparing an update handoff' })
      const body = await readRequestJson(request)
      const root = await canonicalProjectRoot(body.projectRoot)
      if (state.handoffPreparing) return json(response, 503, { ok: false, error: 'editor Hub is preparing an update handoff' })
      const details = await openProject(state, root)
      return json(response, 200, { ok: true, ...details })
    }
    if (request.method === 'POST' && url.pathname === '/v1/hub/launch') {
      const body = await readRequestJson(request)
      if (!body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).length !== 0) {
        return json(response, 400, { ok: false, error: 'launch accepts no parameters' })
      }
      const token = crypto.randomBytes(32).toString('base64url')
      state.launches.set(token, { expiresAt: Date.now() + LAUNCH_TTL_MS })
      return json(response, 200, { ok: true, url: `http://${state.host}/?launch=${token}` })
    }
    if (request.method === 'POST' && url.pathname === '/v1/hub/quit') {
      const body = await readRequestJson(request)
      if (!body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).length !== 0) {
        return json(response, 400, { ok: false, error: 'quit accepts no parameters' })
      }
      json(response, 200, { ok: true, status: 'stopping' })
      setImmediate(() => closeHub(state))
      return
    }
    if (request.method === 'POST' && url.pathname === '/v1/hub/update/check') {
      const body = await readRequestJson(request)
      if (!validUpdateMetadata(body)) return json(response, 400, { ok: false, error: 'invalid update metadata' })
      const updatePluginRoot = await canonicalDirectory(body.pluginRoot).catch(() => null)
      if (!updatePluginRoot || !await isFile(path.join(updatePluginRoot, 'runtime', 'hub-client.cjs'))) {
        return json(response, 400, { ok: false, error: 'invalid update Plugin root' })
      }
      const compatible = body.protocolVersion === state.protocolVersion
        && body.capabilities.every((capability) => state.capabilities.includes(capability))
      const affected = await Promise.all([...state.sidecars.values()].map((owned) => unsafeReasons(owned, true)))
      const reasons = [...new Set(affected.flat())]
      if (reasons.length) {
        state.updatePending = { ...body, pluginRoot: updatePluginRoot, compatible, reasons, requestedAt: new Date().toISOString() }
        if (compatible) return json(response, 200, { ok: true, status: 'compatible', reasons })
        return json(response, 200, { ok: true, status: 'pending', reasons })
      }
      state.updatePending = null
      return json(response, 200, { ok: true, status: 'ready' })
    }
    if (request.method === 'POST' && url.pathname === '/v1/hub/handoff/prepare') {
      const body = await readRequestJson(request)
      if (!body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).length !== 0) {
        return json(response, 400, { ok: false, error: 'handoff preparation accepts no parameters' })
      }
      const prepared = await prepareHandoff(state)
      return json(response, prepared.ok ? 200 : 409, prepared)
    }
    if (request.method === 'POST' && url.pathname === '/v1/hub/handoff/resume') {
      const body = await readRequestJson(request)
      if (!body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).length !== 0) {
        return json(response, 400, { ok: false, error: 'handoff resume accepts no parameters' })
      }
      await resumeHandoff(state)
      return json(response, 200, { ok: true, status: 'resumed' })
    }
    if (request.method === 'POST' && url.pathname === '/v1/hub/handoff/promote') {
      const body = await readRequestJson(request)
      if (!state.candidate || !body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).length !== 0) {
        return json(response, 400, { ok: false, error: 'handoff promotion is unavailable' })
      }
      const locator = await readJson(state.locatorPath)
      if (!locator || locator.instanceId !== state.instanceId) {
        return json(response, 409, { ok: false, error: 'candidate locator is unavailable' })
      }
      await writeJsonAtomic(state.canonicalLocatorPath, locator)
      await fsp.unlink(state.locatorPath).catch(() => {})
      await fsp.unlink(state.lockPath).catch(() => {})
      state.locatorPath = state.canonicalLocatorPath
      state.lockPath = state.canonicalLockPath
      state.candidate = false
      return json(response, 200, { ok: true, status: 'promoted' })
    }
    return json(response, 404, { ok: false, error: 'not found' })
  }

  if (request.method === 'GET' && url.pathname === '/' && url.searchParams.has('launch')) {
    return redeemLaunch(state, request, response, url)
  }
  if (!browserAuthorized(state, request)) return browserLaunchError(response)
  if (request.method === 'GET' && url.pathname === '/v1/hub/projects') {
    const candidates = await discoverProjects(state)
    return json(response, 200, {
      ok: true,
      projects: await publicProjects(state),
      candidates: publicCandidates(candidates),
      suggestedParent: suggestedProjectParent(state, candidates),
      updatePending: publicUpdatePending(state),
    })
  }
  if (request.method === 'POST' && url.pathname === '/v1/hub/projects') {
    if (request.headers.origin !== `http://${state.host}`) return json(response, 403, { ok: false, error: 'invalid origin' })
    const body = await readRequestJson(request)
    try {
      const root = await createProjectScaffold(body?.parent, body?.name, body?.source)
      await registerProject(state, root, pendingProjectId(root))
      return json(response, 201, { ok: true, project: await publicProject(state, state.registry.projects.find((item) => item.root === root)) })
    } catch (error) {
      return json(response, 400, { ok: false, error: error instanceof Error ? error.message : 'could not create project' })
    }
  }
  const candidateRegister = /^\/v1\/hub\/candidates\/([a-f0-9]{24})\/register$/.exec(url.pathname)
  if (request.method === 'POST' && candidateRegister) {
    if (request.headers.origin !== `http://${state.host}`) return json(response, 403, { ok: false, error: 'invalid origin' })
    const body = await readRequestJson(request)
    if (!body || typeof body !== 'object' || Array.isArray(body) || Object.keys(body).length !== 0) {
      return json(response, 400, { ok: false, error: 'register accepts no parameters' })
    }
    const candidate = (await discoverProjects(state)).find((item) => item.candidateId === candidateRegister[1])
    if (!candidate) return json(response, 404, { ok: false, error: 'project candidate not found' })
    await registerProject(state, candidate.root, pendingProjectId(candidate.root))
    return json(response, 200, { ok: true })
  }
  if (request.method === 'GET' && url.pathname === '/v1/hub/meta') {
    return json(response, 200, {
      ok: true, instanceId: state.instanceId, protocolVersion: state.protocolVersion,
      runtimeVersion: state.runtimeVersion, capabilities: state.capabilities,
      updatePending: publicUpdatePending(state),
    })
  }
  const projectLaunch = /^\/v1\/hub\/projects\/([^/]+)\/open$/.exec(url.pathname)
  if (request.method === 'GET' && projectLaunch) {
    if (state.handoffPreparing) return browserProjectError(response, 'Editor update handoff in progress')
    const projectId = decodeURIComponent(projectLaunch[1])
    const registered = state.registry.projects.find((project) => project.projectId === projectId)
    if (!registered) return browserProjectError(response, 'Project not found')
    try {
      const root = await canonicalProjectRoot(registered.root)
      if (state.handoffPreparing) return browserProjectError(response, 'Editor update handoff in progress')
      const details = await openProject(state, root)
      response.writeHead(303, { Location: details.url, 'Cache-Control': 'no-store' })
      return response.end()
    } catch {
      return browserProjectError(response, 'This project is unavailable')
    }
  }
  const projectClose = /^\/v1\/hub\/projects\/([^/]+)\/close$/.exec(url.pathname)
  if (request.method === 'POST' && projectClose) {
    if (request.headers.origin !== `http://${state.host}`) return json(response, 403, { ok: false, error: 'invalid origin' })
    const body = await readRequestJson(request)
    const projectId = decodeURIComponent(projectClose[1])
    const registered = state.registry.projects.find((project) => project.projectId === projectId)
    if (!registered) return json(response, 404, { ok: false, error: 'project not found' })
    const result = await closeProject(state, registered.root, body?.force === true)
    return json(response, result.ok ? 200 : 409, result)
  }
  if (request.method === 'POST' && url.pathname === '/v1/hub/quit') {
    if (request.headers.origin !== `http://${state.host}`) return json(response, 403, { ok: false, error: 'invalid origin' })
    const body = await readRequestJson(request)
    const sidecars = [...state.sidecars.entries()]
    try {
      await Promise.all(sidecars.map(([, owned]) => quiesceSidecar(owned)))
    } catch (error) {
      await Promise.allSettled(sidecars.map(([, owned]) => owned.call('resume')))
      throw error
    }
    const affected = await Promise.all(sidecars.map(async ([root, owned]) => ({
      projectId: owned.projectId, displayName: path.basename(root), reasons: await unsafeReasons(owned),
    })))
    const unsafe = affected.filter((project) => project.reasons.length)
    if (unsafe.length && body?.force !== true) {
      await Promise.allSettled(sidecars.map(([, owned]) => owned.call('resume')))
      return json(response, 409, { ok: false, requiresConfirmation: true, affected, error: 'Projects have protected work' })
    }
    json(response, 200, { ok: true, status: 'stopping', affected })
    setImmediate(() => closeHub(state))
    return
  }
  if (request.method === 'GET' || request.method === 'HEAD') {
    return serveStatic(state.uiRoot, url.pathname, request.method, response)
  }
  return json(response, 404, { ok: false, error: 'not found' })
}

async function openProject(state, projectRoot) {
  if (state.handoffPreparing) throw new Error('editor Hub is preparing an update handoff')
  let owned = state.sidecars.get(projectRoot)
  if (!owned || owned.child.exitCode !== null || owned.child.killed) {
    if (owned) state.sidecars.delete(projectRoot)
    let starting = state.startingSidecars.get(projectRoot)
    if (!starting) {
      starting = startSidecar(state, projectRoot).then((started) => {
        state.sidecars.set(projectRoot, started)
        return started
      }).finally(() => state.startingSidecars.delete(projectRoot))
      state.startingSidecars.set(projectRoot, starting)
    }
    owned = await starting
  }
  const armed = await owned.call('arm_launch')
  if (!armed.ok || typeof armed.url !== 'string') throw new Error(armed.error || 'could not arm editor launch')
  await registerProject(state, projectRoot, owned.projectId)
  return { pid: owned.child.pid, projectRoot, url: armed.url, projectId: owned.projectId }
}

async function registerProject(state, root, projectId) {
  const existing = state.registry.projects.find((project) => project.root === root)
  const record = {
    projectId,
    root,
    displayName: path.basename(root),
    rootFingerprint: crypto.createHash('sha256').update(root).digest('hex').slice(0, 16),
    lastOpenedAt: new Date().toISOString(),
  }
  if (existing) Object.assign(existing, record)
  else state.registry.projects.push(record)
  await writeJsonAtomic(state.registryPath, state.registry)
}

async function unsafeReasons(owned, includeClients = false) {
  if (!owned || owned.child.exitCode !== null) return []
  const status = await owned.call('status').catch(() => ({ activeWork: true }))
  return [
    ...(includeClients && status.clients > 0 ? ['connected editor'] : []),
    ...(status.hasDraft ? ['recoverable draft'] : []),
    ...(status.activeWork ? ['active operation'] : []),
    ...(status.mutationLease ? ['mutation lease'] : []),
  ]
}

async function closeProject(state, root, force) {
  const owned = state.sidecars.get(root)
  if (!owned || owned.child.exitCode !== null) return { ok: true, status: 'closed', projectId: owned?.projectId }
  try {
    await quiesceSidecar(owned)
  } catch (error) {
    await owned.call('resume').catch(() => {})
    throw error
  }
  const reasons = await unsafeReasons(owned)
  if (reasons.length && !force) {
    await owned.call('resume').catch(() => {})
    return { ok: false, requiresConfirmation: true, reasons, error: 'Project has protected work' }
  }
  const exit = waitForExit(owned.child, 2_000)
  owned.child.stdin.end()
  await exit
  if (owned.child.exitCode === null) owned.child.kill()
  state.sidecars.delete(root)
  return { ok: true, status: 'closed', projectId: owned.projectId }
}

async function quiesceSidecar(owned) {
  const result = await owned.call('quiesce')
  if (!result?.ok) throw new Error(result?.error || 'editor runtime could not pause mutations')
}

async function reclaimIdleRuntimes(state) {
  if (state.closing) return
  for (const [root, owned] of state.sidecars) {
    const status = await owned.call('status').catch(() => null)
    if (!status || status.clients !== 0 || status.hasDraft || status.activeWork || status.mutationLease) continue
    if (!Number.isFinite(status.lastActivityAt) || Date.now() - status.lastActivityAt < IDLE_RUNTIME_TTL_MS) continue
    await closeProject(state, root, false)
  }
}

async function prepareHandoff(state) {
  if (state.handoffPreparing) return { ok: false, status: 'pending', reasons: ['handoff already in progress'] }
  state.handoffPreparing = true
  try {
    await Promise.allSettled([...state.startingSidecars.values()])
    const ownedSidecars = [...state.sidecars.values()]
    await Promise.all(ownedSidecars.map((owned) => quiesceSidecar(owned)))
    const affected = await Promise.all(ownedSidecars.map((owned) => unsafeReasons(owned, true)))
    const reasons = [...new Set(affected.flat())]
    if (reasons.length) {
      await resumeHandoff(state)
      return { ok: false, status: 'pending', reasons, error: 'Projects have protected work' }
    }
    for (const [root] of [...state.sidecars]) await closeProject(state, root, true)
    return { ok: true, status: 'prepared' }
  } catch (error) {
    await resumeHandoff(state)
    throw error
  }
}

async function resumeHandoff(state) {
  state.handoffPreparing = false
  await Promise.allSettled([...state.sidecars.values()].map((owned) => owned.call('resume')))
}

async function maybeAdvancePendingUpdate(state) {
  const update = state.updatePending
  if (!update || state.updateAttempting || state.closing || state.handoffPreparing) return
  const affected = await Promise.all([...state.sidecars.values()].map((owned) => unsafeReasons(owned, true)))
  const reasons = [...new Set(affected.flat())]
  state.updatePending.reasons = reasons
  if (reasons.length) return
  state.updateAttempting = true
  const child = spawn(process.execPath, [
    path.join(update.pluginRoot, 'runtime', 'hub-client.cjs'), 'update',
    '--protocol-version', String(update.protocolVersion),
    '--runtime-version', update.runtimeVersion,
    '--capabilities', update.capabilities.join(','),
  ], {
    cwd: path.join(update.pluginRoot, 'runtime'),
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
    env: { ...process.env, PLUGIN_DATA: state.dataRoot },
  })
  child.unref()
  child.once('exit', () => { state.updateAttempting = false })
  child.once('error', () => { state.updateAttempting = false })
}

async function publicProjects(state) {
  return Promise.all(state.registry.projects
    .slice()
    .sort((left, right) => right.lastOpenedAt.localeCompare(left.lastOpenedAt))
    .map((project) => publicProject(state, project)))
}

async function publicProject(state, project) {
  let available = false
  try { available = await canonicalProjectRoot(project.root) === project.root } catch {}
  return {
    projectId: project.projectId,
    displayName: project.displayName,
    rootFingerprint: project.rootFingerprint,
    lastOpenedAt: project.lastOpenedAt,
    available,
    running: state.sidecars.has(project.root),
  }
}

async function discoverProjects(state) {
  const registeredRoots = new Set(state.registry.projects.map((project) => project.root))
  const parents = [...new Set(state.registry.projects.map((project) => path.dirname(project.root)))]
  const candidates = []
  for (const parent of parents) {
    const entries = await fsp.readdir(parent, { withFileTypes: true }).catch(() => [])
    for (const entry of entries.slice(0, 250)) {
      if (!entry.isDirectory()) continue
      const value = path.join(parent, entry.name)
      let root
      try { root = await canonicalProjectRoot(value) } catch { continue }
      if (registeredRoots.has(root) || candidates.some((candidate) => candidate.root === root)) continue
      candidates.push({
        candidateId: projectFingerprint(root, 24),
        displayName: path.basename(root),
        rootFingerprint: projectFingerprint(root),
        root,
      })
    }
  }
  return candidates.sort((left, right) => left.displayName.localeCompare(right.displayName))
}

function publicCandidates(candidates) {
  return candidates.map(({ root, ...candidate }) => candidate)
}

function suggestedProjectParent(state, candidates) {
  const root = state.registry.projects[0]?.root || candidates[0]?.root
  return root ? path.dirname(root) : ''
}

async function createProjectScaffold(parentValue, nameValue, sourceValue, options = {}) {
  const parent = await canonicalDirectory(parentValue)
  const source = await canonicalFile(sourceValue)
  const name = typeof nameValue === 'string' ? nameValue.trim() : ''
  if (!name || name === '.' || name === '..' || /[<>:"/\\|?*\u0000-\u001f]/.test(name)
      || /[. ]$/.test(name) || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)) {
    throw new Error('project name contains invalid characters')
  }
  const root = path.join(parent, name)
  if (path.dirname(root) !== parent) throw new Error('project location is invalid')
  try {
    await fsp.mkdir(root, { recursive: false, mode: 0o700 })
  } catch (error) {
    if (error?.code === 'EEXIST') throw new Error('project already exists')
    throw error
  }
  try {
    await Promise.all(['input', 'review', 'final', 'work'].map((directory) => fsp.mkdir(path.join(root, directory), { mode: 0o700 })))
    const probe = await (options.probeMedia || probeMedia)(source)
    const sourceName = path.basename(source)
    const projectSource = path.join(root, 'input', sourceName)
    await fsp.copyFile(source, projectSource)
    const normalizedMtime = Math.floor(Date.now() / 1000)
    await fsp.utimes(projectSource, normalizedMtime, normalizedMtime)
    const sourceStat = await fsp.stat(projectSource, { bigint: true })
    await writeJsonAtomic(path.join(root, 'work', 'timeline.json'), {
      schema_version: 1,
      source_duration_s: probe.duration,
      program_duration_s: probe.duration,
      fps: probe.fps,
      clips: [{
        id: 'clip-1',
        source_range: { start_s: 0, end_s: probe.duration },
        program_range: { start_s: 0, end_s: probe.duration },
        speed: 1,
      }],
    })
    await writeJsonAtomic(path.join(root, 'work', 'project.json'), {
      schema_version: 1,
      project_id: `project-${crypto.randomBytes(8).toString('hex')}`,
      revision: 1,
      source: {
        path: `../input/${sourceName}`,
        fingerprint: { size: Number(sourceStat.size), modified_ns: Number(sourceStat.mtimeNs), duration_s: probe.duration },
      },
      active_sequence: 'main',
      sequences: { main: { timeline: 'timeline.json', operations: [] } },
      operations: [],
      reviews: [],
      render: { status: 'draft' },
    })
    return await canonicalProjectRoot(root)
  } catch (error) {
    await fsp.rm(root, { recursive: true, force: true }).catch(() => {})
    throw error
  }
}

async function canonicalFile(value) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('source media path is required')
  const real = await fsp.realpath(path.resolve(value))
  if (!(await fsp.stat(real)).isFile()) throw new Error('source media path must be a file')
  return real
}

function probeMedia(source) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.CAC_FFPROBE || 'ffprobe', [
      '-v', 'error', '-select_streams', 'v:0',
      '-show_entries', 'stream=r_frame_rate:format=duration', '-of', 'json', source,
    ], { windowsHide: true })
    let stdout = ''
    let stderr = ''
    child.stdout.setEncoding('utf8')
    child.stderr.setEncoding('utf8')
    child.stdout.on('data', (chunk) => { stdout += chunk })
    child.stderr.on('data', (chunk) => { stderr += chunk })
    child.once('error', () => reject(new Error('ffprobe is required to create a project')))
    child.once('close', (code) => {
      if (code !== 0) return reject(new Error(stderr.trim() || 'source media could not be read'))
      try {
        const value = JSON.parse(stdout)
        const duration = Number(value.format?.duration)
        const parts = String(value.streams?.[0]?.r_frame_rate || '').split('/').map(Number)
        if (!Number.isFinite(duration) || duration <= 0 || parts.length !== 2 || !parts[0] || !parts[1]) {
          throw new Error('source media must contain a readable video stream')
        }
        resolve({ duration, fps: { num: parts[0], den: parts[1] } })
      } catch (error) {
        reject(error instanceof Error ? error : new Error('source media could not be read'))
      }
    })
  })
}

function projectFingerprint(root, length = 16) {
  return crypto.createHash('sha256').update(root).digest('hex').slice(0, length)
}

function pendingProjectId(root) {
  return `project_pending_${projectFingerprint(root, 24)}`
}

function redeemLaunch(state, request, response, url) {
  const token = url.searchParams.get('launch')
  const launch = typeof token === 'string' ? state.launches.get(token) : null
  const now = Date.now()
  for (const [candidate, value] of state.launches) if (value.expiresAt <= now) state.launches.delete(candidate)
  const directNavigation = request.headers['sec-fetch-mode'] === 'navigate'
    && request.headers['sec-fetch-dest'] === 'document'
    && request.headers['sec-fetch-site'] === 'none'
  if (!directNavigation || url.searchParams.size !== 1 || !launch || launch.expiresAt <= now) {
    return browserLaunchError(response)
  }
  state.launches.delete(token)
  const session = crypto.randomBytes(32).toString('base64url')
  state.sessions.add(session)
  response.setHeader('Set-Cookie', `cut_hub_session=${session}; HttpOnly; SameSite=Strict; Path=/`)
  response.writeHead(303, { Location: '/', 'Cache-Control': 'no-store' })
  response.end()
}

function browserAuthorized(state, request) {
  return state.sessions.has(cookiesFor(request).cut_hub_session)
}

function cookiesFor(request) {
  return Object.fromEntries((request.headers.cookie || '').split(';').map((part) => {
    const separator = part.indexOf('=')
    return separator < 0 ? [part.trim(), ''] : [part.slice(0, separator).trim(), part.slice(separator + 1)]
  }))
}

async function startSidecar(state, projectRoot) {
  const child = spawn(process.execPath, [
    path.join(state.pluginRoot, 'runtime', 'sidecar.cjs'),
    '--project-root', projectRoot,
    '--ui-root', state.uiRoot,
    '--data-root', state.dataRoot,
  ], {
    cwd: path.join(state.pluginRoot, 'runtime'),
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
    env: process.env,
  })
  let stderr = ''
  child.stderr.on('data', (chunk) => { stderr = `${stderr}${chunk}`.slice(-8_192) })
  const lines = readline.createInterface({ input: child.stdout, crlfDelay: Infinity })
  const ready = await waitForLine(lines, child, () => `editor sidecar startup failed: ${stderr}`)
  let startup
  try { startup = JSON.parse(ready) } catch { throw new Error('editor sidecar returned invalid startup metadata') }
  if (startup.host !== LOOPBACK || !Number.isInteger(startup.port) || !startup.projectId) {
    child.kill()
    throw new Error('editor sidecar returned invalid startup metadata')
  }
  let requestId = 0
  const pending = new Map()
  lines.on('line', (line) => {
    let result
    try { result = JSON.parse(line) } catch { return }
    const request = pending.get(result.id)
    if (!request) return
    pending.delete(result.id)
    clearTimeout(request.timer)
    request.resolve(result)
  })
  child.once('exit', () => {
    state.sidecars.delete(projectRoot)
    for (const request of pending.values()) {
      clearTimeout(request.timer)
      request.reject(new Error(`editor sidecar stopped: ${stderr}`))
    }
    pending.clear()
  })
  return {
    child,
    projectId: startup.projectId,
    call(command) {
      return new Promise((resolve, reject) => {
        const id = ++requestId
        const timer = setTimeout(() => {
          pending.delete(id)
          reject(new Error('editor sidecar control timed out'))
        }, 5_000)
        pending.set(id, { resolve, reject, timer })
        child.stdin.write(`${JSON.stringify({ id, command })}\n`)
      })
    },
  }
}

async function closeHub(state) {
  if (state.closing) return
  state.closing = true
  clearInterval(state.idleTimer)
  clearInterval(state.updateTimer)
  await Promise.allSettled(state.startingSidecars.values())
  await Promise.allSettled([...state.sidecars.values()].map((owned) => owned.call('quiesce')))
  const exits = []
  for (const owned of state.sidecars.values()) {
    exits.push(waitForExit(owned.child, 2_000))
    owned.child.stdin.end()
  }
  await Promise.all(exits)
  for (const owned of state.sidecars.values()) if (owned.child.exitCode === null) owned.child.kill()
  await new Promise((resolve) => state.server.close(resolve))
  const locator = await readJson(state.locatorPath)
  const lock = await readJson(state.lockPath)
  if (locator?.instanceId === state.instanceId) {
    await fsp.unlink(state.locatorPath).catch(() => {})
    if (lock?.token === state.lockToken) await fsp.unlink(state.lockPath).catch(() => {})
  }
}

function waitForLine(lines, child, errorMessage) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => finish(reject, new Error('editor sidecar startup timed out')), 10_000)
    const onLine = (line) => finish(resolve, line)
    const onExit = () => finish(reject, new Error(errorMessage()))
    const onError = (error) => finish(reject, error)
    const finish = (callback, value) => {
      clearTimeout(timer)
      lines.off('line', onLine)
      child.off('exit', onExit)
      child.off('error', onError)
      callback(value)
    }
    lines.once('line', onLine)
    child.once('exit', onExit)
    child.once('error', onError)
  })
}

function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null) return Promise.resolve()
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, timeoutMs)
    child.once('exit', () => { clearTimeout(timer); resolve() })
  })
}

async function canonicalProjectRoot(value) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('project_root is required')
  const root = await fsp.realpath(path.resolve(value))
  if (!(await isFile(path.join(root, 'work', 'project.json')))) throw new Error('project_root must contain work/project.json')
  return root
}

async function canonicalDirectory(value) {
  if (!value) throw new Error('directory is required')
  const real = await fsp.realpath(path.resolve(value))
  if (!(await fsp.stat(real)).isDirectory()) throw new Error('directory is required')
  return real
}

function readRequestJson(request) {
  return new Promise((resolve, reject) => {
    let body = ''
    request.setEncoding('utf8')
    request.on('data', (chunk) => {
      body += chunk
      if (body.length > 16_384) request.destroy(new Error('request is too large'))
    })
    request.once('end', () => {
      try { resolve(JSON.parse(body)) } catch { reject(new Error('invalid JSON')) }
    })
    request.once('error', reject)
  })
}

async function writeJsonAtomic(file, value) {
  const temporary = `${file}.${crypto.randomBytes(8).toString('hex')}.tmp`
  await fsp.writeFile(temporary, JSON.stringify(value) + '\n', { encoding: 'utf8', mode: 0o600, flag: 'wx' })
  try {
    await fsp.rename(temporary, file)
  } finally {
    await fsp.unlink(temporary).catch(() => {})
  }
}

async function readJson(file) {
  try { return JSON.parse(await fsp.readFile(file, 'utf8')) } catch { return null }
}

async function loadRegistry(file) {
  const value = await readJson(file)
  if (value?.schemaVersion === 1 && Array.isArray(value.projects)) return value
  return { schemaVersion: 1, projects: [] }
}

async function isFile(file) {
  try { return (await fsp.stat(file)).isFile() } catch { return false }
}

function json(response, status, value) {
  if (response.headersSent) return response.end()
  const body = JSON.stringify(value)
  response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(body), 'Cache-Control': 'no-store' })
  response.end(body)
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
  const contentTypes = {
    '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8', '.woff': 'font/woff', '.woff2': 'font/woff2',
    '.png': 'image/png', '.svg': 'image/svg+xml',
  }
  response.writeHead(200, {
    'Content-Type': contentTypes[extension] || 'application/octet-stream',
    'Content-Length': stat.size,
    'Cache-Control': extension === '.html' ? 'no-store' : 'public, max-age=31536000, immutable',
  })
  if (method === 'HEAD') return response.end()
  const content = await fsp.readFile(target)
  response.end(content)
}

function isContained(root, target) {
  const relative = path.relative(root, target)
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

function browserLaunchError(response) {
  const body = '<!doctype html><title>Editor Hub unavailable</title><h1>Editor Hub unavailable</h1><p>This launch link is invalid, expired, or already used. Open the editor from the Cut as Code Plugin again.</p>'
  response.writeHead(401, { 'Content-Type': 'text/html; charset=utf-8', 'Content-Length': Buffer.byteLength(body), 'Cache-Control': 'no-store' })
  response.end(body)
}

function browserProjectError(response, message) {
  const body = `<!doctype html><title>Project unavailable</title><h1>Project unavailable</h1><p>${message}</p>`
  response.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8', 'Content-Length': Buffer.byteLength(body), 'Cache-Control': 'no-store' })
  response.end(body)
}

function validUpdateMetadata(value) {
  return value && typeof value === 'object' && !Array.isArray(value)
    && Number.isInteger(value.protocolVersion) && value.protocolVersion > 0
    && typeof value.runtimeVersion === 'string' && value.runtimeVersion.length > 0
    && Array.isArray(value.capabilities) && value.capabilities.every((item) => typeof item === 'string')
    && typeof value.pluginRoot === 'string' && value.pluginRoot.length > 0
}

function publicUpdatePending(state) {
  if (!state.updatePending) return null
  return {
    runtimeVersion: state.updatePending.runtimeVersion,
    protocolVersion: state.updatePending.protocolVersion,
    compatible: state.updatePending.compatible === true,
    reasons: state.updatePending.reasons,
    requestedAt: state.updatePending.requestedAt,
  }
}

function parseArguments(args) {
  const options = {}
  for (let index = 0; index < args.length; index += 2) {
    if (args[index] === '--plugin-root') options.pluginRoot = args[index + 1]
    else if (args[index] === '--data-root') options.dataRoot = args[index + 1]
    else if (args[index] === '--lock-token') options.lockToken = args[index + 1]
    else if (args[index] === '--protocol-version') options.protocolVersion = Number(args[index + 1])
    else if (args[index] === '--runtime-version') options.runtimeVersion = args[index + 1]
    else if (args[index] === '--capabilities') options.capabilities = args[index + 1].split(',').filter(Boolean)
    else if (args[index] === '--locator-name') options.locatorName = args[index + 1]
    else throw new Error(`unknown argument: ${args[index]}`)
  }
  if (!options.pluginRoot || !options.dataRoot || !options.lockToken || !Number.isInteger(options.protocolVersion)
    || !options.runtimeVersion || !Array.isArray(options.capabilities)) throw new Error('missing editor Hub startup argument')
  if (options.locatorName && !/^hub\.next\.[a-f0-9]+\.json$/.test(options.locatorName)) {
    throw new Error('invalid candidate locator name')
  }
  return options
}

module.exports = { canonicalProjectRoot, createProjectScaffold, discoverProjects, parseArguments, publicCandidates }

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`)
    process.exitCode = 1
  })
}
