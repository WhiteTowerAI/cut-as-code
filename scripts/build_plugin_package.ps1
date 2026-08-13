[CmdletBinding()]
param([string]$OutputPath)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot '.superpowers\package\cut-as-code-editor.zip'
}
$outputCandidate = if ([System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path $repoRoot $OutputPath }
$outputAbsolute = [System.IO.Path]::GetFullPath($outputCandidate)
$outputDirectory = Split-Path -Parent $outputAbsolute
$packageName = 'cut-as-code-editor'
$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("$packageName-" + [guid]::NewGuid().ToString('N'))
$packageRoot = Join-Path $stageRoot $packageName
$skillNames = @('cut-as-code', 'video-understand', 'video-cut', 'video-color-grade', 'video-add-b-roll', 'video-add-graphic-motion', 'video-add-captions', 'video-add-content-cards', 'video-edit-compare', 'video-to-shorts')
$excludedDirectoryNames = @('.git', '.hyperframes', '__pycache__', 'cache', 'docs', 'fixtures', 'node_modules', 'screenshots', 'test-results', 'tests', 'work')
$excludedExtensions = @('.gif', '.jpeg', '.jpg', '.map', '.m4a', '.mkv', '.mov', '.mp3', '.mp4', '.png', '.pyc', '.tmp', '.wav', '.webm', '.webp')
$allowedEditorAssets = @('ASSET_MANIFEST.json', 'viewer-poster.png', 'brand.png', 'caption-boxed.png', 'caption-clean.png', 'caption-minimal.png', 'caption-pill.png', 'caption-shorts.png', 'caption-social-bold.png', 'caption-stroked.png', 'card-cta.png', 'card-lower-third.png', 'card-product.png', 'card-quote.png', 'card-split.png', 'card-stat.png', 'city.png', 'founder.png', 'icon-filter.svg', 'icon-search.svg', 'icon-upload.svg', 'product.png')
$normalTimestamp = [DateTimeOffset]::new(2020, 1, 1, 0, 0, 0, [TimeSpan]::Zero)

function Test-ExcludedRelativePath {
    param([Parameter(Mandatory = $true)][string]$Relative, [switch]$GraphicMotion)
    $segments = $Relative -split '[\\/]'
    if ($segments | Where-Object { $excludedDirectoryNames -contains $_ -or $_ -like '.env*' }) { return $true }
    $normalized = $Relative -replace '\\', '/'
    if ($normalized -eq 'package-video-add-graphic-motion.SKILL.md') { return $true }
    if ($normalized -match '(^|/)assets/editor/') { return -not ($allowedEditorAssets -contains [System.IO.Path]::GetFileName($normalized)) }
    if ($GraphicMotion -and $segments[0] -eq 'recipes' -and $segments[1] -ne 'animxyz' -and $Relative -ne 'recipes\ATTRIBUTION.md') { return $true }
    return ($excludedExtensions -contains [System.IO.Path]::GetExtension($Relative).ToLowerInvariant())
}

function Copy-AllowlistedTree {
    param([Parameter(Mandatory = $true)][string]$Source, [Parameter(Mandatory = $true)][string]$Destination, [switch]$GraphicMotion)
    $sourceItem = Get-Item -LiteralPath $Source
    Get-ChildItem -LiteralPath $sourceItem.FullName -Recurse -File -Force | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($sourceItem.FullName.Length).TrimStart('\', '/')
        if (Test-ExcludedRelativePath -Relative $relative -GraphicMotion:$GraphicMotion) { return }
        $destinationFile = Join-Path $Destination $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destinationFile) | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destinationFile -Force
    }
}

function Assert-PackageContents {
    param([Parameter(Mandatory = $true)][string]$Root)
    $requiredFiles = @('.codex-plugin\plugin.json', '.mcp.json', 'LICENSE', 'README.md', 'runtime\mcp.cjs', 'runtime\project_snapshot.py', 'runtime\protocol_service.py', 'runtime\sidecar.cjs', 'ui\dist\index.html')
    foreach ($requiredFile in $requiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $Root $requiredFile) -PathType Leaf)) { throw "Package is missing required file: $requiredFile" }
    }
    foreach ($skillName in $skillNames) {
        if (-not (Test-Path -LiteralPath (Join-Path $Root "skills\$skillName\SKILL.md") -PathType Leaf)) { throw "Package is missing skill entrypoint: $skillName" }
    }
    foreach ($item in Get-ChildItem -LiteralPath $Root -Recurse -File -Force) {
        $relative = $item.FullName.Substring($Root.Length).TrimStart('\', '/')
        if (Test-ExcludedRelativePath -Relative $relative) { throw "Package contains forbidden file: $relative" }
    }
}

function Write-DeterministicZip {
    param([Parameter(Mandatory = $true)][string]$Root, [Parameter(Mandatory = $true)][string]$Output)
    $entries = @()
    foreach ($item in Get-ChildItem -LiteralPath $Root -Recurse -File -Force) {
        $relative = $item.FullName.Substring($Root.Length).TrimStart('\', '/') -replace '\\', '/'
        $entryName = "$packageName/$relative"
        if ($entryName -match '^[A-Za-z]:|^/' -or $entryName.Split('/') -contains '..') { throw "Unsafe archive entry: $entryName" }
        $entries += [pscustomobject]@{ Name = $entryName; Path = $item.FullName }
    }
    [Array]::Sort($entries, [System.Comparison[object]]{ param($left, $right) [StringComparer]::Ordinal.Compare($left.Name, $right.Name) })
    $seen = @{}
    foreach ($entry in $entries) {
        $key = $entry.Name.ToLowerInvariant()
        if ($seen.ContainsKey($key)) { throw "Duplicate or case-colliding archive entry: $($entry.Name)" }
        $seen[$key] = $true
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null
    if (Test-Path -LiteralPath $Output) { Remove-Item -LiteralPath $Output -Force }
    $stream = [System.IO.File]::Open($Output, [System.IO.FileMode]::CreateNew)
    try {
        $zip = [System.IO.Compression.ZipArchive]::new($stream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
        try {
            foreach ($entry in $entries) {
                $archiveEntry = $zip.CreateEntry($entry.Name, [System.IO.Compression.CompressionLevel]::Optimal)
                $archiveEntry.LastWriteTime = $normalTimestamp
                $archiveEntry.ExternalAttributes = 0x81A40000
                $source = [System.IO.File]::OpenRead($entry.Path)
                try { $target = $archiveEntry.Open(); try { $source.CopyTo($target) } finally { $target.Dispose() } } finally { $source.Dispose() }
            }
        } finally { $zip.Dispose() }
    } finally { $stream.Dispose() }
}

try {
    Push-Location (Join-Path $repoRoot 'ui')
    try {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "UI build failed with exit code $LASTEXITCODE" }
    } finally { Pop-Location }

    New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
    foreach ($file in @('.mcp.json', 'LICENSE', 'README.md')) { Copy-Item -LiteralPath (Join-Path $repoRoot $file) -Destination (Join-Path $packageRoot $file) -Force }
    Copy-AllowlistedTree -Source (Join-Path $repoRoot '.codex-plugin') -Destination (Join-Path $packageRoot '.codex-plugin')
    Copy-AllowlistedTree -Source (Join-Path $repoRoot 'runtime') -Destination (Join-Path $packageRoot 'runtime')
    Copy-AllowlistedTree -Source (Join-Path $repoRoot 'ui\dist') -Destination (Join-Path $packageRoot 'ui\dist')
    foreach ($skillName in $skillNames) {
        Copy-AllowlistedTree -Source (Join-Path $repoRoot "skills\$skillName") -Destination (Join-Path $packageRoot "skills\$skillName") -GraphicMotion:($skillName -eq 'video-add-graphic-motion')
    }
    Copy-Item -LiteralPath (Join-Path $repoRoot 'runtime\package-video-add-graphic-motion.SKILL.md') -Destination (Join-Path $packageRoot 'skills\video-add-graphic-motion\SKILL.md') -Force
    Assert-PackageContents -Root $packageRoot
    Write-DeterministicZip -Root $packageRoot -Output $outputAbsolute
    Write-Output "Built local plugin package: $outputAbsolute"
} finally {
    if (Test-Path -LiteralPath $stageRoot) { Remove-Item -LiteralPath $stageRoot -Recurse -Force }
}
