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
    "scripts\caption_spatial_context.py",
    "scripts\check_caption_spatial_context.py",
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
$projectRegistration = Get-Section $skill "Project Registration"
$selfCheck = Get-Section $skill "Self Check"

Assert-CommandOptions $canonical 'caption_interaction.mjs" start' @('--review-dir $Review') "start"
Assert-CommandOptions $canonical 'caption_spatial_context.py" align' @(
    '--project-root $ProjectRoot',
    '--plan $Plan',
    '--out-plan $Plan'
) "spatial align"
Assert-CommandOptions $canonical 'caption_spatial_context.py" build' @(
    '--project-root $ProjectRoot',
    '--plan $Plan',
    '--out $SpatialContext'
) "spatial build"
Assert-CommandOptions $canonical 'caption_spatial_context.py" validate' @(
    '--project-root $ProjectRoot',
    '--plan $Plan',
    '--context $SpatialContext'
) "spatial validate"
Assert-CommandOptions $canonical 'caption_spatial_context.py" attach' @(
    '--project-root $ProjectRoot',
    '--plan $Plan',
    '--context $SpatialContext'
) "spatial attach"
Assert-CommandOptions $canonical 'build_caption_review.py"' @('--interaction-state $Receipt') "build_caption_review"
Assert-CommandOptions $canonical 'caption_interaction.mjs" preview-ready' @(
    '--review-page "$Review\captions-review.html"',
    '--timeline "$Work\timeline.json"'
) "preview-ready"

$standardSpatialBlocks = @(
    [regex]::Matches($canonical, '(?ms)^```powershell\s*\r?\n(?<body>.*?)^```\s*$') |
        ForEach-Object { $_.Groups["body"].Value } |
        Where-Object { $_.Contains('$StandardSpatialEvidenceDocument') }
)
if ($standardSpatialBlocks.Count -ne 1) {
    Fail-Contract "Standard + spatial review must have exactly one dynamic evidence command block"
}
$standardSpatialBlock = $standardSpatialBlocks[0] -replace '\s+', ' '
foreach ($marker in @(
    'captions-evidence.json',
    '$StandardSpatialEvidenceDocument.review_samples',
    'caption_interaction.mjs" preview-ready',
    '--evidence $Evidence',
    '--evidence-document "$Review\captions-evidence.json"'
)) {
    if (-not $standardSpatialBlock.Contains($marker)) {
        Fail-Contract "Standard + spatial dynamic evidence command is missing $marker"
    }
}
if ($standardSpatialBlock.Contains('--comparison-evidence')) {
    Fail-Contract "Standard + spatial dynamic evidence must not bind comparison evidence"
}

$expressiveEvidenceBlocks = @(
    [regex]::Matches($canonical, '(?ms)^```powershell\s*\r?\n(?<body>.*?)^```\s*$') |
        ForEach-Object { $_.Groups["body"].Value } |
        Where-Object { $_.Contains('$EvidenceDocument =') }
)
if ($expressiveEvidenceBlocks.Count -ne 1) {
    Fail-Contract "Expressive review must have exactly one representative evidence command block"
}
$expressiveEvidenceBlock = $expressiveEvidenceBlocks[0] -replace '\s+', ' '
foreach ($marker in @(
    '$EvidenceDocument.review_samples',
    '--evidence $Evidence',
    '--evidence-document "$Review\captions-evidence.json"',
    '--comparison-evidence $ComparisonEvidence'
)) {
    if (-not $expressiveEvidenceBlock.Contains($marker)) {
        Fail-Contract "Expressive representative evidence command is missing $marker"
    }
}

$presentationStart = $canonical.IndexOf('Before building the caption plan')
$planStart = $canonical.IndexOf('Build program-time cues and the review SRT:')
$styleStart = $canonical.IndexOf('`start` prints the authoritative')
$evidenceStart = $canonical.IndexOf('The builder writes `captions-review.html`')
$renderStart = $canonical.IndexOf('Generate the approved overlay project.')
if ($presentationStart -lt 0 -or $planStart -le $presentationStart -or $styleStart -le $planStart -or
    $evidenceStart -le $styleStart -or $renderStart -le $evidenceStart) {
    Fail-Contract "cannot locate distinct presentation, plan, style, evidence, and render workflow segments"
}
$presentationFlow = $canonical.Substring($presentationStart, $planStart - $presentationStart)
$styleFlow = $canonical.Substring($styleStart, $evidenceStart - $styleStart)
$evidenceFlow = $canonical.Substring($evidenceStart, $renderStart - $evidenceStart)

$presentationStopCount = [regex]::Matches($presentationFlow, 'Present\s*\+\s*STOP').Count
if ($presentationStopCount -ne 1) {
    Fail-Contract "presentation mode flow must contain exactly one Present + STOP gate; found $presentationStopCount"
}
Assert-NativeOpenFlow $styleFlow 'captions-style-review-<UUID>.html' '$StyleReviewPage' "style review"
Assert-NativeOpenFlow $evidenceFlow 'captions-review.html' '$EvidenceReviewPage' "evidence review"
if ([regex]::Matches($canonical, 'Present\s*\+\s*STOP').Count -ne 3) {
    Fail-Contract "canonical workflow must contain exactly three distinct Present + STOP gates"
}

Assert-SectionRegex $presentationFlow '(?s)current conversation language.*`Standard`.*`Expressive`.*Reply with Standard, Expressive, or "Use the default \(Standard\)\."' "presentation flow must localize the runtime question while preserving the Standard and Expressive identifiers and English prompt ending"
Assert-SectionRegex $styleFlow '(?s)authoritative.*captions-style-review-<UUID>\.html.*captions-style-review\.html.*non-authoritative.*latest convenience alias' "style flow must distinguish the authoritative UUID page from the latest alias"
Assert-SectionRegex $styleFlow '(?s)Caption style review.*Decision:\s*select.*Choice:.*--response\s+\$StyleResponse' "style flow must preserve and pass the structured human summary"
Assert-SectionRegex $styleFlow '(?s)--decision-mode\s+agent.*--delegation-note.*--no-open\s+true.*agent-select.*--rationale' "style flow must keep delegated Agent selection separate"
Assert-SectionRegex $evidenceFlow '(?s)Caption preview review.*Decision:\s*approve.*Evidence:\s*early, middle, late, no-caption.*Decision:\s*revise.*--response\s+\$PreviewResponse' "evidence flow must preserve approve and revise summaries"
Assert-SectionRegex $evidenceFlow '(?ms)^```text\s*\r?\nCaption preview review\s*\r?\nReview: <UUID from the opened page>\s*\r?\nDecision: approve\s*\r?\nEvidence: early, middle, late, no-caption\s*\r?\n```' "Standard preview approval summary must remain unchanged"
Assert-SectionRegex $evidenceFlow '(?s)Evidence:\s*expressive-layout-beats\s*Karaoke:\s*on\|off' "Expressive preview approval must include the strict Karaoke on|off field"
Assert-SectionRegex $evidenceFlow '(?s)Evidence:\s*composite-aware.*Karaoke:\s*on\|off' "composite-aware Expressive approval must preserve the strict Karaoke on|off field"
Assert-SectionRegex $evidenceFlow '(?s)same `captions-review\.html` page.*agent-confirm.*--state\s+\$Receipt.*--karaoke\s+(?:on|off).*--rationale' "Expressive Agent confirmation must bind an explicit Karaoke choice to inspected evidence"
Assert-SectionRegex $canonical '(?s)\$SpatialContext\s*=.*caption-spatial-context\.json.*\$SpatialArgs.*--spatial-context.*\$SpatialReviewArgs.*--project-root' "canonical workflow must define optional spatial arguments for interaction, rendering, and review"
Assert-SectionRegex $skill '(?s)`panel-bottom`.*`unsplittable_word_boundary`.*lower-center' "skill must document the bounded lower-center boundary fallback"
Assert-SectionRegex $skill '(?s)canonical `level: hero`.*`1\.5x`.*Legacy `level: strong`.*input alias' "skill must expose one canonical Hero 1.5x level and retain strong only as compatibility input"
Assert-SectionRegex $skill '(?s)`captions-evidence\.json\.samples`.*dense machine evidence.*`review_samples`.*at most one representative.*`Hero 1\.5x`' "skill must separate exhaustive machine evidence from representative human evidence"
Assert-SectionRegex $canonical '(?s)Human-visible.*`review\.representative_evidence`.*`review\.evidence`.*shared\s*delivery compiler.*one.*machine sample per layout beat.*`no-caption`.*does not add.*human review.*`review\.machine_evidence_document`' "formal overlay generation must preserve the representative/delivery evidence compatibility boundary"
Assert-SectionRegex $decisionModes '(?s)source,\s*plan,\s*timeline,\s*style,\s*override,\s*project metadata,\s*review page,\s*or evidence.*invalidates approval' "Decision Modes must state complete approval invalidation"
Assert-SectionRegex $compatibility 'Standalone exact ID and skip responses are legacy compatibility only\.' "legacy ID/skip behavior must remain in Compatibility"
Assert-SectionRegex $skill '(?s)active B-roll.*based_on.*revision' "Project Registration must bind captions to the active B-roll revision"
Assert-SectionRegex $projectRegistration '(?s)"depends_on":\s*\[[^\]]*"b-roll"[^\]]*\].*"based_on":\s*\{[^}]*"b-roll":\s*4' "Project Registration JSON example must include the bound B-roll dependency and revision"
Assert-SectionRegex $projectRegistration '(?s)no spatial context.*omit.*`b-roll`.*`depends_on`.*`based_on`' "Project Registration must say to omit B-roll dependency fields without spatial context"
Assert-SectionRegex $selfCheck 'check_caption_spatial_context\.py' "Self Check must run the spatial context regression"
Assert-SectionRegex $selfCheck 'check_caption_review\.py' "Self Check must run the review regression"
Assert-SectionRegex $selfCheck 'check_caption_interaction\.mjs' "Self Check must run the interaction regression"
Assert-SectionRegex $selfCheck '(?s)HTML generation alone is not success.*Inspect actual pixels and the final delivery' "Self Check must require pixel and delivery inspection"

Write-Host "Structure check passed: $skillRoot"
