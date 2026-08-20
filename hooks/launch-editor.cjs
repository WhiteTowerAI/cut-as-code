'use strict'

const path = require('node:path')
const { ensureHub, hubRequest } = require('../runtime/hub-client.cjs')
const { openBrowser } = require('../runtime/mcp.cjs')

const LAUNCH_PROMPT = 'Open Cut as Code Editor'

async function runHook(input, dependencies = {}) {
  if (input?.hook_event_name !== 'UserPromptSubmit' || input.prompt !== LAUNCH_PROMPT) return null
  const pluginRootValue = dependencies.pluginRoot || process.env.PLUGIN_ROOT || process.env.CLAUDE_PLUGIN_ROOT
  if (!pluginRootValue) throw new Error('Plugin root is unavailable')
  const pluginRoot = path.resolve(pluginRootValue)
  const locate = dependencies.ensureHub || ensureHub
  const request = dependencies.hubRequest || hubRequest
  const launchBrowser = dependencies.openBrowser || openBrowser
  const locator = await locate({ pluginRoot })
  const launched = await request(locator, 'POST', '/v1/hub/launch', {})
  await launchBrowser(launched.url)
  return { decision: 'block', reason: 'Cut as Code Editor opened.' }
}

async function readInput() {
  let body = ''
  process.stdin.setEncoding('utf8')
  for await (const chunk of process.stdin) {
    body += chunk
    if (body.length > 64 * 1024) throw new Error('Hook input is too large')
  }
  return JSON.parse(body)
}

async function main() {
  let input
  try {
    input = await readInput()
    const output = await runHook(input)
    if (output) process.stdout.write(JSON.stringify(output) + '\n')
  } catch {
    if (input?.prompt === LAUNCH_PROMPT) {
      process.stdout.write(JSON.stringify({ decision: 'block', reason: 'Cut as Code Editor could not be opened.' }) + '\n')
      return
    }
    process.exitCode = 1
  }
}

module.exports = { LAUNCH_PROMPT, runHook }

if (require.main === module) void main()
