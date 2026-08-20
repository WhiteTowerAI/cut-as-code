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
const assetInventory = inspectPackagedScriptAndFontAssets(packageRoot, components)
components.push(...assetInventory.components)
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
  scope: 'all packaged files for secrets; executable, stylesheet, font, and runtime binary assets for third-party licensing',
  generated_from: {
    dependency_lock: 'ui/package-lock.json',
    package_builder: 'scripts/build_plugin_package.ps1',
  },
  license_audit: {
    status: 'pass',
    component_count: components.length,
    first_party_license: 'MIT',
    components: components.map(({ name, version, license, checksum, packagedPaths, evidence }) => ({
      name,
      version,
      license,
      checksum,
      packaged_paths: packagedPaths ?? [],
      evidence,
    })),
    unresolved: [],
  },
  third_party_asset_audit: {
    status: 'pass',
    scope: 'executable, stylesheet, font, and runtime binary assets',
    extensions: assetInventory.extensions,
    files_scanned: assetInventory.filesScanned,
    third_party: assetInventory.thirdParty,
    generated_bundles: assetInventory.generatedBundles,
    generated_stylesheets: assetInventory.generatedStylesheets,
    first_party_or_generated: assetInventory.firstPartyOrGenerated,
    unknown: [],
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
  const recipesRoot = path.join(root, 'skills', 'video-add-motion-graphics', 'recipes', 'animxyz')
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
    manifest_glob: 'skills/video-add-motion-graphics/recipes/animxyz/*/recipe.motion.yaml',
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

function inspectPackagedScriptAndFontAssets(root, dependencyComponents) {
  const extensions = ['.bin', '.cjs', '.css', '.dll', '.dylib', '.js', '.mjs', '.node', '.otf', '.so', '.ttf', '.wasm', '.woff', '.woff2']
  const files = walk(root)
    .filter((file) => extensions.includes(path.extname(file).toLowerCase()))
    .map((file) => ({ file, path: relative(root, file) }))
  const known = [
    inspectGsap(root),
    inspectFont(root, {
      name: 'Cal Sans',
      version: '1.000',
      path: 'skills/video-add-captions/public/fonts/CalSans-Regular.ttf',
      additionalPaths: ['skills/video-add-captions/examples/fonts/CalSans-Regular.ttf'],
      sha256: 'c7e50dba671a7b2e606d5bcb9390cbd5e4e1de269afc0bc98eb1eacc517fdb05',
      sourceRevision: '46b43bfb793e324d84a8c93f127d4addcadcbfd9',
      sourceRepository: 'https://github.com/calcom/font',
      licenseUrl: 'https://openfontlicense.org',
      evidenceStrings: [
        'Version 1.000',
        'Copyright 2021 The Cal Sans Project Authors (https://github.com/calcom/font)',
        'SIL Open Font License, Version 1.1',
        'https://openfontlicense.org',
      ],
    }),
    inspectFont(root, {
      name: 'Lexend',
      version: '1.007',
      path: 'skills/video-add-content-cards/assets/fonts/Lexend-VariableFont_wght.ttf',
      sha256: '91342a7f7da58a6bc398057da404b563d8890cc755ab312718a7cea515c09232',
      sourceRevision: '388ae39e02759a6c5ff40419e1c2c43c2736e533',
      sourceRepository: 'https://github.com/googlefonts/lexend',
      licenseUrl: 'https://scripts.sil.org/OFL',
      evidenceStrings: [
        'Version 1.007',
        'Copyright 2019 The Lexend Project Authors (https://github.com/googlefonts/lexend)',
        'SIL Open Font License, Version 1.1',
        'https://scripts.sil.org/OFL',
      ],
    }),
  ]
  const knownPaths = new Set(known.flatMap((item) => item.packagedPaths))
  const interComponent = dependencyComponents.find((item) => item.name === '@fontsource/inter')
  if (!interComponent) throw new Error('packaged Inter assets have no @fontsource/inter component')
  const interHashes = new Set(
    walk(path.join(repositoryRoot, 'ui', 'node_modules', '@fontsource', 'inter'))
      .filter((file) => ['.otf', '.ttf', '.woff', '.woff2'].includes(path.extname(file).toLowerCase()))
      .map((file) => sha256(fs.readFileSync(file))),
  )
  const thirdParty = known.flatMap((item) => item.packagedPaths.map((packagedPath) => ({
    path: packagedPath,
    component: item.name,
    sha256: item.checksum.value,
  })))
  const generatedBundles = []
  const generatedStylesheets = []
  const firstPartyOrGenerated = []
  const unknown = []
  for (const item of files) {
    if (knownPaths.has(item.path)) continue
    if (/^ui\/dist\/assets\/inter-[A-Za-z0-9-]+\.(?:woff2?|otf|ttf)$/.test(item.path)) {
      const hash = sha256(fs.readFileSync(item.file))
      if (!interHashes.has(hash)) {
        unknown.push(item.path)
        continue
      }
      thirdParty.push({ path: item.path, component: interComponent.name, sha256: hash })
      continue
    }
    if (/^ui\/dist\/assets\/index-[A-Za-z0-9_-]+\.js$/.test(item.path)) {
      const hash = assertGeneratedDistAsset(item)
      if (!hash) {
        unknown.push(item.path)
        continue
      }
      generatedBundles.push({
        path: item.path,
        sha256: hash,
        components: dependencyComponents
          .filter((component) => component.evidence.kind === 'npm-lockfile-and-installed-license')
          .map((component) => component.name)
          .sort(),
      })
      continue
    }
    if (/^ui\/dist\/assets\/index-[A-Za-z0-9_-]+\.css$/.test(item.path)) {
      const hash = assertGeneratedDistAsset(item)
      if (!hash) {
        unknown.push(item.path)
        continue
      }
      generatedStylesheets.push({
        path: item.path,
        sha256: hash,
        kind: 'generated-vite-stylesheet',
      })
      continue
    }
    if (/^skills\/video-add-motion-graphics\/recipes\/animxyz\/(?:[^/]+\/hyperframes\/)?_runtime\/animxyz\.css$/.test(item.path)) {
      const hash = sha256(fs.readFileSync(item.file))
      if (hash !== '4a133a5e4bf9ff2b3c87d7ef3a20064ccaab3c8838cafbf540c75d658f7c451d') unknown.push(item.path)
      else thirdParty.push({ path: item.path, component: '@animxyz/core', sha256: hash })
      continue
    }
    if (isFirstPartyOrGeneratedAsset(item.path)) firstPartyOrGenerated.push(item.path)
    else unknown.push(item.path)
  }
  if (generatedBundles.length !== 1) unknown.push(...generatedBundles.map((item) => item.path))
  if (generatedStylesheets.length !== 1) unknown.push(...generatedStylesheets.map((item) => item.path))
  if (unknown.length) throw new Error(`unknown third-party runtime assets: ${unknown.join(', ')}`)
  return {
    extensions,
    filesScanned: files.length,
    components: known,
    thirdParty,
    generatedBundles,
    generatedStylesheets,
    firstPartyOrGenerated,
  }
}

function assertGeneratedDistAsset(item) {
  const source = path.join(repositoryRoot, ...item.path.split('/'))
  if (!fs.existsSync(source) || !fs.statSync(source).isFile()) return undefined
  const hash = sha256(fs.readFileSync(item.file))
  return hash === sha256(fs.readFileSync(source)) ? hash : undefined
}

function inspectGsap(root) {
  const packagedPath = 'skills/video-add-captions/public/gsap.min.js'
  const file = requiredPackagedFile(root, packagedPath)
  const bytes = fs.readFileSync(file)
  const hash = sha256(bytes)
  const expectedHash = 'c71e401021a12cfa35fe7afcf45240c0dea1ca87016d3921b9ecd35424e49026'
  if (hash !== expectedHash) throw new Error(`packaged GSAP hash changed: ${hash}`)
  const source = bytes.toString('utf8')
  for (const evidence of ['GSAP 3.12.5', 'Copyright 2024, GreenSock', 'https://gsap.com/standard-license']) {
    if (!source.includes(evidence)) throw new Error(`packaged GSAP license evidence is missing: ${evidence}`)
  }
  return {
    name: 'GSAP',
    version: '3.12.5',
    license: 'LicenseRef-GSAP-Standard',
    downloadLocation: 'https://gsap.com',
    checksum: { algorithm: 'SHA256', value: hash },
    packagedPaths: [packagedPath],
    licenseText: 'Copyright 2024, GreenSock. All rights reserved. Subject to the terms at https://gsap.com/standard-license or, for Club GSAP members, the agreement issued with that membership.',
    evidence: {
      kind: 'embedded-javascript-license-header',
      packaged_path: packagedPath,
      license_url: 'https://gsap.com/standard-license',
      source_revision: 'a7646f5b8acf6369f30df1b04aa9a9c85dfae38c',
      sha256: hash,
    },
  }
}

function inspectFont(root, definition) {
  const paths = [definition.path, ...(definition.additionalPaths ?? [])]
  const file = requiredPackagedFile(root, definition.path)
  const bytes = fs.readFileSync(file)
  const hash = sha256(bytes)
  if (hash !== definition.sha256) throw new Error(`packaged ${definition.name} hash changed: ${hash}`)
  for (const packagedPath of paths.slice(1)) {
    const additionalHash = sha256(fs.readFileSync(requiredPackagedFile(root, packagedPath)))
    if (additionalHash !== definition.sha256) throw new Error(`packaged ${definition.name} hash changed at ${packagedPath}: ${additionalHash}`)
  }
  const metadata = extractSfntNameText(bytes)
  for (const evidence of definition.evidenceStrings) {
    if (!metadata.includes(evidence)) throw new Error(`packaged ${definition.name} license evidence is missing: ${evidence}`)
  }
  return {
    name: definition.name,
    version: definition.version,
    license: 'OFL-1.1',
    downloadLocation: definition.sourceRepository,
    checksum: { algorithm: 'SHA256', value: hash },
    packagedPaths: paths,
    licenseText: `This Font Software is licensed under the SIL Open Font License, Version 1.1. The packaged font name table identifies ${definition.sourceRepository} and ${definition.licenseUrl}.`,
    evidence: {
      kind: 'embedded-sfnt-name-table',
      packaged_path: definition.path,
      source_repository: definition.sourceRepository,
      license_url: definition.licenseUrl,
      source_revision: definition.sourceRevision,
      sha256: hash,
    },
  }
}

function extractSfntNameText(bytes) {
  return `${bytes.toString('utf8')}\n${Buffer.from(bytes).swap16().toString('utf16le')}`
}

function requiredPackagedFile(root, packagedPath) {
  const file = path.join(root, ...packagedPath.split('/'))
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) throw new Error(`required packaged third-party asset is missing: ${packagedPath}`)
  return file
}

function isFirstPartyOrGeneratedAsset(packagedPath) {
  if (packagedPath === 'hooks/launch-editor.cjs') return true
  if (/^runtime\/(?:hub|hub-client|hub-trust|mcp|sidecar)\.cjs$/.test(packagedPath)) return true
  if (/^skills\/video-add-motion-graphics\/recipes\/animxyz\/[^/]+\/hyperframes\/hf-(?:adapter|recipe)\.js$/.test(packagedPath)) return true
  return new Set([
    'skills/video-add-motion-graphics/scripts/audit_sticker_metadata.mjs',
    'skills/video-add-motion-graphics/scripts/convert_codrops_recipes.mjs',
    'skills/video-add-motion-graphics/scripts/convert_motion_anything_recipes.mjs',
    'skills/video-add-motion-graphics/scripts/import_sticker_recipes.mjs',
    'skills/video-add-motion-graphics/scripts/recipe_library.mjs',
    'skills/video-add-motion-graphics/scripts/sticker_recipe_catalog.mjs',
    'skills/video-add-motion-graphics/scripts/sticker_semantics.mjs',
    'skills/video-add-motion-graphics/scripts/verify_codrops_hyperframes.mjs',
    'skills/video-add-captions/scripts/build_style_preview_gallery.mjs',
    'skills/video-add-captions/scripts/caption_interaction.mjs',
    'skills/video-add-captions/scripts/caption_interaction_state.mjs',
    'skills/video-add-captions/scripts/caption_style_config.mjs',
    'skills/video-add-captions/scripts/check_caption_interaction.mjs',
    'skills/video-add-captions/scripts/check_caption_style_config.mjs',
    'skills/video-add-captions/scripts/generate_caption_project.mjs',
    'skills/video-add-content-cards/examples/build-gallery.mjs',
    'skills/video-add-content-cards/examples/shoot.mjs',
  ]).has(packagedPath)
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
      : item.packagedPaths?.length
        ? `Packaged path: ${item.packagedPaths.join(', ')}; source revision ${item.evidence.source_revision}; license evidence ${item.evidence.license_url}; SHA-256 ${item.checksum.value}.`
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
      ...(item.packagedPaths?.length ? {
        packageFileName: item.packagedPaths.join(', '),
        sourceInfo: `Packaged asset evidence: ${item.evidence.kind}; source revision ${item.evidence.source_revision}; license ${item.evidence.license_url}`,
      } : {}),
      externalRefs: item.name === '@animxyz/core' || item.packagedPaths?.length ? [] : [{
        referenceCategory: 'PACKAGE-MANAGER',
        referenceType: 'purl',
        referenceLocator: `pkg:npm/${encodeURIComponent(item.name)}@${item.version}`,
      }],
    })),
    hasExtractedLicensingInfos: [{
      licenseId: 'LicenseRef-GSAP-Standard',
      extractedText: items.find((item) => item.name === 'GSAP')?.licenseText ?? 'NOASSERTION',
      seeAlsos: ['https://gsap.com/standard-license'],
    }],
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
