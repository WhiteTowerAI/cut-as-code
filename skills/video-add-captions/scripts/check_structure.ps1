$ErrorActionPreference = "Stop"

$skillRoot = Split-Path -Parent $PSScriptRoot
$required = @(
    "SKILL.md",
    "examples\index.html",
    "scripts\caption-styles.json",
    "scripts\caption_style_config.mjs",
    "scripts\caption_interaction_state.mjs",
    "scripts\caption_interaction.mjs",
    "scripts\check_caption_style_config.mjs",
    "scripts\check_project_protocol.py",
    "scripts\build_caption_review.py",
    "scripts\generate_caption_project.mjs",
    "scripts\composite_caption_overlay.ps1",
    "public\gsap.min.js",
    "public\fonts\CalSans-Regular.ttf"
)

$missing = foreach ($relativePath in $required) {
    $fullPath = Join-Path $skillRoot $relativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        $relativePath
    }
}

if ($missing) {
    $missing | ForEach-Object { Write-Error "Missing required file: $_" }
    exit 1
}

$html = Get-Content -LiteralPath (Join-Path $skillRoot "examples\index.html") -Raw
$requiredMarkers = @(
    'data-composition-id="video-add-captions-preview"',
    'data-duration="9"',
    'data-fps="30"',
    'window.__timelines["video-add-captions-preview"]'
)

foreach ($marker in $requiredMarkers) {
    if (-not $html.Contains($marker)) {
        Write-Error "Missing HyperFrames marker: $marker"
        exit 1
    }
}

if ($html -match '<script[^>]+src="https?://') {
    Write-Error "Caption example must not load remote runtime scripts"
    exit 1
}

Write-Host "Structure check passed: $skillRoot"
