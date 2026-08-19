---
name: video-add-captions
description: >
  Add word-timed captions to an Open Recut program. Use this skill to map the
  canonical transcript through timeline.json, review a maintained style on
  source-backed pixels, render a local transparent HyperFrames PNG sequence,
  and register it as an overlay contribution for the shared delivery render.
---

# Video Add Captions

## Dependencies

`/video-understand` is a prerequisite. Run it first so captions use the validated
word-level transcript and canonical timeline.
Before starting, verify that it is installed. If it is not, warn the user that
this prerequisite is missing and stop before processing media.

Require `ffmpeg`/`ffprobe` on PATH, Python with `Pillow`, and Node.js >= 22 (for the `.mjs` scripts and `npx hyperframes`, fetched on demand). `hyperframes render`/`snapshot` drives a headless Chrome — it manages its own `chrome-headless-shell`, and falls back to a system Chrome (set `CHROME` to override) when the cached one is unusable. Check these before processing media.

## Scope

This skill owns caption grouping, style selection, review, and the transparent
caption track. It does not transcribe, cut, retime, grade, reframe, or choose the
delivery audio policy.

Run captions before content cards and graphic motion whenever either is selected.
The approved caption layout establishes a reserved subtitle region that both later
operations must keep clear. This relative order also applies when only one pair is active.

Use `video-understand` first. If a cut exists, caption the active program
timeline; do not treat source transcript seconds as program seconds.

## Protocol Inputs

Required:

- `work/project.json`
- `work/understand/transcript.json`, with word-level source timestamps
- `work/understand/media.json`
- `work/timeline.json`
- the source video named by `work/project.json`

The timeline is the only source-to-program mapping. All ranges are half-open
`[start_s, end_s)`. `scripts/build_captions.py` uses the shared
`projectlib.map_transcript_to_timeline`; words in dropped source ranges disappear,
retained words move to program time, and cues always break at clip boundaries.

## Durable Outputs

```text
work/captions/
|-- captions-plan.json
|-- caption-spatial-context.json (only for eligible B-roll composites)
`-- caption-interaction.json
work/cache/captions/
|-- preview-project/
|-- preview-snapshots/
|-- overlay-project/
`-- overlay-frames/frame_000001.png ...
review/05-captions/
|-- captions.srt
|-- captions-style-review-<UUID>.html
|-- captions-style-review.html
|-- captions-review.html
|-- preview-early.png
|-- preview-middle.png
|-- preview-late.png
|-- preview-no-caption.png
|-- captions-evidence.json
`-- captions-summary.md
```

Generated HTML, copied runtime files, extracted source frames, and overlay frames
are cache. The plan, optional spatial context, SRT, decision receipt, and review
evidence are durable.

## Caption Plan

`work/captions/captions-plan.json` is the canonical caption plan, targets `overlay`, and uses
program time. It records:

- `timeline_id`, `program_duration_s`, and the source transcript path;
- cue grouping settings;
- approved style, decision mode, rationale, gallery choice, and complete resolved style;
- source-backed review evidence and approval actor;
- cues with compatibility fields `start`, `end`, `text`, `lines`, and `words`;
- `program_range` and `source_ranges` on every cue;
- program/source ranges and `clip_id` on every mapped word;
- a local renderer recipe with exact rational FPS and hashed runtime assets.

The generator also accepts the old top-level cue array. That is a standalone
compatibility adapter only; it cannot express timeline provenance or regenerate an
approved protocol contribution.

Standard is the default presentation mode. Standard plans do not need a
`presentation` field and must not be migrated merely to add one. Expressive is an
explicit presentation mode, not a preset: request it with
`--presentation-mode expressive`. The build step then adds stable cue IDs, default
word `semantic_role` values, and a draft `presentation` planning shell; it does not
guess layout variants.

Expressive supports only `bottom-standard` and `center-emphasis`. Read
`reference/caption-rules.md` before filling the shell. The
existing renderer consumes only completed `presentation.layout_beats`; it does not
infer positions or change layout inside a beat.

Expressive cues may also define one contiguous phrase-level `hero_line`.
Use canonical `level: hero`; it renders the phrase gold on its own line at
`1.5x`. Legacy `level: strong` remains accepted as an input alias and renders
identically, but new Agent-authored plans must not emit it. The maintained word roles `keyword`, `number`, and
`contrast` each use `1.22x`; `normal` remains `1.0x`. These treatments are
orthogonal to presets and do not create new style IDs. Read
`reference/caption-rules.md` for the schema, overflow policy, and Karaoke rules.

When an active, review-approved B-roll operation contains approved or verified
speaker-inset composites, captions may derive `caption-spatial-context.json` from
the frozen upstream plan, evidence, normalized composites, and explicit subshot
`display_mode`. This does not modify or reselect the B-roll layout. It aligns cue
boundaries before Expressive planning and resolves only the maintained
`preset-bottom`, `frame-center`, `panel-center`, and boundary-only `panel-bottom`
placements. `panel-bottom` is allowed only for an `unsplittable_word_boundary`
adjacent to a lower-center focused panel; it centers the stable cue inside the
reserved strip below the structured speaker rect. Such a cue is checked against
every visual context it intersects, not only the context containing the word
midpoint. Without this context, all existing Standard and Expressive placement
behavior remains unchanged.

## Styles

Maintained presets are `clean`, `minimal`, `social-bold`, `pill`, `boxed`,
`stroked`, and `shorts`. Gallery combination IDs add maintained themes, for
example `pill-yellow`, `stroked-blue`, and `shorts-green`. Karaoke is an option,
not a separate preset.

Default delegated choice: `clean`, Karaoke off. Choose a more expressive preset
only when the destination or footage justifies it. Store job-specific changes in
an overrides JSON; do not edit the generator for ordinary style feedback.

Expressive supports both `semantic-only` (Karaoke off) and
`semantic-plus-karaoke` (Karaoke on). Semantic emphasis persists for the full cue
in both configurations. In coexistence mode, semantic emphasis and the active
Karaoke word use `style.wordHighlight.activeColor` as their foreground color in
every highlight mode; a background highlight remains an additional effect. The
effective scale is `max(semantic scale, karaoke active scale)`, never their
product. Expressive never renders an underline, including for the compatible
`contrast` semantic role.

The existing review contract continues to use semantic-only as the primary
Expressive evidence and binds semantic-plus-karaoke separately. The compatibility
payload field remains named `experimental_comparison`; do not rename it without an
approval-protocol migration.

Read:

- `reference/caption-rules.md` before changing grouping limits;
- `reference/caption-style-themes.md` for style vocabulary;
- `reference/caption-feedback-mapping.md` for override mapping.

## Decision Modes

Two honest modes share the same hash-bound state machine:

- `human`: pass the exact copied gallery summary to `select`, show all real
  preview evidence, and pass the exact copied approval or revision summary to
  `confirm` or `adjust`. Review-page-bound commands do not accept bare approval
  phrases.
- `agent`: use only when the user explicitly delegates caption decisions. Start
  with a non-empty delegation note, then use `agent-select` and `agent-confirm`
  with non-empty rationales.

Human commands fail in agent mode and agent commands fail in human mode. Standard
without spatial context requires the four maintained source-backed images;
Expressive and composite-aware reviews use their dynamic evidence contracts. A
change to the source, plan, timeline, style, override, project metadata,
review page, or evidence invalidates approval; spatial context, upstream B-roll revision,
or bound-composite changes do the same. Rebuild the affected artifacts and review
them again.

## Canonical Workflow

Run from the repository root. Set project paths:

```powershell
$RepoRoot = (Resolve-Path ".").Path
$SkillRoot = Join-Path $RepoRoot "skills\video-add-captions"
$ProjectRoot = (Resolve-Path "<project-root>").Path
$Work = Join-Path $ProjectRoot "work"
$SourceVideo = "<absolute path from work/project.json>"
$Plan = Join-Path $Work "captions\captions-plan.json"
$SpatialContext = Join-Path $Work "captions\caption-spatial-context.json"
$SpatialArgs = @()
$SpatialReviewArgs = @()
$Receipt = Join-Path $Work "captions\caption-interaction.json"
$Review = Join-Path $ProjectRoot "review\05-captions"
$Cache = Join-Path $Work "cache\captions"
$PreviewProject = Join-Path $Cache "preview-project"
$ComparisonProject = Join-Path $Cache "preview-project-expressive-karaoke"
$OverlayProject = Join-Path $Cache "overlay-project"
$OverlayFrames = Join-Path $Cache "overlay-frames"
New-Item -ItemType Directory -Force -Path (Split-Path $Plan),$Review,$Cache | Out-Null
```

Before building the caption plan, ask the user to choose the presentation mode
unless the current request already explicitly selects one. Render the question in
the user's current conversation language while keeping the `Standard` and
`Expressive` identifiers untranslated. Keep the English source prompt below in
this file, present the localized choice in the current session, then
**Present + STOP**:

```text
Choose the caption presentation mode:

1. Standard: Uses stable conventional placement and suits most content.
2. Expressive: Switches between bottom and center placement based on meaning and emphasizes keywords and numbers.

Reply with Standard, Expressive, or "Use the default (Standard)."
```

Do not run `build_captions.py` until the user responds. If the user explicitly
delegates the choice in any wording, select Standard. State that Standard was
selected as the compatibility-preserving default before building the plan.

Build program-time cues and the review SRT:

```powershell
python "$SkillRoot\scripts\build_captions.py" `
  "$Work\understand\transcript.json" `
  $Plan `
  "$Review\captions.srt" `
  --timeline "$Work\timeline.json" `
  --source-transcript "understand/transcript.json" `
  --max-chars 42 --max-lines 2 --max-dur 6 --gap 0.6
```

After the user selects Standard, the command above produces the unchanged Standard
plan. After the user selects Expressive, run the same command with:

```powershell
  --presentation-mode expressive
```

After draft cue generation, inspect the active B-roll operation and its bound plan
read-only. Enable composite-aware placement only when the operation is active, its
status is `approved` or `verified`, `review.status` is `approved`, the
speaker-inset analysis/agent-input/preview/clearance bindings are complete, and at
least one verified or normalized shot has a maintained composite layout. The
spatial builder uses explicit subshot `display_mode: enabled` for speaker geometry;
`pure_broll` and missing speaker evidence never imply a speaker rectangle.

When eligible, align draft cues to every B-roll visual boundary before filling any
Expressive `layout_beats` or `hero_line`. Alignment splits only at word gaps and
writes back atomically; a boundary inside a word keeps the word whole and records
mandatory review evidence:

```powershell
python "$SkillRoot\scripts\caption_spatial_context.py" align `
  --project-root $ProjectRoot --plan $Plan --out-plan $Plan
```

For an eligible project, prepare the optional arguments used by every later gate:

```powershell
$SpatialArgs = @("--spatial-context", $SpatialContext)
$SpatialReviewArgs = @("--spatial-context", $SpatialContext, "--project-root", $ProjectRoot)
```

When no eligible composite exists, skip all four spatial commands and leave
`$SpatialArgs` and `$SpatialReviewArgs` empty. Do not create or attach an empty
context.

Before starting style selection or generating a preview, the Agent must plan the
entire Expressive program in one pass:

1. Read the transcript, available understanding artifacts, canonical timeline,
   generated caption cues, and any real source-frame evidence needed to justify
   layout changes.
2. Fill all `presentation.layout_beats`, annotate exceptional word
   `semantic_role` values, add at most one contiguous `hero_line` with canonical
   `level: hero` to a cue when
   warranted, write one rationale per beat/hero line, and write the overall
   `presentation.planner.rationale`.
3. Set `presentation.planning_status` to `complete` only after every cue is covered
   exactly once.
4. Validate the completed plan before preview generation:

```powershell
python "$SkillRoot\scripts\build_captions.py" --validate-plan $Plan
```

For an eligible composite, build, validate, and attach the context only after the
final cue IDs and Expressive candidates are complete. This preserves the upstream
layout and binds its current revision and hashes into the caption plan:

```powershell
python "$SkillRoot\scripts\caption_spatial_context.py" build `
  --project-root $ProjectRoot --plan $Plan --out $SpatialContext
```

```powershell
python "$SkillRoot\scripts\caption_spatial_context.py" validate `
  --project-root $ProjectRoot --plan $Plan --context $SpatialContext
```

```powershell
python "$SkillRoot\scripts\caption_spatial_context.py" attach `
  --project-root $ProjectRoot --plan $Plan --context $SpatialContext
```

Do not ask the user to choose a position cue by cue. The user reviews the existing
HTML evidence and corrects only a small number of anomalous beats. Starting the
interaction after planning keeps the existing caption-plan hash binding authoritative.

Start one decision mode. For human mode, publish the maintained offline gallery
into the project review directory without asking the user to locate a file:

```powershell
$StartOutput = node "$SkillRoot\scripts\caption_interaction.mjs" start `
  --state $Receipt --source $SourceVideo --captions $Plan `
  --review-dir $Review --no-open true @SpatialArgs
$StartOutput | Write-Host
```

`start` prints the authoritative `captions-style-review-<UUID>.html` project page
path and the fixed question. `captions-style-review.html` is a non-authoritative
latest convenience alias only. The Agent must take the UUID path printed after
`Caption style review:`, assign that exact path to `$StyleReviewPage`, and open it
with the native command for the host OS:

Windows PowerShell:

```powershell
$StyleReviewPage = "<authoritative UUID page path printed after Caption style review:>"
Start-Process -FilePath (Resolve-Path $StyleReviewPage)
```

macOS:

```bash
open "$StyleReviewPage"
```

Linux:

```bash
xdg-open "$StyleReviewPage"
```

If opening fails, diagnose the command or path and retry it. Do not ask the user
to find the page. Present the opened gallery and the fixed question exactly as
printed, then **Present + STOP**. Do not continue until the human copies the
structured summary from the page. It has this form:

```text
Caption style review
Review: <UUID from the opened page>
Decision: select
Choice: pill-yellow
```

Pass the user's exact summary unchanged to `select --response`. In PowerShell, a
single-quoted here-string preserves the lines safely:

```powershell
$StyleResponse = @'
Caption style review
Review: <UUID from the opened page>
Decision: select
Choice: pill-yellow
'@
node "$SkillRoot\scripts\caption_interaction.mjs" select `
  --state $Receipt --response $StyleResponse
```

The block above shows the structure; use the user's returned block, including
their review UUID and choice. Never infer, normalize, or simulate a human
response.

For explicit delegation, create a separate Agent-mode receipt. Keep the bound
gallery, suppress the script's Windows-only auto-open, open the authoritative UUID
page with the matching native command above, and inspect it before choosing:

```powershell
$StartOutput = node "$SkillRoot\scripts\caption_interaction.mjs" start `
  --state $Receipt --source $SourceVideo --captions $Plan `
  --review-dir $Review `
  --decision-mode agent `
  --delegation-note "User delegated caption style and preview approval." `
  --no-open true @SpatialArgs
$StartOutput | Write-Host

node "$SkillRoot\scripts\caption_interaction.mjs" agent-select `
  --state $Receipt --choice clean `
  --rationale "Conservative readable treatment preserves the talking-head frame."
```

Use `agent-select` only after inspecting the bound gallery and record the real
rationale. Do not manufacture a human summary or use `select` in Agent mode.

Generate a transparent preview composition. The project contains only local GSAP
and font files and preserves rational FPS in `project-meta.json`:

```powershell
node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo --captions $Plan --out $PreviewProject `
  --interaction-state $Receipt --project-root $ProjectRoot --mode preview @SpatialArgs

npx.cmd hyperframes check $PreviewProject --at 1 --timeout 10000 --no-contrast
```

For the primary Expressive review, append `--karaoke false`. Generate the supported
coexistence comparison from the same source, plan, interaction selection, and timing by changing
only the output directory and appending `--karaoke true`:

```powershell
node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo --captions $Plan --out $ComparisonProject `
  --interaction-state $Receipt --project-root $ProjectRoot `
  --karaoke true --mode preview @SpatialArgs
```

For Standard, build mapped early/middle/late/no-caption evidence. This command captures
transparent HyperFrames snapshots, maps each program time through
`timeline.json`, extracts the matching original source frame, and composites the
two with Pillow:

```powershell
python "$SkillRoot\scripts\build_caption_review.py" `
  --source $SourceVideo --timeline "$Work\timeline.json" --plan $Plan `
  --project $PreviewProject --cache "$Cache\review-cache" --out $Review `
  --interaction-state $Receipt @SpatialReviewArgs
```

For Expressive, the same builder emits exhaustive machine samples, a compact
human-review index, and a separately bound semantic-only/Karaoke comparison:

```powershell
python "$SkillRoot\scripts\build_caption_review.py" `
  --source $SourceVideo --timeline "$Work\timeline.json" --plan $Plan `
  --project $PreviewProject --comparison-project $ComparisonProject `
  --cache "$Cache\review-cache" --out $Review --interaction-state $Receipt `
  @SpatialReviewArgs
```

The builder writes `captions-review.html` as the one authoritative page. Standard
without spatial context contains exactly the four maintained evidence labels. For
Expressive or composite-aware review, `captions-evidence.json.samples` retains all
dense machine evidence while `review_samples` contains at most one representative
for each category actually present: `bottom-standard`, `center-emphasis`,
`preset-bottom`, `frame-center`, `panel-center`, and `Hero 1.5x`. One PNG may carry
multiple category labels; absent categories are not fabricated. `no-caption`
remains machine evidence, and the Karaoke comparison remains separate from the
representative count. The
Agent must open that page with the native command for the host OS; for example,
set `$EvidenceReviewPage = "$Review\captions-review.html"` and run one of:

```powershell
Start-Process -FilePath (Resolve-Path $EvidenceReviewPage)
```

```bash
open "$EvidenceReviewPage"
```

```bash
xdg-open "$EvidenceReviewPage"
```

If opening fails, diagnose and retry. Inspect every representative primary image for readability,
safe-area placement, clipping, word wrapping, stable beat placement, and unwanted
pixels. Machine validation must already have passed every dense sample, including
`no-caption`, before this gate. Standard without spatial context binds the
maintained four images:

```powershell
$Evidence = @(
  "$Review\preview-early.png",
  "$Review\preview-middle.png",
  "$Review\preview-late.png",
  "$Review\preview-no-caption.png"
) -join ","

node "$SkillRoot\scripts\caption_interaction.mjs" preview-ready `
  --state $Receipt --project-meta "$PreviewProject\project-meta.json" `
  --evidence $Evidence --review-page "$Review\captions-review.html" `
  --timeline "$Work\timeline.json"
```

With spatial context, keep those maintained Standard samples and add dense
start/25%/50%/75%/end evidence only for placement beats that carry a composite
background. Do not add dense evidence for A-roll placement beats.

Use that fixed four-image command only when Standard has no spatial context. For
Standard with a bound spatial context, bind only the representative PNGs and bind
the complete machine evidence document separately. Standard has no coexistence comparison, so do not pass
`--comparison-evidence`:

```powershell
$StandardSpatialEvidenceDocument = Get-Content "$Review\captions-evidence.json" -Raw | ConvertFrom-Json
$Evidence = @($StandardSpatialEvidenceDocument.review_samples | ForEach-Object {
  Join-Path $Review $_.preview
}) -join ","

node "$SkillRoot\scripts\caption_interaction.mjs" preview-ready `
  --state $Receipt --project-meta "$PreviewProject\project-meta.json" `
  --evidence $Evidence --evidence-document "$Review\captions-evidence.json" `
  --review-page "$Review\captions-review.html" `
  --timeline "$Work\timeline.json"
```

Expressive binds the representative PNGs, complete machine document, and separate
coexistence pair from `captions-evidence.json`:

```powershell
$EvidenceDocument = Get-Content "$Review\captions-evidence.json" -Raw | ConvertFrom-Json
$Evidence = @($EvidenceDocument.review_samples | ForEach-Object {
  Join-Path $Review $_.preview
}) -join ","
$ComparisonEvidence = @($EvidenceDocument.experimental_comparison.samples | ForEach-Object {
  Join-Path $Review $_.preview
}) -join ","

node "$SkillRoot\scripts\caption_interaction.mjs" preview-ready `
  --state $Receipt --project-meta "$PreviewProject\project-meta.json" `
  --evidence $Evidence --evidence-document "$Review\captions-evidence.json" `
  --comparison-evidence $ComparisonEvidence `
  --review-page "$Review\captions-review.html" --timeline "$Work\timeline.json"
```

In human mode, present the opened page and its images, then **Present + STOP**.
The human copies one of these structured summaries from the page:

```text
Caption preview review
Review: <UUID from the opened page>
Decision: approve
Evidence: early, middle, late, no-caption
```

Expressive approval uses the dynamic evidence token and requires the explicit
Karaoke choice made after inspecting the bound comparison evidence:

```text
Caption preview review
Review: <UUID from the opened page>
Decision: approve
Evidence: expressive-layout-beats
Karaoke: on|off
```

When `caption-spatial-context.json` is bound, the authoritative page emits the
composite-aware token. Standard uses the same block without the Karaoke line;
Expressive requires the explicit Karaoke choice:

```text
Caption preview review
Review: <UUID from the opened page>
Decision: approve
Evidence: composite-aware
Karaoke: on|off
```

```text
Caption preview review
Review: <UUID from the opened page>
Decision: revise
Changes: Raise captions 20 pixels.
```

Pass the returned summary unchanged to `confirm --response` or
`adjust --response`. Quote the multiline response safely in PowerShell:

```powershell
$PreviewResponse = @'
Caption preview review
Review: <UUID from the opened page>
Decision: approve
Evidence: early, middle, late, no-caption
'@
node "$SkillRoot\scripts\caption_interaction.mjs" confirm `
  --state $Receipt --response $PreviewResponse
```

For a `revise` summary, preserve it in `$PreviewResponse` the same way and run:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" adjust `
  --state $Receipt --response $PreviewResponse
```

Apply the requested change, then regenerate the preview project, review page, and
all evidence before presenting the gate again. Never convert human feedback into
an Agent decision.

In delegated mode, the Agent must inspect the same `captions-review.html` page and
all primary evidence plus any coexistence comparison before recording its own rationale.
For Standard, keep the existing command unchanged:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" agent-confirm `
  --state $Receipt `
  --rationale "All bound primary frames are readable and collision-free; coexistence comparison evidence was inspected separately when present."
```

For Expressive, pass the explicit Karaoke choice made from the comparison:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" agent-confirm `
  --state $Receipt --karaoke off `
  --rationale "The semantic-only comparison is clearer for this footage."
```

Generate the approved overlay project. This formal render is the only step that
finalizes `style`, `review`, and hashed runtime assets in the canonical plan.
Expressive overlay generation uses the preview-approved Karaoke choice; an
explicit `--karaoke` value must match that approval:

For Expressive, formal overlay generation stores the Human-visible representative
PNGs in `review.representative_evidence`. It keeps `review.evidence` as the shared
delivery compiler compatibility set: one already-bound machine sample per layout beat
plus `no-caption`, selected from `captions-evidence.json`. This does not add cards to
the human review or claim that the user inspected machine-only samples; the complete
document path, hash, and sample count remain in `review.machine_evidence_document`.

```powershell
node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo --captions $Plan --out $OverlayProject `
  --interaction-state $Receipt --project-root $ProjectRoot --mode overlay @SpatialArgs

npx.cmd hyperframes check $OverlayProject --at 1 --timeout 10000 --no-contrast

$RenderMeta = Get-Content -Raw "$OverlayProject\project-meta.json" | ConvertFrom-Json
$RenderFps = "$($RenderMeta.fpsRational.num)/$($RenderMeta.fpsRational.den)"
Push-Location $OverlayProject
try {
  npx.cmd hyperframes render --format png-sequence --fps $RenderFps --output $OverlayFrames
}
finally {
  Pop-Location
}
```

Canonical overlay generation refreshes the `## Approval` section in
`captions-summary.md` with the selected style, decision actor/rationale, and
hash-binding result. It deliberately leaves rendered-frame and shared-delivery
checks pending; replace that pending line with the measured results before marking
the operation verified.

After cache deletion, rebuild the composition without replaying approval:

```powershell
node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo --captions $Plan --out $OverlayProject `
  --approved-plan true --project-root $ProjectRoot --mode overlay @SpatialArgs
```

The command verifies that the frozen runtime hashes still match.

## Project Registration

Add or revise one `captions` operation in `work/project.json`. Depend on
`understanding`; also depend on the active `cut` operation when it exists.
When active B-roll supplied the spatial context, also add `b-roll` to
`depends_on`; its `based_on` value must equal the bound active B-roll revision.
When there is no spatial context, omit `b-roll` from `depends_on` and
`based_on`. All `based_on` values must equal the current dependency revisions.

```json
{
  "id": "captions",
  "skill": "video-add-captions",
  "revision": 1,
  "depends_on": ["understanding", "cut", "b-roll"],
  "based_on": {"understanding": 1, "cut": 1, "b-roll": 4},
  "status": "verified",
  "plan": "captions/captions-plan.json",
  "outputs": ["cache/captions/overlay-frames"],
  "target": {"sequence": "main", "scope": "captions"},
  "effects": {
    "changes_timeline": false,
    "changes_geometry": false,
    "changes_video_pixels": false,
    "changes_audio": false,
    "adds_track": "captions"
  },
  "check": {"status": "pass", "report": "../review/05-captions/captions-summary.md"},
  "render": {
    "kind": "overlay",
    "asset": "cache/captions/overlay-frames",
    "asset_type": "image-sequence",
    "pattern": "frame_%06d.png",
    "start_number": 1,
    "fps": {"num": 30000, "den": 1001}
  }
}
```

Use the actual timeline FPS. Insert `captions` before active `content-cards` and
`graphic-motion` operations. Captions never depend on either downstream operation;
adding captions to a project that already contains them requires reordering the active
sequence. Then compile and render delivery once:

```powershell
python "$RepoRoot\skills\video-understand\scripts\validate.py" project `
  "$Work\project.json" $ProjectRoot
python "$RepoRoot\skills\video-understand\scripts\build_render_plan.py" $ProjectRoot
python "$RepoRoot\skills\video-understand\scripts\render_project.py" `
  "$Work\render\render-plan.json"
```

The shared renderer copies audio only for an identity timeline with no audio
filters. Cuts or retiming require encoded/filtered audio. Caption code never
overrides that decision.

## Compatibility

Without `--timeline`, `build_captions.py` still writes the old cue array.
`generate_caption_project.mjs` accepts that array with the interaction receipt.
Standalone exact ID and skip responses are legacy compatibility only. Standalone
`approve` is also a legacy compatibility response. Historical non-English aliases
remain accepted as input compatibility but are never emitted or documented as
user instructions.
`composite_caption_overlay.ps1` accepts an overlay video or `frame_%06d.png`
directory and writes compatible H.264/yuv420p while copying source audio. Use this
standalone path only when no active operation changes time; canonical projects use
the shared renderer.

## Self Check

Run before declaring the operation verified:

```powershell
python "$SkillRoot\scripts\check_project_protocol.py"
node "$SkillRoot\scripts\check_caption_style_config.mjs"
python "$SkillRoot\scripts\check_caption_spatial_context.py"
python "$SkillRoot\scripts\check_caption_review.py"
node "$SkillRoot\scripts\check_caption_interaction.mjs"
powershell.exe -ExecutionPolicy Bypass -File "$SkillRoot\scripts\check_structure.ps1"
node "$SkillRoot\scripts\caption_interaction.mjs" status --state $Receipt
```

Also verify:

- cue and word times are finite, ordered, within program duration, and never cross clips;
- early/middle/late captions appear on the correct mapped source pixels;
- dropped speech has no cue;
- overlay first frame exists, dimensions match, FPS equals timeline rational FPS,
  frame count equals `ceil(program_duration_s * fps.num / fps.den)`, duration covers
  the complete program, and non-caption pixels are transparent;
- the shared delivery exists, has synchronized audio, and passes the project's
  delivery report;
- `captions-summary.md` records the selected style, approval mode/rationale,
  evidence, and validation result.

HTML generation alone is not success. Inspect actual pixels and the final delivery
before reporting completion.
