'use strict'

const fsp = require('node:fs/promises')
const path = require('node:path')
const { spawn } = require('node:child_process')
const readline = require('node:readline')

const MCP_TOOL_ALLOWLIST = Object.freeze(['open_editor'])
const RUNTIME_ROOT = __dirname
const PACKAGE_ROOT = path.resolve(RUNTIME_ROOT, '..')
const UI_ROOT = path.join(PACKAGE_ROOT, 'ui', 'dist')
const sidecars = new Map()
const startingSidecars = new Map()

const TOOL = Object.freeze({
  name: 'open_editor',
  description: 'Open one explicit local Cut as Code project in the localhost editor.',
  inputSchema: {
    type: 'object',
    additionalProperties: false,
    required: ['project_root'],
    properties: { project_root: { type: 'string', minLength: 1 } },
  },
})

async function main() {
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity })
  input.on('line', (line) => handleLine(line).catch((error) => respondError(null, -32603, error.message)))
  await new Promise((resolve) => process.stdin.once('end', resolve))
  await stopSidecars()
}

async function handleLine(line) {
  let request
  try { request = JSON.parse(line) } catch { return respondError(null, -32700, 'invalid JSON-RPC request') }
  const id = Object.prototype.hasOwnProperty.call(request, 'id') ? request.id : null
  if (request.method === 'initialize') return respond(id, { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'cut-as-code-editor', version: '0.1.0' } })
  if (request.method === 'tools/list') return respond(id, { tools: [TOOL] })
  if (request.method === 'tools/call') return callTool(id, request.params)
  if (request.method === 'shutdown') {
    await stopSidecars()
    return respond(id, {})
  }
  return respondError(id, -32601, 'method not found')
}

async function callTool(id, params) {
  if (!params || !MCP_TOOL_ALLOWLIST.includes(params.name)) return respondError(id, -32602, 'unknown tool')
  const root = await canonicalProjectRoot(params.arguments?.project_root)
  const details = await openEditor(root)
  return respond(id, { content: [{ type: 'text', text: JSON.stringify(details) }] })
}

async function openEditor(projectRoot) {
  let owned = sidecars.get(projectRoot)
  if (!owned || owned.child.exitCode !== null || owned.child.killed) {
    if (owned) sidecars.delete(projectRoot)
    let starting = startingSidecars.get(projectRoot)
    if (!starting) {
      starting = startSidecar(projectRoot).then((started) => {
        sidecars.set(projectRoot, started)
        return started
      }).finally(() => startingSidecars.delete(projectRoot))
      startingSidecars.set(projectRoot, starting)
    }
    owned = await starting
  }
  const armed = await owned.call('arm_launch')
  if (!armed.ok || typeof armed.url !== 'string') throw new Error(armed.error || 'could not arm editor launch')
  return {
    pid: owned.child.pid,
    projectRoot,
    url: armed.url,
    projectId: owned.projectId,
  }
}

async function startSidecar(projectRoot) {
  const child = spawn(process.execPath, [
    path.join(RUNTIME_ROOT, 'sidecar.cjs'),
    '--project-root', projectRoot,
    '--ui-root', UI_ROOT,
  ], { cwd: RUNTIME_ROOT, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true })
  let stderr = ''
  child.stderr.on('data', (chunk) => { stderr = `${stderr}${chunk}`.slice(-8_192) })
  const lines = readline.createInterface({ input: child.stdout, crlfDelay: Infinity })
  const ready = await waitForLine(lines, child, () => `editor sidecar startup failed: ${stderr}`)
  let startup
  try { startup = JSON.parse(ready) } catch { throw new Error('editor sidecar returned invalid startup metadata') }
  if (startup.host !== '127.0.0.1' || !Number.isInteger(startup.port) || !startup.projectId) {
    child.kill()
    throw new Error('editor sidecar returned invalid startup metadata')
  }

  let requestId = 0
  const pending = new Map()
  lines.on('line', (line) => {
    let response
    try { response = JSON.parse(line) } catch { return }
    const request = pending.get(response.id)
    if (!request) return
    pending.delete(response.id)
    clearTimeout(request.timer)
    request.resolve(response)
  })
  child.once('exit', () => {
    sidecars.delete(projectRoot)
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

async function canonicalProjectRoot(value) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('project_root is required')
  const root = await fsp.realpath(path.resolve(value))
  const manifest = path.join(root, 'work', 'project.json')
  if (!(await isFile(manifest))) throw new Error('project_root must contain work/project.json')
  return root
}

async function stopSidecars() {
  await Promise.allSettled(startingSidecars.values())
  const stopped = []
  for (const owned of sidecars.values()) {
    stopped.push(waitForExit(owned.child, 2_000))
    owned.child.stdin.end()
  }
  await Promise.all(stopped)
  for (const owned of sidecars.values()) if (owned.child.exitCode === null) owned.child.kill()
  sidecars.clear()
}

function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null) return Promise.resolve()
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, timeoutMs)
    child.once('exit', () => { clearTimeout(timer); resolve() })
  })
}

async function isFile(value) {
  try { return (await fsp.stat(value)).isFile() } catch { return false }
}

function respond(id, result) { process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, result })}\n`) }
function respondError(id, code, message) { process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, error: { code, message } })}\n`) }

main().catch((error) => {
  process.stderr.write(`${error.message}\n`)
  process.exitCode = 1
})
