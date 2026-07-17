---
name: video-add-captions
description: >
  Add word-timed captions to an Open Recut program. Use this skill to map the
  canonical transcript through timeline.json, review a maintained style on
  source-backed pixels, render a local transparent HyperFrames PNG sequence,
  and register it as an overlay contribution for the shared delivery render.
---

# Video Add Captions

## Scope

This skill owns caption grouping, style selection, review, and the transparent
caption track. It does not transcribe, cut, retime, grade, reframe, or choose the
delivery audio policy.

Use `video-understand` first. If a rough cut exists, caption the active program
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
`-- caption-interaction.json
work/cache/captions/
|-- preview-project/
|-- preview-snapshots/
|-- overlay-project/
`-- overlay-frames/frame_000001.png ...
review/05-captions/
|-- captions.srt
|-- preview-early.png
|-- preview-middle.png
|-- preview-late.png
|-- preview-no-caption.png
|-- captions-evidence.json
`-- captions-summary.md
```

Generated HTML, copied runtime files, extracted source frames, and overlay frames
are cache. The plan, SRT, decision receipt, and review evidence are durable.

## Caption Plan

`work/captions/captions-plan.json` is schema V1, targets `overlay`, and uses
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

## Styles

Maintained presets are `clean`, `minimal`, `social-bold`, `pill`, `boxed`,
`stroked`, and `shorts`. Gallery combination IDs add maintained themes, for
example `pill-yellow`, `stroked-blue`, and `shorts-green`. Karaoke is an option,
not a separate preset.

Default delegated choice: `clean`, Karaoke off. Choose a more expressive preset
only when the destination or footage justifies it. Store job-specific changes in
an overrides JSON; do not edit the generator for ordinary style feedback.

Read:

- `reference/caption-rules.md` before changing grouping limits;
- `reference/caption-style-themes.md` for style vocabulary;
- `reference/caption-feedback-mapping.md` for override mapping.

## Decision Modes

Two honest modes share the same hash-bound state machine:

- `human`: record the user's exact gallery response with `select`, show all real
  preview evidence, and record the exact confirmation response with `confirm`.
- `agent`: use only when the user explicitly delegates caption decisions. Start
  with a non-empty delegation note, then use `agent-select` and `agent-confirm`
  with non-empty rationales.

Human commands fail in agent mode and agent commands fail in human mode. Both
modes require four existing source-backed images before approval. Any source,
plan, selection, override, or preview change invalidates the old approval.

## Canonical Workflow

Run from the repository root. Set project paths:

```powershell
$RepoRoot = (Resolve-Path ".").Path
$SkillRoot = Join-Path $RepoRoot "skills\video-add-captions"
$ProjectRoot = (Resolve-Path "<project-root>").Path
$Work = Join-Path $ProjectRoot "work"
$SourceVideo = "<absolute path from work/project.json>"
$Plan = Join-Path $Work "captions\captions-plan.json"
$Receipt = Join-Path $Work "captions\caption-interaction.json"
$Review = Join-Path $ProjectRoot "review\05-captions"
$Cache = Join-Path $Work "cache\captions"
$PreviewProject = Join-Path $Cache "preview-project"
$OverlayProject = Join-Path $Cache "overlay-project"
$OverlayFrames = Join-Path $Cache "overlay-frames"
New-Item -ItemType Directory -Force -Path (Split-Path $Plan),$Review,$Cache | Out-Null
```

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

Start one decision mode. Human mode opens the maintained offline gallery:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" start `
  --state $Receipt --source $SourceVideo --captions $Plan
```

Print the command output, wait for the user, and pass the response unchanged to
`select`. Never infer or simulate the response.

For explicit delegation:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" start `
  --state $Receipt --source $SourceVideo --captions $Plan `
  --decision-mode agent `
  --delegation-note "User delegated caption style and preview approval." `
  --no-open true

node "$SkillRoot\scripts\caption_interaction.mjs" agent-select `
  --state $Receipt --choice clean `
  --rationale "Conservative readable treatment preserves the talking-head frame."
```

Generate a transparent preview composition. The project contains only local GSAP
and font files and preserves rational FPS in `project-meta.json`:

```powershell
node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo --captions $Plan --out $PreviewProject `
  --interaction-state $Receipt --project-root $ProjectRoot --mode preview

npx.cmd hyperframes check $PreviewProject --at 1 --timeout 10000 --no-contrast
```

Build mapped early/middle/late/no-caption evidence. This command captures
transparent HyperFrames snapshots, maps each program time through
`timeline.json`, extracts the matching original source frame, and composites the
two with Pillow:

```powershell
python "$SkillRoot\scripts\build_caption_review.py" `
  --source $SourceVideo --timeline "$Work\timeline.json" --plan $Plan `
  --project $PreviewProject --cache "$Cache\review-cache" --out $Review
```

Inspect all four images for readability, safe-area placement, clipping, word
wrapping, and any unwanted pixels in `preview-no-caption.png`. Record them:

```powershell
$Evidence = @(
  "$Review\preview-early.png",
  "$Review\preview-middle.png",
  "$Review\preview-late.png",
  "$Review\preview-no-caption.png"
) -join ","

node "$SkillRoot\scripts\caption_interaction.mjs" preview-ready `
  --state $Receipt --project-meta "$PreviewProject\project-meta.json" `
  --evidence $Evidence
```

In human mode, show the images, print the command output, and wait. Use `adjust`
for requested changes and regenerate all evidence. In delegated mode, inspect the
pixels and record the decision:

```powershell
node "$SkillRoot\scripts\caption_interaction.mjs" agent-confirm `
  --state $Receipt `
  --rationale "Early, middle, late, and no-caption frames are readable and collision-free."
```

Generate the approved overlay project. This formal render is the only step that
finalizes `style`, `review`, and hashed runtime assets in the canonical plan:

```powershell
node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo --captions $Plan --out $OverlayProject `
  --interaction-state $Receipt --project-root $ProjectRoot --mode overlay

npx.cmd hyperframes check $OverlayProject --at 1 --timeout 10000 --no-contrast

Push-Location $OverlayProject
try {
  npx.cmd hyperframes render --format png-sequence --output $OverlayFrames
}
finally {
  Pop-Location
}
```

After cache deletion, rebuild the composition without replaying approval:

```powershell
node "$SkillRoot\scripts\generate_caption_project.mjs" `
  --video $SourceVideo --captions $Plan --out $OverlayProject `
  --approved-plan true --mode overlay
```

The command verifies that the frozen runtime hashes still match.

## Project Registration

Add or revise one `captions` operation in `work/project.json`. Depend on
`understanding`; also depend on the active `rough-cut` operation when it exists.
`based_on` must equal the current dependency revisions.

```json
{
  "id": "captions",
  "skill": "video-add-captions",
  "revision": 1,
  "depends_on": ["understanding", "rough-cut"],
  "based_on": {"understanding": 1, "rough-cut": 1},
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

Use the actual timeline FPS. Add `captions` to the active sequence operations,
then compile and render delivery once:

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
`composite_caption_overlay.ps1` accepts an overlay video or `frame_%06d.png`
directory and writes compatible H.264/yuv420p while copying source audio. Use this
standalone path only when no active operation changes time; canonical projects use
the shared renderer.

## Self Check

Run before declaring the operation verified:

```powershell
python "$SkillRoot\scripts\check_project_protocol.py"
node "$SkillRoot\scripts\check_caption_style_config.mjs"
powershell.exe -ExecutionPolicy Bypass -File "$SkillRoot\scripts\check_structure.ps1"
node "$SkillRoot\scripts\caption_interaction.mjs" status --state $Receipt
```

Also verify:

- cue and word times are finite, ordered, within program duration, and never cross clips;
- early/middle/late captions appear on the correct mapped source pixels;
- dropped speech has no cue;
- overlay first frame exists, dimensions match, FPS equals timeline rational FPS,
  duration covers the complete program, and non-caption pixels are transparent;
- the shared delivery exists, has synchronized audio, and passes the project's
  delivery report;
- `captions-summary.md` records the selected style, approval mode/rationale,
  evidence, and validation result.

Do not report success from a generated HTML file alone. Inspect real rendered
pixels and the final delivery.
