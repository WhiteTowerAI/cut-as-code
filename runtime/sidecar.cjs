'use strict'

const crypto = require('node:crypto')
const fs = require('node:fs')
const fsp = require('node:fs/promises')
const http = require('node:http')
const path = require('node:path')
const { spawn } = require('node:child_process')
const readline = require('node:readline')

const LOOPBACK = '127.0.0.1'
const LAUNCH_TTL_MS = 10_000
const HTTP_ROUTE_ALLOWLIST = Object.freeze([
  Object.freeze({ id: 'launch', methods: Object.freeze(['GET']), pattern: /^\/$/ }),
  Object.freeze({ id: 'meta', methods: Object.freeze(['GET']), pattern: /^\/v1\/meta$/ }),
  Object.freeze({ id: 'snapshot', methods: Object.freeze(['GET']), pattern: /^\/v1\/projects\/([^/]+)\/snapshot$/ }),
  Object.freeze({ id: 'transaction', methods: Object.freeze(['POST']), pattern: /^\/v1\/projects\/([^/]+)\/transactions$/ }),
  Object.freeze({ id: 'review', methods: Object.freeze(['POST']), pattern: /^\/v1\/projects\/([^/]+)\/reviews\/decision$/ }),
  Object.freeze({ id: 'resource', methods: Object.freeze(['GET']), pattern: /^\/v1\/projects\/([^/]+)\/resources\/(res_[a-f0-9]+)$/ }),
  Object.freeze({ id: 'file', methods: Object.freeze(['GET']), pattern: /^\/v1\/projects\/([^/]+)\/(media|artifacts)\/((?:asset|artifact)_[a-f0-9]+)$/ }),
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
    launches: [],
    sessions: new Set(),
    clients: new Set(),
    media: new Map(),
    artifacts: new Map(),
  }
  await refreshFiles(state)

  const server = http.createServer((request, response) => {
    handleRequest(state, request, response).catch(() => json(response, 500, { ok: false, error: 'internal error' }))
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

  const control = readline.createInterface({ input: process.stdin, crlfDelay: Infinity })
  control.on('line', (line) => handleControl(state, line))

  let closing = false
  const close = async () => {
    if (closing) return
    closing = true
    state.watcher?.close()
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
    if (authorized(state, request)) return serveStatic(state.uiRoot, url.pathname, request.method, response)
    const directNavigation = request.headers['sec-fetch-mode'] === 'navigate'
      && request.headers['sec-fetch-dest'] === 'document'
      && request.headers['sec-fetch-site'] === 'none'
    const correctProject = url.searchParams.size === 1 && url.searchParams.get('project') === state.projectId
    state.launches = state.launches.filter((expiresAt) => expiresAt >= Date.now())
    if (!directNavigation || !correctProject || state.launches.length === 0) {
      return json(response, 401, { ok: false, error: 'editor launch is not armed' })
    }
    state.launches.shift()
    const session = crypto.randomBytes(32).toString('base64url')
    state.sessions.add(session)
    response.setHeader('Set-Cookie', `cut_session=${session}; HttpOnly; SameSite=Strict; Path=/`)
    response.writeHead(303, { Location: request.url, 'Cache-Control': 'no-store' })
    return response.end()
  }

  if (route.id !== 'static') {
    if (!authorized(state, request)) return json(response, 401, { ok: false, error: 'unauthorized' })
    if (route.id === 'meta') {
      return json(response, 200, { ok: true, projectId: state.projectId, readOnly: true })
    }
    const match = route.match
    if (route.id === 'snapshot' && match[1] === state.projectId) {
      await refreshFiles(state)
      const result = await state.protocol.call({ verb: 'get_snapshot', project_id: state.projectId })
      if (result.ok) {
        result.snapshot.media = publicFiles(state.media, state.projectId, 'media')
        result.snapshot.artifacts = publicFiles(state.artifacts, state.projectId, 'artifacts')
      }
      return json(response, result.ok ? 200 : 400, result)
    }
    if (route.id === 'transaction' && match[1] === state.projectId) {
      if (request.headers.origin !== state.origin) return json(response, 403, { ok: false, error: 'invalid origin' })
      const body = await readJson(request)
      const result = await state.protocol.call({
        verb: 'plan.update', project_id: state.projectId, operation: body.operation,
        read_set: body.readSet, review: body.review,
      })
      return json(response, result.status || (result.ok ? 200 : 400), result)
    }
    if (route.id === 'review' && match[1] === state.projectId) {
      if (request.headers.origin !== state.origin) return json(response, 403, { ok: false, error: 'invalid origin' })
      const body = await readJson(request)
      const result = await state.protocol.call({
        verb: 'review.record', project_id: state.projectId, operation: body.operation,
        read_set: body.readSet, decision: body.decision,
      })
      return json(response, result.status || (result.ok ? 200 : 400), result)
    }
    if (route.id === 'resource' && match[1] === state.projectId) {
      const result = await state.protocol.call({
        verb: 'get_resource', project_id: state.projectId, resource_id: match[2],
      })
      return json(response, result.ok ? 200 : 404, result)
    }
    if (route.id === 'file' && match[1] === state.projectId) {
      const registry = match[2] === 'media' ? state.media : state.artifacts
      const item = registry.get(match[3])
      if (!item) return json(response, 404, { ok: false, error: 'unknown resource' })
      return streamFile(request, response, item)
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
  state.launches.push(Date.now() + LAUNCH_TTL_MS)
  const url = `${state.origin}/?project=${encodeURIComponent(state.projectId)}`
  process.stdout.write(`${JSON.stringify({ id: request.id, ok: true, url })}\n`)
}

function watchProject(state) {
  let timer
  const changed = () => {
    clearTimeout(timer)
    timer = setTimeout(async () => {
      await refreshFiles(state).catch(() => {})
      for (const client of state.clients) client.write(`event: project-change\ndata: ${JSON.stringify({ projectId: state.projectId })}\n\n`)
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

async function refreshFiles(state) {
  state.media = await collectFiles(state.root, ['input'], 'asset')
  state.artifacts = await collectFiles(state.root, ['review'], 'artifact')
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

async function streamFile(request, response, item) {
  const range = parseRange(request.headers.range, item.size)
  if (range === false) {
    response.writeHead(416, { 'Content-Range': `bytes */${item.size}` })
    return response.end()
  }
  const start = range?.start ?? 0
  const end = range?.end ?? item.size - 1
  response.writeHead(range ? 206 : 200, {
    'Accept-Ranges': 'bytes',
    'Content-Length': Math.max(0, end - start + 1),
    ...(range ? { 'Content-Range': `bytes ${start}-${end}/${item.size}` } : {}),
    'Content-Type': item.mediaType,
    'X-Content-Type-Options': 'nosniff',
    ...(item.mediaType.startsWith('text/html') ? {
      'Content-Security-Policy': "sandbox; default-src 'none'; img-src 'self' data:; media-src 'self'; style-src 'unsafe-inline'",
    } : {}),
  })
  if (request.method === 'HEAD' || item.size === 0) return response.end()
  fs.createReadStream(item.path, { start, end }).pipe(response)
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

function json(response, status, value) {
  if (response.headersSent) return response.end()
  const body = JSON.stringify(value)
  response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(body) })
  response.end(body)
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
  child.stderr.resume()
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
        }, 10_000)
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

module.exports = { HTTP_ROUTE_ALLOWLIST, routeForRequest }

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`)
    process.exitCode = 1
  })
}
