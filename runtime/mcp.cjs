'use strict'

const path = require('node:path')
const { spawn } = require('node:child_process')
const readline = require('node:readline')
const { ensureHub, hubRequest } = require('./hub-client.cjs')

const MCP_TOOL_ALLOWLIST = Object.freeze(['open_editor'])
const PACKAGE_ROOT = path.resolve(__dirname, '..')

const TOOL = Object.freeze({
  name: 'open_editor',
  description: 'Open one explicit local Cut as Code project in the system default browser.',
  inputSchema: {
    type: 'object',
    additionalProperties: false,
    required: ['project_root'],
    properties: {
      project_root: { type: 'string', minLength: 1 },
      open_browser: {
        type: 'boolean',
        default: true,
        description: 'Open the editor in the system default browser. Set false only for automation.',
      },
    },
  },
})

async function main() {
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity })
  input.on('line', (line) => handleLine(line).catch((error) => respondError(null, -32603, error.message)))
  await new Promise((resolve) => process.stdin.once('end', resolve))
}

async function handleLine(line) {
  let request
  try { request = JSON.parse(line) } catch { return respondError(null, -32700, 'invalid JSON-RPC request') }
  const id = Object.prototype.hasOwnProperty.call(request, 'id') ? request.id : null
  if (request.method === 'initialize') return respond(id, { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'cut-as-code-editor', version: '0.1.0' } })
  if (request.method === 'tools/list') return respond(id, { tools: [TOOL] })
  if (request.method === 'tools/call') return callTool(id, request.params)
  if (request.method === 'shutdown') return respond(id, {})
  return respondError(id, -32601, 'method not found')
}

async function callTool(id, params) {
  if (!params || !MCP_TOOL_ALLOWLIST.includes(params.name)) return respondError(id, -32602, 'unknown tool')
  let openInBrowser
  try { openInBrowser = shouldOpenBrowser(params.arguments?.open_browser) } catch (error) {
    return respondError(id, -32602, error.message)
  }
  try {
    const locator = await ensureHub({ pluginRoot: PACKAGE_ROOT })
    const details = await hubRequest(locator, 'POST', '/v1/projects/open', { projectRoot: params.arguments?.project_root })
    const result = {
      pid: details.pid,
      projectRoot: details.projectRoot,
      url: details.url,
      projectId: details.projectId,
    }
    if (openInBrowser) await openBrowser(result.url)
    return respond(id, { content: [{ type: 'text', text: JSON.stringify(result) }] })
  } catch (error) {
    return respondError(id, -32602, error.message)
  }
}

function shouldOpenBrowser(value) {
  if (value === undefined) return true
  if (typeof value !== 'boolean') throw new Error('open_browser must be a boolean')
  return value
}

function browserLaunchSpec(platform = process.platform) {
  if (platform === 'win32') return {
    command: 'powershell.exe',
    args: ['-NoProfile', '-NonInteractive', '-Command', 'Start-Process -FilePath $args[0]'],
    options: { detached: true, stdio: 'ignore', windowsHide: true },
  }
  if (platform === 'darwin') return { command: 'open', args: [], options: { detached: true, stdio: 'ignore' } }
  return { command: 'xdg-open', args: [], options: { detached: true, stdio: 'ignore' } }
}

function openBrowser(url, spawnProcess = spawn, platform = process.platform) {
  const { command, args, options } = browserLaunchSpec(platform)
  const child = spawnProcess(command, [...args, url], options)
  child.unref()
  return new Promise((resolve, reject) => {
    child.once('spawn', resolve)
    child.once('error', () => reject(new Error(`Could not open the system browser automatically. Open this URL manually: ${url}`)))
  })
}

function respond(id, result) { process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, result })}\n`) }
function respondError(id, code, message) { process.stdout.write(`${JSON.stringify({ jsonrpc: '2.0', id, error: { code, message } })}\n`) }

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`)
    process.exitCode = 1
  })
}

module.exports = { TOOL, browserLaunchSpec, openBrowser, shouldOpenBrowser }
