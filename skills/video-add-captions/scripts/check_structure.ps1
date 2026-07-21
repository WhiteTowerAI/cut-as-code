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

$skill = Get-Content -LiteralPath (Join-Path $skillRoot "SKILL.md") -Raw

function Fail-Contract([string]$message) {
    Write-Error "Caption workflow contract: $message"
    exit 1
}

function Get-Section([string]$text, [string]$heading) {
    $pattern = "(?ms)^## $([regex]::Escape($heading))\s*\r?\n(?<body>.*?)(?=^## |\z)"
    $match = [regex]::Match($text, $pattern)
    if (-not $match.Success) {
        Fail-Contract "missing section: $heading"
    }
    return $match.Groups["body"].Value
}

function Assert-SectionRegex([string]$text, [string]$pattern, [string]$diagnostic) {
    if ($text -notmatch $pattern) {
        Fail-Contract $diagnostic
    }
}

function Assert-CommandOptions(
    [string]$text,
    [string]$commandMarker,
    [string[]]$requiredOptions,
    [string]$label
) {
    $blocks = @(
        [regex]::Matches($text, '(?ms)^```[^\r\n]*\r?\n(?<body>.*?)^```\s*$') |
            ForEach-Object { $_.Groups["body"].Value } |
            Where-Object { $_.Contains($commandMarker) }
    )
    if ($blocks.Count -eq 0) {
        Fail-Contract "missing $label command block"
    }
    foreach ($block in $blocks) {
        $normalized = $block -replace '\s+', ' '
        foreach ($option in $requiredOptions) {
            if (-not $normalized.Contains($option)) {
                Fail-Contract "$label command is missing $option"
            }
        }
    }
}

function Assert-NativeOpenFlow(
    [string]$text,
    [string]$pageMarker,
    [string]$variable,
    [string]$label
) {
    $normalized = $text -replace '\s+', ' '
    foreach ($marker in @(
        $pageMarker,
        "Start-Process -FilePath (Resolve-Path $variable)",
        "open `"$variable`"",
        "xdg-open `"$variable`""
    )) {
        if (-not $normalized.Contains($marker)) {
            Fail-Contract "$label flow is missing $marker"
        }
    }
    $stopCount = [regex]::Matches($text, 'Present\s*\+\s*STOP').Count
    if ($stopCount -ne 1) {
        Fail-Contract "$label flow must contain exactly one Present + STOP gate; found $stopCount"
    }
}

$canonical = Get-Section $skill "Canonical Workflow"
$decisionModes = Get-Section $skill "Decision Modes"
$compatibility = Get-Section $skill "Compatibility"
$selfCheck = Get-Section $skill "Self Check"

Assert-CommandOptions $canonical 'caption_interaction.mjs" start' @('--review-dir $Review') "start"
Assert-CommandOptions $canonical 'build_caption_review.py"' @('--interaction-state $Receipt') "build_caption_review"
Assert-CommandOptions $canonical 'caption_interaction.mjs" preview-ready' @(
    '--review-page "$Review\captions-review.html"',
    '--timeline "$Work\timeline.json"'
) "preview-ready"

$styleStart = $canonical.IndexOf('`start` prints the authoritative')
$evidenceStart = $canonical.IndexOf('The builder writes `captions-review.html`')
$renderStart = $canonical.IndexOf('Generate the approved overlay project.')
if ($styleStart -lt 0 -or $evidenceStart -le $styleStart -or $renderStart -le $evidenceStart) {
    Fail-Contract "cannot locate distinct style, evidence, and render workflow segments"
}
$styleFlow = $canonical.Substring($styleStart, $evidenceStart - $styleStart)
$evidenceFlow = $canonical.Substring($evidenceStart, $renderStart - $evidenceStart)

Assert-NativeOpenFlow $styleFlow 'captions-style-review-<UUID>.html' '$StyleReviewPage' "style review"
Assert-NativeOpenFlow $evidenceFlow 'captions-review.html' '$EvidenceReviewPage' "evidence review"
if ([regex]::Matches($canonical, 'Present\s*\+\s*STOP').Count -ne 2) {
    Fail-Contract "canonical workflow must contain exactly two distinct Present + STOP gates"
}

Assert-SectionRegex $styleFlow '(?s)authoritative.*captions-style-review-<UUID>\.html.*captions-style-review\.html.*non-authoritative.*latest convenience alias' "style flow must distinguish the authoritative UUID page from the latest alias"
Assert-SectionRegex $styleFlow '(?s)Caption style review.*Decision:\s*select.*Choice:.*--response\s+\$StyleResponse' "style flow must preserve and pass the structured human summary"
Assert-SectionRegex $styleFlow '(?s)--decision-mode\s+agent.*--delegation-note.*--no-open\s+true.*agent-select.*--rationale' "style flow must keep delegated Agent selection separate"
Assert-SectionRegex $evidenceFlow '(?s)Caption preview review.*Decision:\s*approve.*Evidence:\s*early, middle, late, no-caption.*Decision:\s*revise.*--response\s+\$PreviewResponse' "evidence flow must preserve approve and revise summaries"
Assert-SectionRegex $evidenceFlow '(?s)same `captions-review\.html` page.*agent-confirm.*--rationale' "evidence flow must keep Agent confirmation bound to inspected evidence"
Assert-SectionRegex $decisionModes '(?s)source,\s*plan,\s*timeline,\s*style,\s*override,\s*project metadata,\s*review page,\s*or evidence.*invalidates approval' "Decision Modes must state complete approval invalidation"
Assert-SectionRegex $compatibility 'Standalone exact ID and skip responses are legacy compatibility only\.' "legacy ID/skip behavior must remain in Compatibility"
Assert-SectionRegex $selfCheck '(?s)HTML generation alone is not success.*Inspect actual pixels and the final delivery' "Self Check must require pixel and delivery inspection"

Write-Host "Structure check passed: $skillRoot"
