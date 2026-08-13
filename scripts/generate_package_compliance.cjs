#!/usr/bin/env node

const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')

const [repositoryRootValue, packageRootValue] = process.argv.slice(2)
if (!repositoryRootValue || !packageRootValue) {
  throw new Error('usage: generate_package_compliance.cjs <repository-root> <package-root>')
}

const repositoryRoot = path.resolve(repositoryRootValue)
const packageRoot = path.resolve(packageRootValue)
const lock = readJson(path.join(repositoryRoot, 'ui', 'package-lock.json'))
const rootPackage = lock.packages?.['']
if (!rootPackage || typeof rootPackage.dependencies !== 'object') {
  throw new Error('ui/package-lock.json has no production dependency set')
}

const components = productionDependencyClosure(lock, Object.keys(rootPackage.dependencies))
const animxyz = inspectAnimxyz(packageRoot)
components.push(animxyz.component)
components.sort((left, right) => left.name.localeCompare(right.name, 'en'))

const unresolved = components.filter((component) => !component.license || component.license === 'NOASSERTION')
if (unresolved.length) {
  throw new Error(`package has unresolved component licenses: ${unresolved.map((item) => item.name).join(', ')}`)
}

writeText(path.join(packageRoot, 'THIRD_PARTY_NOTICES.md'), notices(components, animxyz))
writeJson(path.join(packageRoot, 'SBOM.spdx.json'), spdx(components))

const auditPath = path.join(packageRoot, 'PACKAGE_AUDIT.json')
const baseAudit = {
  schema_version: 1,
  scope: 'all packaged files',
  generated_from: {
    dependency_lock: 'ui/package-lock.json',
    package_builder: 'scripts/build_plugin_package.ps1',
  },
  license_audit: {
    status: 'pass',
    component_count: components.length,
    first_party_license: 'MIT',
    components: components.map(({ name, version, license, evidence }) => ({ name, version, license, evidence })),
    unresolved: [],
  },
  secret_audit: {
    status: 'pending',
    files_scanned: 0,
    bytes_scanned: 0,
    patterns: secretPatterns().map((item) => item.id),
    findings: [],
  },
  vendored_sources: [animxyz.audit],
}
writeJson(auditPath, baseAudit)

const secretAudit = scanSecrets(packageRoot)
if (secretAudit.findings.length) {
  throw new Error(`package secret audit failed: ${secretAudit.findings.map((item) => `${item.pattern}:${item.path}`).join(', ')}`)
}
writeJson(auditPath, {
  ...baseAudit,
  secret_audit: { status: 'pass', ...secretAudit },
})

function productionDependencyClosure(packageLock, roots) {
  const queued = [...roots]
  const seen = new Set()
  const result = []
  while (queued.length) {
    const name = queued.shift()
    if (seen.has(name)) continue
    seen.add(name)
    const packagePath = `node_modules/${name}`
    const metadata = packageLock.packages?.[packagePath]
    if (!metadata) throw new Error(`production dependency is missing from lockfile: ${name}`)
    const licensePath = path.join(repositoryRoot, 'ui', 'node_modules', ...name.split('/'), 'LICENSE')
    if (!fs.statSync(licensePath).isFile()) throw new Error(`production dependency has no bundled LICENSE: ${name}`)
    const integrity = parseIntegrity(metadata.integrity, name)
    result.push({
      name,
      version: metadata.version,
      license: metadata.license,
      downloadLocation: metadata.resolved,
      checksum: integrity,
      licenseText: fs.readFileSync(licensePath, 'utf8').trim(),
      evidence: {
        kind: 'npm-lockfile-and-installed-license',
        lockfile_path: packagePath,
        license_path: `ui/node_modules/${name}/LICENSE`,
      },
    })
    queued.push(...Object.keys(metadata.dependencies ?? {}))
  }
  return result
}

function inspectAnimxyz(root) {
  const recipesRoot = path.join(root, 'skills', 'video-add-graphic-motion', 'recipes', 'animxyz')
  const manifests = walk(recipesRoot).filter((file) => path.basename(file) === 'recipe.motion.yaml')
  if (manifests.length !== 20) throw new Error(`expected 20 packaged AnimXYZ manifests, found ${manifests.length}`)
  for (const manifest of manifests) {
    const source = fs.readFileSync(manifest, 'utf8')
    if (!/^\s*spdx:\s*MIT\s*$/m.test(source) || !/^\s*upstream:\s*["']?https:\/\/animxyz\.com["']?\s*$/m.test(source)) {
      throw new Error(`AnimXYZ license declaration is missing or inconsistent: ${relative(root, manifest)}`)
    }
  }
  const cssFiles = walk(recipesRoot).filter((file) => path.basename(file) === 'animxyz.css')
  if (!cssFiles.length) throw new Error('packaged AnimXYZ CSS is missing')
  const hashes = [...new Set(cssFiles.map((file) => sha256(fs.readFileSync(file))))]
  if (hashes.length !== 1) throw new Error('packaged AnimXYZ CSS copies do not match')
  const hash = hashes[0]
  const expectedHash = '4a133a5e4bf9ff2b3c87d7ef3a20064ccaab3c8838cafbf540c75d658f7c451d'
  if (hash !== expectedHash) throw new Error(`packaged AnimXYZ CSS hash changed: ${hash}`)
  const evidence = {
    kind: 'vendored-manifest-declarations',
    manifest_count: manifests.length,
    manifest_glob: 'skills/video-add-graphic-motion/recipes/animxyz/*/recipe.motion.yaml',
    source_repository: 'https://github.com/nexu-io/motion-anything',
    source_revision: 'b016900d9ee92fc2d3e4dc520359cc8999d2ed4e',
    upstream: 'https://animxyz.com',
  }
  return {
    component: {
      name: '@animxyz/core',
      version: 'vendored',
      license: 'MIT',
      downloadLocation: 'NOASSERTION',
      checksum: { algorithm: 'SHA256', value: hash },
      licenseText: 'MIT license declared by every packaged AnimXYZ recipe manifest. The upstream package version and standalone license file were not preserved in the vendored source; provenance is bound to the frozen CSS hash and motion-anything revision below.',
      evidence,
    },
    audit: {
      name: '@animxyz/core',
      packaged_paths: cssFiles.map((file) => relative(root, file)).sort(),
      sha256: hash,
      license: 'MIT',
      license_evidence: evidence,
    },
  }
}

function notices(items, animxyzInfo) {
  const rows = items.map((item) => `| ${item.name} | ${item.version} | ${item.license} |`).join('\n')
  const sections = items.map((item) => [
    `## ${item.name} ${item.version}`,
    '',
    `License: ${item.license}`,
    '',
    item.name === '@animxyz/core'
      ? `Vendored through nexu-io/motion-anything revision ${animxyzInfo.audit.license_evidence.source_revision}; upstream ${animxyzInfo.audit.license_evidence.upstream}; frozen CSS SHA-256 ${animxyzInfo.audit.sha256}.`
      : `Source: ${item.downloadLocation}`,
    '',
    '```text',
    item.licenseText,
    '```',
  ].join('\n')).join('\n\n')
  return [
    '# Third-Party Notices',
    '',
    'This file is generated from the production UI lockfile and the exact vendored sources included in the local editor package.',
    '',
    '| Component | Version | License |',
    '| --- | --- | --- |',
    rows,
    '',
    sections,
    '',
  ].join('\n')
}

function spdx(items) {
  return {
    spdxVersion: 'SPDX-2.3',
    dataLicense: 'CC0-1.0',
    SPDXID: 'SPDXRef-DOCUMENT',
    name: 'cut-as-code-editor-third-party',
    documentNamespace: 'https://github.com/WhiteTowerAI/cut-as-code/sbom/cut-as-code-editor-0.0.0',
    creationInfo: {
      created: '2020-01-01T00:00:00Z',
      creators: ['Tool: cut-as-code package compliance generator'],
    },
    packages: items.map((item) => ({
      name: item.name,
      SPDXID: `SPDXRef-Package-${item.name.replace(/[^A-Za-z0-9.-]/g, '-')}`,
      versionInfo: item.version,
      downloadLocation: item.downloadLocation,
      filesAnalyzed: false,
      licenseConcluded: item.license,
      licenseDeclared: item.license,
      copyrightText: 'NOASSERTION',
      checksums: [{ algorithm: item.checksum.algorithm, checksumValue: item.checksum.value }],
      externalRefs: item.name === '@animxyz/core' ? [] : [{
        referenceCategory: 'PACKAGE-MANAGER',
        referenceType: 'purl',
        referenceLocator: `pkg:npm/${encodeURIComponent(item.name)}@${item.version}`,
      }],
    })),
  }
}

function scanSecrets(root) {
  const patterns = secretPatterns()
  const findings = []
  let bytesScanned = 0
  const files = walk(root).sort()
  for (const file of files) {
    const bytes = fs.readFileSync(file)
    bytesScanned += bytes.length
    const source = bytes.toString('latin1')
    for (const pattern of patterns) {
      pattern.expression.lastIndex = 0
      if (pattern.expression.test(source)) findings.push({ pattern: pattern.id, path: relative(root, file) })
    }
  }
  return {
    files_scanned: files.length,
    bytes_scanned: bytesScanned,
    patterns: patterns.map((item) => item.id),
    findings,
  }
}

function secretPatterns() {
  return [
    { id: 'private-key-pem', expression: /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/g },
    { id: 'aws-access-key-id', expression: /AKIA[0-9A-Z]{16}/g },
    { id: 'github-token', expression: /gh[pousr]_[A-Za-z0-9]{36,255}/g },
    { id: 'openai-api-key', expression: /sk-[A-Za-z0-9]{32,}/g },
    { id: 'slack-token', expression: /xox[baprs]-[A-Za-z0-9-]{20,}/g },
  ]
}

function parseIntegrity(value, name) {
  const match = /^(sha(?:256|384|512))-([A-Za-z0-9+/=]+)$/.exec(value ?? '')
  if (!match) throw new Error(`production dependency has no supported integrity checksum: ${name}`)
  return { algorithm: match[1].toUpperCase(), value: Buffer.from(match[2], 'base64').toString('hex') }
}

function walk(root) {
  const result = []
  for (const entry of fs.readdirSync(root, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
    const item = path.join(root, entry.name)
    if (entry.isDirectory()) result.push(...walk(item))
    else if (entry.isFile()) result.push(item)
  }
  return result
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'))
}

function writeJson(file, value) {
  writeText(file, `${JSON.stringify(value, null, 2)}\n`)
}

function writeText(file, value) {
  fs.writeFileSync(file, value.replace(/\r\n/g, '\n'), 'utf8')
}

function sha256(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex')
}

function relative(root, file) {
  return path.relative(root, file).split(path.sep).join('/')
}
