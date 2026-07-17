param(
    [string]$OutputDirectory,
    [string]$ReviewDirectory,
    [string]$LandscapeVideo,
    [string]$ShortsVideo,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$skillRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $skillRoot)

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $skillRoot "assets\style-previews"
}
if (-not $ReviewDirectory) {
    $ReviewDirectory = Join-Path $repoRoot "TEST\videos\video-add-captions-work\phase-4-style-previews"
}
if (-not $LandscapeVideo) {
    $LandscapeVideo = Join-Path $ReviewDirectory "fixtures\preview-landscape.mp4"
}
if (-not $ShortsVideo) {
    $ShortsVideo = Join-Path $ReviewDirectory "fixtures\preview-shorts.mp4"
}

$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$ReviewDirectory = [System.IO.Path]::GetFullPath($ReviewDirectory)
$LandscapeVideo = [System.IO.Path]::GetFullPath($LandscapeVideo)
$ShortsVideo = [System.IO.Path]::GetFullPath($ShortsVideo)

$captionsFile = Join-Path $ReviewDirectory "fixtures\preview-captions.json"
$projectsDirectory = Join-Path $ReviewDirectory "generated-projects"
$interactionStatesDirectory = Join-Path $ReviewDirectory "interaction-states"
$logsDirectory = Join-Path $ReviewDirectory "logs"
$snapshotsDirectory = Join-Path $ReviewDirectory "review\snapshots"
$generationLog = Join-Path $ReviewDirectory "generation-log.txt"
$hyperframesLog = Join-Path $logsDirectory "hyperframes-checks.txt"
$generator = Join-Path $PSScriptRoot "generate_caption_project.mjs"
$interactionScript = Join-Path $PSScriptRoot "caption_interaction.mjs"
$snapshotTime = 1.55

$candidates = @(
    [pscustomobject]@{ id = "clean"; label = "Clean"; group = "core"; preset = "clean"; themeType = "none"; theme = $null; backgroundTheme = $null; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "minimal"; label = "Minimal"; group = "core"; preset = "minimal"; themeType = "none"; theme = $null; backgroundTheme = $null; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "social-bold"; label = "Social Bold"; group = "core"; preset = "social-bold"; themeType = "none"; theme = $null; backgroundTheme = $null; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "social-bold-karaoke"; label = "Social Bold Karaoke"; group = "core"; preset = "social-bold"; themeType = "none"; theme = $null; backgroundTheme = $null; strokeTheme = $null; highlightTheme = $null; karaoke = $true; orientation = "landscape" },

    [pscustomobject]@{ id = "pill-gray"; label = "Pill Gray"; group = "pill"; preset = "pill"; themeType = "background"; theme = "gray"; backgroundTheme = "gray"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "pill-yellow"; label = "Pill Yellow"; group = "pill"; preset = "pill"; themeType = "background"; theme = "yellow"; backgroundTheme = "yellow"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "pill-blue"; label = "Pill Blue"; group = "pill"; preset = "pill"; themeType = "background"; theme = "blue"; backgroundTheme = "blue"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "pill-pink"; label = "Pill Pink"; group = "pill"; preset = "pill"; themeType = "background"; theme = "pink"; backgroundTheme = "pink"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "pill-green"; label = "Pill Green"; group = "pill"; preset = "pill"; themeType = "background"; theme = "green"; backgroundTheme = "green"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },

    [pscustomobject]@{ id = "boxed-gray"; label = "Boxed Gray"; group = "boxed"; preset = "boxed"; themeType = "background"; theme = "gray"; backgroundTheme = "gray"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "boxed-yellow"; label = "Boxed Yellow"; group = "boxed"; preset = "boxed"; themeType = "background"; theme = "yellow"; backgroundTheme = "yellow"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "boxed-blue"; label = "Boxed Blue"; group = "boxed"; preset = "boxed"; themeType = "background"; theme = "blue"; backgroundTheme = "blue"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "boxed-pink"; label = "Boxed Pink"; group = "boxed"; preset = "boxed"; themeType = "background"; theme = "pink"; backgroundTheme = "pink"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "boxed-green"; label = "Boxed Green"; group = "boxed"; preset = "boxed"; themeType = "background"; theme = "green"; backgroundTheme = "green"; strokeTheme = $null; highlightTheme = $null; karaoke = $false; orientation = "landscape" },

    [pscustomobject]@{ id = "stroked-black"; label = "Stroked Black"; group = "stroked"; preset = "stroked"; themeType = "stroke"; theme = "black"; backgroundTheme = $null; strokeTheme = "black"; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "stroked-yellow"; label = "Stroked Yellow"; group = "stroked"; preset = "stroked"; themeType = "stroke"; theme = "yellow"; backgroundTheme = $null; strokeTheme = "yellow"; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "stroked-blue"; label = "Stroked Blue"; group = "stroked"; preset = "stroked"; themeType = "stroke"; theme = "blue"; backgroundTheme = $null; strokeTheme = "blue"; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "stroked-pink"; label = "Stroked Pink"; group = "stroked"; preset = "stroked"; themeType = "stroke"; theme = "pink"; backgroundTheme = $null; strokeTheme = "pink"; highlightTheme = $null; karaoke = $false; orientation = "landscape" },
    [pscustomobject]@{ id = "stroked-green"; label = "Stroked Green"; group = "stroked"; preset = "stroked"; themeType = "stroke"; theme = "green"; backgroundTheme = $null; strokeTheme = "green"; highlightTheme = $null; karaoke = $false; orientation = "landscape" },

    [pscustomobject]@{ id = "shorts-yellow"; label = "Shorts Yellow"; group = "shorts"; preset = "shorts"; themeType = "highlight"; theme = "yellow"; backgroundTheme = $null; strokeTheme = $null; highlightTheme = "yellow"; karaoke = $true; orientation = "shorts" },
    [pscustomobject]@{ id = "shorts-green"; label = "Shorts Green"; group = "shorts"; preset = "shorts"; themeType = "highlight"; theme = "green"; backgroundTheme = $null; strokeTheme = $null; highlightTheme = "green"; karaoke = $true; orientation = "shorts" },
    [pscustomobject]@{ id = "shorts-orange"; label = "Shorts Orange"; group = "shorts"; preset = "shorts"; themeType = "highlight"; theme = "orange"; backgroundTheme = $null; strokeTheme = $null; highlightTheme = "orange"; karaoke = $true; orientation = "shorts" },
    [pscustomobject]@{ id = "shorts-purple"; label = "Shorts Purple"; group = "shorts"; preset = "shorts"; themeType = "highlight"; theme = "purple"; backgroundTheme = $null; strokeTheme = $null; highlightTheme = "purple"; karaoke = $true; orientation = "shorts" },
    [pscustomobject]@{ id = "shorts-blue"; label = "Shorts Blue"; group = "shorts"; preset = "shorts"; themeType = "highlight"; theme = "blue"; backgroundTheme = $null; strokeTheme = $null; highlightTheme = "blue"; karaoke = $true; orientation = "shorts" },
    [pscustomobject]@{ id = "shorts-pink"; label = "Shorts Pink"; group = "shorts"; preset = "shorts"; themeType = "highlight"; theme = "pink"; backgroundTheme = $null; strokeTheme = $null; highlightTheme = "pink"; karaoke = $true; orientation = "shorts" }
)

function Write-GenerationLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $generationLog -Value $line -Encoding UTF8
    Write-Host $line
}

function Invoke-LoggedCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogPath
    )

    $commandText = "$FilePath " + (($Arguments | ForEach-Object {
        if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
    }) -join " ")
    Add-Content -LiteralPath $LogPath -Value "COMMAND: $commandText" -Encoding UTF8
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $output | Add-Content -LiteralPath $LogPath -Encoding UTF8
    Add-Content -LiteralPath $LogPath -Value "EXIT CODE: $exitCode`r`n" -Encoding UTF8
    if ($exitCode -ne 0) {
        throw "Command failed with exit code ${exitCode}: $commandText"
    }
}

function Get-PortablePath {
    param([string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $rootPrefix = $repoRoot.TrimEnd("\") + "\"
    if ($fullPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $fullPath.Substring($rootPrefix.Length).Replace("\", "/")
    }
    return $fullPath.Replace("\", "/")
}

foreach ($requiredPath in @($generator, $captionsFile, $LandscapeVideo, $ShortsVideo)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Missing required preview input: $requiredPath"
    }
}

New-Item -ItemType Directory -Force -Path $OutputDirectory, $ReviewDirectory, $logsDirectory | Out-Null

$expectedOutputFiles = foreach ($candidate in $candidates) {
    Join-Path $OutputDirectory "preview-$($candidate.id).png"
    Join-Path $OutputDirectory "props-$($candidate.id).json"
}
$expectedOutputFiles += Join-Path $OutputDirectory "preview-manifest.json"

$existingOutputFiles = $expectedOutputFiles | Where-Object { Test-Path -LiteralPath $_ }
if ($existingOutputFiles -and -not $Force) {
    throw "Preview output already exists. Re-run with -Force to replace the 25 expected previews and manifest."
}

if ($Force) {
    if (Test-Path -LiteralPath $OutputDirectory) {
        Get-ChildItem -LiteralPath $OutputDirectory -File | Where-Object {
            $_.Name -eq "preview-manifest.json" -or
            $_.Name -like "preview-*.png" -or
            $_.Name -like "props-*.json"
        } | Remove-Item -Force
    }
    foreach ($path in @($projectsDirectory, $snapshotsDirectory)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }
    foreach ($path in @($generationLog, $hyperframesLog)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
        }
    }
}

New-Item -ItemType Directory -Force -Path $projectsDirectory, $interactionStatesDirectory, $snapshotsDirectory | Out-Null
Set-Content -LiteralPath $generationLog -Value "Phase 4 style preview generation" -Encoding UTF8
Set-Content -LiteralPath $hyperframesLog -Value "HyperFrames checks for all 25 preview candidates" -Encoding UTF8

Write-GenerationLog "Generating $($candidates.Count) previews with snapshotTime=$snapshotTime."
Write-GenerationLog "Check strategy: HyperFrames lint/runtime/layout/motion check for every candidate before snapshot; contrast is disabled because color-theme previews include intentional palette colors that are not WCAG-gated body text."

$manifestItems = @()

foreach ($candidate in $candidates) {
    $video = if ($candidate.orientation -eq "shorts") { $ShortsVideo } else { $LandscapeVideo }
    $projectDirectory = Join-Path $projectsDirectory $candidate.id
    $interactionState = Join-Path $interactionStatesDirectory "$($candidate.id).json"
    $snapshotDirectory = Join-Path $snapshotsDirectory $candidate.id
    $candidateLog = Join-Path $logsDirectory "$($candidate.id).txt"

    Write-GenerationLog "[$($candidate.id)] generate project"
    Invoke-LoggedCommand -FilePath "node" -Arguments @(
        $interactionScript,
        "start",
        "--state", $interactionState,
        "--source", $video,
        "--captions", $captionsFile,
        "--no-open", "true",
        "--force", "true"
    ) -LogPath $candidateLog
    Invoke-LoggedCommand -FilePath "node" -Arguments @(
        $interactionScript,
        "select",
        "--state", $interactionState,
        "--response", $candidate.id
    ) -LogPath $candidateLog
    $generateArgs = @(
        $generator,
        "--video", $video,
        "--captions", $captionsFile,
        "--out", $projectDirectory,
        "--interaction-state", $interactionState,
        "--mode", "preview"
    )
    Set-Content -LiteralPath $candidateLog -Value "Preview candidate: $($candidate.id)" -Encoding UTF8
    Invoke-LoggedCommand -FilePath "node" -Arguments $generateArgs -LogPath $candidateLog

    Write-GenerationLog "[$($candidate.id)] hyperframes check"
    Invoke-LoggedCommand -FilePath "npx.cmd" -Arguments @(
        "hyperframes", "check", $projectDirectory,
        "--at", $snapshotTime.ToString([System.Globalization.CultureInfo]::InvariantCulture),
        "--timeout", "10000",
        "--no-contrast"
    ) -LogPath $candidateLog
    Add-Content -LiteralPath $hyperframesLog -Value (Get-Content -LiteralPath $candidateLog -Raw) -Encoding UTF8

    Write-GenerationLog "[$($candidate.id)] hyperframes snapshot"
    $snapshotArguments = @(
        "hyperframes", "snapshot", $projectDirectory,
        "--at", $snapshotTime.ToString([System.Globalization.CultureInfo]::InvariantCulture),
        "--no-end",
        "--timeout", "60000",
        "--describe", "false",
        "--output", $snapshotDirectory
    )
    try {
        Invoke-LoggedCommand -FilePath "npx.cmd" -Arguments $snapshotArguments -LogPath $candidateLog
    }
    catch {
        Write-GenerationLog "[$($candidate.id)] snapshot failed once; retrying."
        if (Test-Path -LiteralPath $snapshotDirectory) {
            Remove-Item -LiteralPath $snapshotDirectory -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path $snapshotDirectory | Out-Null
        Invoke-LoggedCommand -FilePath "npx.cmd" -Arguments $snapshotArguments -LogPath $candidateLog
    }

    $snapshot = @(Get-ChildItem -LiteralPath $snapshotDirectory -Filter "frame-*.png" -File)
    if ($snapshot.Count -ne 1) {
        throw "Expected exactly one snapshot PNG for $($candidate.id), found $($snapshot.Count)."
    }

    $imageName = "preview-$($candidate.id).png"
    $propsName = "props-$($candidate.id).json"
    Copy-Item -LiteralPath $snapshot[0].FullName -Destination (Join-Path $OutputDirectory $imageName) -Force

    $projectMeta = Get-Content -LiteralPath (Join-Path $projectDirectory "project-meta.json") -Raw | ConvertFrom-Json
    $props = [ordered]@{
        id = $candidate.id
        preset = $candidate.preset
        backgroundTheme = $candidate.backgroundTheme
        strokeTheme = $candidate.strokeTheme
        highlightTheme = $candidate.highlightTheme
        karaoke = [bool]$candidate.karaoke
        mode = "preview"
        width = [int]$projectMeta.width
        height = [int]$projectMeta.height
        fps = [double]$projectMeta.fps
        snapshotTime = $snapshotTime
        sourceVideo = Get-PortablePath $video
        captionsFile = Get-PortablePath $captionsFile
        resolvedStyle = $projectMeta.resolvedStyle
    }
    $props | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath (Join-Path $OutputDirectory $propsName) -Encoding UTF8

    $manifestItems += [pscustomobject][ordered]@{
        id = $candidate.id
        label = $candidate.label
        preset = $candidate.preset
        themeType = $candidate.themeType
        theme = $candidate.theme
        karaoke = [bool]$candidate.karaoke
        orientation = $candidate.orientation
        aspectRatio = if ($candidate.orientation -eq "shorts") { "9:16" } else { "16:9" }
        width = [int]$projectMeta.width
        height = [int]$projectMeta.height
        image = $imageName
        props = $propsName
    }
}

$groupOrder = @("core", "pill", "boxed", "stroked", "shorts")
$groups = foreach ($groupName in $groupOrder) {
    $groupIds = @($candidates | Where-Object { $_.group -eq $groupName } | ForEach-Object { $_.id })
    [pscustomobject][ordered]@{
        id = $groupName
        items = @($manifestItems | Where-Object { $groupIds -contains $_.id })
    }
}

$manifest = [ordered]@{
    schemaVersion = 1
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    generator = "scripts/render_style_previews.ps1"
    total = $manifestItems.Count
    groups = @($groups)
}
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $OutputDirectory "preview-manifest.json") -Encoding UTF8

$pngFiles = @(Get-ChildItem -LiteralPath $OutputDirectory -Filter "preview-*.png" -File)
$propsFiles = @(Get-ChildItem -LiteralPath $OutputDirectory -Filter "props-*.json" -File)
if ($pngFiles.Count -ne 25) {
    throw "Expected 25 preview PNG files, found $($pngFiles.Count)."
}
if ($propsFiles.Count -ne 25) {
    throw "Expected 25 props JSON files, found $($propsFiles.Count)."
}
if (-not (Test-Path -LiteralPath (Join-Path $OutputDirectory "preview-manifest.json"))) {
    throw "preview-manifest.json was not created."
}
foreach ($path in $expectedOutputFiles) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing expected preview output: $path"
    }
}

Write-GenerationLog "Completed: 25 PNG, 25 props JSON, 1 manifest."
Write-Host "[caption-previews] output: $OutputDirectory"
Write-Host "[caption-previews] review: $ReviewDirectory"
