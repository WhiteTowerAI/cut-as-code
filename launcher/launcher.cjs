'use strict'

const fs = require('node:fs')
const fsp = require('node:fs/promises')
const os = require('node:os')
const path = require('node:path')
const { spawn } = require('node:child_process')

const PLUGIN_NAME = 'cut-as-code-editor'
const COMMAND_TIMEOUT_MS = 15_000
const MAX_OUTPUT_BYTES = 1024 * 1024

async function main(environment = process.env, platform = process.platform) {
  const codexHome = path.resolve(environment.CODEX_HOME || path.join(os.homedir(), '.codex'))
  const codex = codexSpec(environment, platform)
  const listed = await run(codex.command, codex.args, { timeoutMs: COMMAND_TIMEOUT_MS })
    .catch((error) => { throw actionable(error, 'Codex Plugin metadata is unavailable. Install or repair Codex, then try again.') })
  const metadata = parsePluginList(listed.stdout)
  const pluginRoot = await resolveInstalledPlugin(metadata, codexHome)
  const hub = await run(process.execPath, [path.join(pluginRoot, 'runtime', 'hub-client.cjs'), 'launch'], {
    timeoutMs: COMMAND_TIMEOUT_MS,
  }).catch((error) => { throw actionable(error, 'The Cut as Code Editor Hub could not be started.') })
  const url = parseLaunchUrl(hub.stdout)
  const browser = browserSpec(url, environment, platform)
  await run(browser.command, browser.args, { timeoutMs: COMMAND_TIMEOUT_MS, discardOutput: true })
    .catch(() => { throw new Error(`The browser could not be opened automatically. Open this URL manually: ${url}`) })
  return 'Cut as Code Editor opened.'
}

function commandSpec(command, args) {
  if (/\.(?:c?js|mjs)$/i.test(command)) return { command: process.execPath, args: [command, ...args] }
  return { command, args }
}

function codexSpec(environment, platform) {
  const args = ['plugin', 'list', '--json']
  if (environment.CAC_CODEX_CLI) return commandSpec(environment.CAC_CODEX_CLI, args)
  if (platform !== 'win32') return { command: 'codex', args }
  for (const directory of (environment.PATH || '').split(path.delimiter).filter(Boolean)) {
    const npmShim = path.join(directory, 'codex.cmd')
    const npmCli = path.join(directory, 'node_modules', '@openai', 'codex', 'bin', 'codex.js')
    if (fs.existsSync(npmShim) && fs.existsSync(npmCli)) {
      return { command: process.execPath, args: [npmCli, ...args] }
    }
    const executable = path.join(directory, 'codex.exe')
    if (fs.existsSync(executable)) return { command: executable, args }
  }
  return { command: 'codex.exe', args }
}

function parsePluginList(output) {
  let value
  try { value = JSON.parse(output) } catch { throw new Error('Codex returned invalid Plugin metadata.') }
  const installed = value?.installed
  if (!Array.isArray(installed)) throw new Error('Codex returned invalid Plugin metadata.')
  const match = installed.find((entry) => entry?.name === PLUGIN_NAME && entry.installed === true)
  if (!match || !safeSegment(match.marketplaceName) || !safeSegment(match.version)) {
    throw new Error('The Cut as Code Editor Plugin is not installed. Install it in Codex, then try again.')
  }
  return match
}

async function resolveInstalledPlugin(metadata, codexHome) {
  const versionsRoot = path.join(codexHome, 'plugins', 'cache', metadata.marketplaceName, PLUGIN_NAME)
  const root = path.join(versionsRoot, metadata.version)
  const manifestPath = path.join(root, '.codex-plugin', 'plugin.json')
  const hubClientPath = path.join(root, 'runtime', 'hub-client.cjs')
  const manifest = await readJson(manifestPath)
  const valid = await isDirectory(root)
    && await isFile(manifestPath)
    && manifest?.name === PLUGIN_NAME
    && manifest.version === metadata.version
    && await isFile(hubClientPath)
  if (!valid) {
    throw new Error('No valid installed Cut as Code Editor Plugin was found. Reinstall the Plugin, then try again.')
  }
  return root
}

function parseLaunchUrl(output) {
  let value
  try { value = JSON.parse(output) } catch { throw new Error('The Cut as Code Editor Hub returned an invalid launch response.') }
  if (value?.ok !== true || typeof value.url !== 'string') {
    throw new Error('The Cut as Code Editor Hub returned an invalid launch response.')
  }
  const url = new URL(value.url)
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1') {
    throw new Error('The Cut as Code Editor Hub returned an invalid launch URL.')
  }
  return url.href
}

function browserSpec(url, environment, platform) {
  if (environment.CAC_BROWSER_CLI) return commandSpec(environment.CAC_BROWSER_CLI, [url])
  if (platform === 'win32') return { command: 'rundll32.exe', args: ['url.dll,FileProtocolHandler', url] }
  if (platform === 'darwin') return { command: 'open', args: [url] }
  return { command: 'xdg-open', args: [url] }
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { shell: false, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
    let stdout = ''
    let stderr = ''
    let outputBytes = 0
    const timer = setTimeout(() => child.kill(), options.timeoutMs || COMMAND_TIMEOUT_MS)
    const collect = (target) => (chunk) => {
      outputBytes += chunk.length
      if (outputBytes > MAX_OUTPUT_BYTES) return child.kill()
      if (!options.discardOutput) {
        if (target === 'stdout') stdout += chunk
        else stderr += chunk
      }
    }
    child.stdout.on('data', collect('stdout'))
    child.stderr.on('data', collect('stderr'))
    child.once('error', (error) => { clearTimeout(timer); reject(error) })
    child.once('exit', (code, signal) => {
      clearTimeout(timer)
      if (outputBytes > MAX_OUTPUT_BYTES) return reject(new Error('Command output exceeded the safety limit.'))
      if (signal) return reject(new Error('Command timed out.'))
      if (code !== 0) return reject(new Error(stderr.trim() || `Command failed with exit code ${code}.`))
      resolve({ stdout: stdout.trim(), stderr: stderr.trim() })
    })
  })
}

function safeSegment(value) {
  return typeof value === 'string' && /^[A-Za-z0-9._+-]+$/.test(value) && value !== '.' && value !== '..'
}

async function readJson(file) {
  try { return JSON.parse(await fsp.readFile(file, 'utf8')) } catch { return null }
}

async function isFile(file) {
  try { return (await fsp.lstat(file)).isFile() } catch { return false }
}

async function isDirectory(directory) {
  try { return (await fsp.lstat(directory)).isDirectory() } catch { return false }
}

function actionable(error, message) {
  const wrapped = new Error(message)
  wrapped.cause = error
  return wrapped
}

module.exports = { main }

if (require.main === module) {
  main().then(
    (message) => process.stdout.write(`${message}\n`),
    (error) => { process.stderr.write(`${error.message}\n`); process.exitCode = 1 },
  )
}
