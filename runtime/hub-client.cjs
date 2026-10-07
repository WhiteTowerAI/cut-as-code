'use strict'

const crypto = require('node:crypto')
const fsp = require('node:fs/promises')
const http = require('node:http')
const os = require('node:os')
const path = require('node:path')
const { spawn } = require('node:child_process')
const { challengeProof, locatorProof, safeEqual } = require('./hub-trust.cjs')

const LOOPBACK = '127.0.0.1'
const STARTUP_TIMEOUT_MS = 10_000
const POLL_INTERVAL_MS = 50
const HUB_PROTOCOL_VERSION = 1
const HUB_CAPABILITIES = Object.freeze(['multi-project', 'recoverable-drafts', 'explicit-lifecycle', 'typed-protocol-v1'])

function resolvePluginData(environment = process.env, platform = process.platform, home = os.homedir()) {
  const configured = environment.PLUGIN_DATA || environment.CLAUDE_PLUGIN_DATA || environment.CAC_EDITOR_DATA
  if (configured) return path.resolve(configured)
  if (platform === 'win32') {
    const base = environment.LOCALAPPDATA || environment.APPDATA || path.join(home, 'AppData', 'Local')
    return path.join(base, 'cut-as-code-editor')
  }
  if (platform === 'darwin') return path.join(home, 'Library', 'Application Support', 'cut-as-code-editor')
  return path.join(environment.XDG_STATE_HOME || path.join(home, '.local', 'state'), 'cut-as-code-editor')
}

function hubPaths(dataRoot) {
  return {
    locator: path.join(dataRoot, 'hub.json'),
    lock: path.join(dataRoot, 'hub.lock'),
  }
}

async function ensureHub(options = {}) {
  const pluginRoot = path.resolve(options.pluginRoot || path.join(__dirname, '..'))
  const dataRoot = path.resolve(options.dataRoot || resolvePluginData())
  const metadata = await runtimeMetadata(pluginRoot, options)
  await fsp.mkdir(dataRoot, { recursive: true, mode: 0o700 })
  const paths = hubPaths(dataRoot)
  const connected = await readTrustedLocator(paths.locator)
  if (connected) {
    const compatible = connected.protocolVersion === metadata.protocolVersion
      && metadata.capabilities.every((capability) => connected.capabilities.includes(capability))
    const unchanged = compatible
      && connected.runtimeVersion === metadata.runtimeVersion
      && sameStrings(connected.capabilities, metadata.capabilities)
    if (unchanged) return connected
    const update = await hubRequest(connected, 'POST', '/v1/hub/update/check', { ...metadata, pluginRoot })
    if (compatible && update.status === 'compatible') return { ...connected, updateAvailable: true }
    if (update.status === 'pending') return { ...connected, updatePending: true }
    return handoffHub({ ...options, pluginRoot, dataRoot, metadata, paths, connected })
  }

  const lockToken = crypto.randomBytes(32).toString('base64url')
  let ownsStartup = false
  try {
    const handle = await fsp.open(paths.lock, 'wx', 0o600)
    try {
      await handle.writeFile(JSON.stringify({ token: lockToken, createdAt: new Date().toISOString() }) + '\n')
    } finally {
      await handle.close()
    }
    ownsStartup = true
  } catch (error) {
    if (error?.code !== 'EEXIST') throw error
  }

  if (ownsStartup) {
    startHubProcess({ pluginRoot, dataRoot, metadata, lockToken, spawnProcess: options.spawnProcess })
  }

  const deadline = Date.now() + (options.startupTimeoutMs || STARTUP_TIMEOUT_MS)
  while (Date.now() < deadline) {
    const locator = await readTrustedLocator(paths.locator)
    if (locator) return locator
    await delay(POLL_INTERVAL_MS)
  }

  const lock = await readJson(paths.lock)
  const stat = await fsp.stat(paths.lock).catch(() => null)
  const stale = stat && Date.now() - stat.mtimeMs >= STARTUP_TIMEOUT_MS
  if (stale || lock?.token === lockToken) {
    await fsp.unlink(paths.locator).catch(() => {})
    await fsp.unlink(paths.lock).catch(() => {})
  }
  if (!options.retried) return ensureHub({ ...options, pluginRoot, dataRoot, retried: true })
  throw new Error('editor Hub startup timed out')
}

async function handoffHub({ pluginRoot, dataRoot, metadata, paths, connected, spawnProcess, startupTimeoutMs }) {
  const oldLock = await readJson(paths.lock)
  if (!/^[A-Za-z0-9_-]{43}$/.test(oldLock?.token || '')) throw new Error('editor Hub startup lock is unavailable')
  const lockToken = oldLock.token
  const locatorName = `hub.next.${crypto.randomBytes(12).toString('hex')}.json`
  const candidatePath = path.join(dataRoot, locatorName)
  const candidateLockPath = trustLockPath(candidatePath)
  await writeJsonAtomic(candidateLockPath, { token: lockToken, createdAt: new Date().toISOString() })
  try {
    startHubProcess({ pluginRoot, dataRoot, metadata, lockToken, locatorName, spawnProcess })
    const deadline = Date.now() + (startupTimeoutMs || STARTUP_TIMEOUT_MS)
    let candidate
    while (Date.now() < deadline) {
      candidate = await readTrustedLocator(candidatePath)
      if (candidate) break
      await delay(POLL_INTERVAL_MS)
    }
    if (!candidate) throw new Error('replacement editor Hub startup timed out')
    await hubRequest(connected, 'POST', '/v1/hub/handoff/prepare', {})
    await hubRequest(candidate, 'POST', '/v1/hub/handoff/promote', {})
    const promoted = await readTrustedLocator(paths.locator)
    if (!promoted || promoted.instanceId !== candidate.instanceId) throw new Error('replacement editor Hub promotion failed')
    await hubRequest(connected, 'POST', '/v1/hub/quit', {}).catch(() => {})
    return promoted
  } catch (error) {
    await hubRequest(connected, 'POST', '/v1/hub/handoff/resume', {}).catch(() => {})
    const candidate = await readTrustedLocator(candidatePath)
    if (candidate) await hubRequest(candidate, 'POST', '/v1/hub/quit', {}).catch(() => {})
    await fsp.unlink(candidatePath).catch(() => {})
    await fsp.unlink(candidateLockPath).catch(() => {})
    throw error
  }
}

function startHubProcess({ pluginRoot, dataRoot, metadata, lockToken, locatorName, spawnProcess = spawn }) {
  const child = spawnProcess(process.execPath, [
    path.join(pluginRoot, 'runtime', 'hub.cjs'),
    '--plugin-root', pluginRoot,
    '--data-root', dataRoot,
    '--lock-token', lockToken,
    '--protocol-version', String(metadata.protocolVersion),
    '--runtime-version', metadata.runtimeVersion,
    '--capabilities', metadata.capabilities.join(','),
    ...(locatorName ? ['--locator-name', locatorName] : []),
  ], {
    cwd: path.join(pluginRoot, 'runtime'),
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
    env: process.env,
  })
  child.unref()
  return child
}

async function readTrustedLocator(locatorPath) {
  const locator = await readJson(locatorPath)
  const lock = await readJson(trustLockPath(locatorPath))
  if (!validLocator(locator) || !/^[A-Za-z0-9_-]{43}$/.test(lock?.token || '')) return null
  const expectedStartupProof = locatorProof(lock.token, locator)
  if (!safeEqual(locator.startupProof, expectedStartupProof)) return null
  try {
    const challenge = crypto.randomBytes(32).toString('base64url')
    const response = await hubRequest(locator, 'POST', '/v1/challenge', { challenge })
    const expected = challengeProof(locator.controlToken, challenge, locator.instanceId, locator.pid)
    if (!response.ok || response.instanceId !== locator.instanceId || response.pid !== locator.pid
      || !safeEqual(response.proof, expected)) return null
    return locator
  } catch {
    return null
  }
}

function trustLockPath(locatorPath) {
  return locatorPath.replace(/\.json$/, '.lock')
}

function sameStrings(left, right) {
  return left.length === right.length && left.every((value, index) => value === right[index])
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

function validLocator(value) {
  return value?.schemaVersion === 2
    && value.host === LOOPBACK
    && Number.isInteger(value.port)
    && value.port > 0
    && Number.isInteger(value.pid)
    && typeof value.instanceId === 'string'
    && Number.isInteger(value.protocolVersion)
    && typeof value.runtimeVersion === 'string'
    && Array.isArray(value.capabilities)
    && /^[A-Za-z0-9_-]{43}$/.test(value.controlToken || '')
    && /^[A-Za-z0-9_-]{43}$/.test(value.startupProof || '')
}

async function runtimeMetadata(pluginRoot, options = {}) {
  let runtimeVersion = options.runtimeVersion
  if (!runtimeVersion) {
    const manifest = await readJson(path.join(pluginRoot, '.codex-plugin', 'plugin.json'))
    runtimeVersion = typeof manifest?.version === 'string' ? manifest.version : '0.0.0'
  }
  return {
    protocolVersion: Number.isInteger(options.protocolVersion) ? options.protocolVersion : HUB_PROTOCOL_VERSION,
    runtimeVersion,
    capabilities: Array.isArray(options.capabilities) ? options.capabilities : [...HUB_CAPABILITIES],
  }
}

function hubRequest(locator, method, pathname, body) {
  const payload = body === undefined ? null : Buffer.from(JSON.stringify(body))
  return new Promise((resolve, reject) => {
    const request = http.request({
      host: locator.host,
      port: locator.port,
      method,
      path: pathname,
      headers: {
        Authorization: `Bearer ${locator.controlToken}`,
        ...(payload ? { 'Content-Type': 'application/json', 'Content-Length': payload.length } : {}),
      },
      timeout: 5_000,
    }, (response) => {
      let value = ''
      response.setEncoding('utf8')
      response.on('data', (chunk) => { value += chunk })
      response.on('end', () => {
        let parsed
        try { parsed = value ? JSON.parse(value) : {} } catch { return reject(new Error('editor Hub returned invalid JSON')) }
        if (response.statusCode < 200 || response.statusCode >= 300 || !parsed.ok) {
          return reject(new Error(parsed.error || `editor Hub request failed with ${response.statusCode}`))
        }
        resolve(parsed)
      })
    })
    request.once('timeout', () => request.destroy(new Error('editor Hub request timed out')))
    request.once('error', reject)
    if (payload) request.write(payload)
    request.end()
  })
}

async function readJson(file) {
  try { return JSON.parse(await fsp.readFile(file, 'utf8')) } catch { return null }
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

async function commandLine() {
  const command = process.argv[2]
  if (!['launch', 'shutdown', 'update'].includes(command)) throw new Error('usage: node hub-client.cjs <launch|shutdown|update>')
  const dataRoot = resolvePluginData()
  if (command === 'launch' || command === 'update') {
    const overrides = command === 'update' ? updateOverrides(process.argv.slice(3)) : {}
    const locator = await ensureHub({ dataRoot, ...overrides })
    if (command === 'update') return
    const launched = await hubRequest(locator, 'POST', '/v1/hub/launch', {})
    process.stdout.write(JSON.stringify({ ok: true, url: launched.url }) + '\n')
    return
  }
  const locator = await readTrustedLocator(hubPaths(dataRoot).locator)
  if (!locator) {
    process.stdout.write(JSON.stringify({ ok: true, status: 'stopped' }) + '\n')
    return
  }
  await hubRequest(locator, 'POST', '/v1/hub/quit', {})
  const deadline = Date.now() + 5_000
  while (Date.now() < deadline && await readTrustedLocator(hubPaths(dataRoot).locator)) await delay(50)
  process.stdout.write(JSON.stringify({ ok: true, status: 'stopped' }) + '\n')
}

function updateOverrides(args) {
  const options = {}
  for (let index = 0; index < args.length; index += 2) {
    if (args[index] === '--protocol-version') options.protocolVersion = Number(args[index + 1])
    else if (args[index] === '--runtime-version') options.runtimeVersion = args[index + 1]
    else if (args[index] === '--capabilities') options.capabilities = args[index + 1].split(',').filter(Boolean)
    else throw new Error(`unknown update argument: ${args[index]}`)
  }
  return options
}

module.exports = { HUB_CAPABILITIES, HUB_PROTOCOL_VERSION, ensureHub, hubPaths, hubRequest, readTrustedLocator, resolvePluginData, runtimeMetadata, validLocator }

if (require.main === module) {
  commandLine().catch((error) => {
    process.stderr.write(`${error.message}\n`)
    process.exitCode = 1
  })
}
