'use strict'

const crypto = require('node:crypto')

function challengeProof(controlToken, challenge, instanceId, pid) {
  return crypto.createHmac('sha256', controlToken)
    .update(`${challenge}:${instanceId}:${pid}`)
    .digest('base64url')
}

function locatorProof(lockToken, locator) {
  return crypto.createHmac('sha256', lockToken)
    .update(JSON.stringify({
      schemaVersion: locator.schemaVersion,
      host: locator.host,
      port: locator.port,
      pid: locator.pid,
      instanceId: locator.instanceId,
      protocolVersion: locator.protocolVersion,
      runtimeVersion: locator.runtimeVersion,
      capabilities: locator.capabilities,
      controlToken: locator.controlToken,
    }))
    .digest('base64url')
}

function safeEqual(left, right) {
  if (typeof left !== 'string' || typeof right !== 'string') return false
  const leftBytes = Buffer.from(left)
  const rightBytes = Buffer.from(right)
  return leftBytes.length === rightBytes.length && crypto.timingSafeEqual(leftBytes, rightBytes)
}

module.exports = { challengeProof, locatorProof, safeEqual }
