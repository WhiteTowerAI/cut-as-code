---
name: video-to-shorts
description: >
  Select complete short-form moments from a verified Open Recut main delivery,
  extract approved horizontal derivatives, and optionally render reviewed 9:16
  versions. Uses the shared program transcript/timeline, hash-bound human or
  delegated-agent decisions, and Project Protocol V1 output locations.
---

# Video To Shorts

## Scope

This skill owns short candidate judgment, deterministic qualification, horizontal
extraction, short-relative transcripts, and optional deterministic vertical
delivery. It does not transcribe in project mode, change the main sequence, add
captions/graphics, grade, publish, or perform continuous subject tracking.

Shorts are derivatives of `final/final-video.mp4`. Record the operation in the
project DAG, but never add it to `sequences.main.operations`; the main delivery and
its original-vs-final comparison remain unchanged.

## Project Inputs

- `work/project.json`, whose main render status is `verified`
- `final/final-video.mp4`, exactly matching the project render path
- `work/understand/transcript.json` in source time
- `work/timeline.json`
- active main-operation revisions

`prepare_transcript.py --timeline` calls the shared
`projectlib.map_transcript_to_timeline`. Candidate/extraction times are therefore
program seconds on the actual final video. Words removed by the main edit are not
available to shorts. Each retained word keeps its `source_range`, `program_range`,
and `clip_id`.

Project transcript metadata binds the final video, source transcript, and timeline
by absolute path, size, modified time, and SHA-256. Candidate validation refuses a
changed binding.

## Output Layout

```text
work/shorts/
|-- transcript.json
|-- transcript_metadata.json
|-- candidates.json
|-- shorts-plan.json
|-- review/candidate_review.json
`-- short-001/
    |-- transcript.json
    |-- extraction-report.json
    `-- vertical-agent/
        |-- agent_vertical_plan.json
        |-- vertical_plan.json
        `-- review/vertical_review.json

work/cache/shorts/                 # disposable frames/sheets/intermediate media

review/06-shorts/
|-- candidates.html
|-- candidates-summary.md
|-- short-001-horizontal.jpg
|-- short-001-vertical-preview.mp4
|-- short-001-vertical-contact-sheet.jpg
`-- shorts-summary.md

final/shorts/
|-- short-001-horizontal.mp4
`-- short-001-vertical.mp4          # only when selected and approved
```

## Program Transcript

Run from the repository root:

```powershell
$RepoRoot = (Resolve-Path ".").Path
$SkillRoot = Join-Path $RepoRoot "skills\video-to-shorts"
$ProjectRoot = (Resolve-Path "<project-root>").Path
$Work = Join-Path $ProjectRoot "work"
$ShortsWork = Join-Path $Work "shorts"
$FinalVideo = Join-Path $ProjectRoot "final\final-video.mp4"
$ShortsReview = Join-Path $ProjectRoot "review\06-shorts"
New-Item -ItemType Directory -Force $ShortsWork,$ShortsReview | Out-Null

python "$SkillRoot\scripts\prepare_transcript.py" $FinalVideo `
  --transcript "$Work\understand\transcript.json" `
  --timeline "$Work\timeline.json" `
  --out $ShortsWork
```

Project timeline mode requires the canonical supplied transcript. Standalone mode
may omit `--timeline`; it keeps input-relative time and may use the temporary
`video-understand/scripts/transcribe.py` fallback. No transcript is auto-discovered.

## Candidate Authoring

Generate long-video visual context into cache, inspect every sheet needed for a
decision, and hand-author candidate JSON. Deterministic code validates editorial
judgment; it does not invent candidates or scores.

```powershell
python "$SkillRoot\scripts\prepare_visual_context.py" $FinalVideo `
  --out "$Work\cache\shorts\candidate-visual" --interval 15
```

Candidate input remains `shorts-candidates.v2` for compatibility. Set
`selection.evidence_mode` and every candidate `evidence_mode` to `text_visual`.
Each candidate requires:

- stable `candidate_id`, title, and scene type;
- complete `start_time`/`end_time` in program time;
- `transcript_excerpt` exactly equal to overlapping transcript words, not whole
  overlapping segments;
- all six score entries and non-empty reasons;
- non-empty `metadata.editorial_reason`;
- optional reviewed `filler_drop_spans` and visual evidence fields.

Do not supply total `score`; the validator adds the six dimensions:

| Dimension | Maximum |
|---|---:|
| `hook` | 20 |
| `completeness` | 20 |
| `audience_value` | 20 |
| `emotion_tension` | 15 |
| `quotability` | 15 |
| `pace_editability` | 10 |

Prefer a complete, independently understandable thought over a shorter fragment.
Keep a dependent interviewer question, premise, claim support, reversal, or payoff
when it is necessary. Boundaries must land on whole words and thoughts.

Validate the authored file:

```powershell
$CandidateDir = Join-Path $ShortsWork "preview\text_visual"
python "$SkillRoot\scripts\candidates.py" `
  --out $CandidateDir `
  --candidates "$CandidateDir\candidate-input.json" `
  --transcript "$ShortsWork\transcript.json" `
  --project-root $ProjectRoot
```

This writes the compatibility preview files, durable `work/shorts/candidates.json`,
and `review/06-shorts/candidates.{html,summary.md}`.

## Review Modes

Candidate selection and delivery mode are one hash-bound gate. Delivery is exactly
`horizontal_only` or `horizontal_and_vertical`.

Human mode:

```powershell
python "$SkillRoot\scripts\interaction.py" candidate-open --out $ShortsWork
```

Show the generated question, wait, then record the response unchanged with
`candidate-answer`. Never simulate it.

When the user explicitly delegates decisions:

```powershell
python "$SkillRoot\scripts\interaction.py" candidate-open `
  --out $ShortsWork --decision-mode agent `
  --delegation-note "User delegated shorts selection and vertical approval."

python "$SkillRoot\scripts\interaction.py" candidate-agent-approve `
  --out $ShortsWork `
  --candidates "text_visual/cand-001" `
  --delivery horizontal_and_vertical `
  --rationale "The selected range has a self-contained hook, explanation, and payoff."
```

Agent mode requires explicit candidate references, delivery mode, and rationale. It
never writes `user_response`. Human commands fail in agent mode and vice versa.
Regenerated source/candidate/preview artifacts invalidate approval.

## Canonical Plan

```powershell
python "$SkillRoot\scripts\plan.py" `
  --out $ShortsWork --project-root $ProjectRoot
```

`work/shorts/shorts-plan.json` uses integer `schema_version: 1`. It records:

- `target: derived`, `timebase: program`, and `timeline_id`;
- the verified main-render path and fingerprint;
- exact `depends_on` / `based_on` revisions from the active main sequence;
- selection mode, rationale, delivery mode, and review ID;
- stable short IDs;
- explicit `program_range` and mapped `source_ranges`;
- scoring/editorial evidence, approved filler drops, and program-time keep spans;
- work transcript/report paths and `../final/shorts/*.mp4` delivery paths.

Qualification remains deterministic: score at least 70, completeness at least 15,
estimated output duration 20-90 seconds, valid exact excerpt, no greater-than-50%
overlap with a higher-ranked short, and at most five outputs unless configured.

Only isolated, semantically empty hesitation words with safe word boundaries may be
approved as filler drops. Rejected/unsafe spans remain in the plan with reasons.
Total removal may not exceed 15% and no keep span may be shorter than 0.15 seconds.

## Horizontal Extraction

```powershell
python "$SkillRoot\scripts\extract_shorts.py" `
  --video $FinalVideo --out $ShortsWork `
  --project-root $ProjectRoot
```

Before extraction, the script rechecks the main-render fingerprint, project render
status, dependency revisions, candidate receipt, approved candidate hash, and source
video. Each keep range becomes its own seeked `-ss/-t/-i` input; ffmpeg concatenates
those inputs and performs one H.264/AAC encode. It does not decode the complete main
video once per keep range.

The short-relative transcript excludes dropped words, shifts later words onto a
continuous zero-based clock, and retains input program/source evidence. Horizontal
media goes directly to `final/shorts`; work contains only its transcript and report.

## Vertical Planning

Vertical delivery starts from the approved horizontal output. Generate dense visual
evidence at 1 second, or 0.5 seconds when motion requires it. Inspect every sheet and
author one of:

- `STATIC_CROP`: one stable fixed 9:16 crop.
- `SCENE_CROP`: scene-bounded fixed crops, with LETTERBOX only for scenes needing
  complete horizontal information.
- `LETTERBOX`: complete sharp foreground over a blurred/darkened fill.
- `REVIEW_REQUIRED`: evidence cannot support deterministic fixed crops; formal render
  is blocked.

Presenter scenes should keep the head and torso stable and large. Slides, products,
groups, and diagrams must retain essential information. Do not claim continuous
tracking. Crop changes belong at scene boundaries.

Each plan segment fully covers the short timeline, has a strategy, content type,
non-empty rationale, and valid in-bounds crop when applicable. Required content types
are `PRESENTER`, `WIDE_INFORMATION`, `PRODUCT`, `MULTI_SUBJECT`, and `OTHER`.

```powershell
$ShortId = "short-001"
$Horizontal = Join-Path $ProjectRoot "final\shorts\$ShortId-horizontal.mp4"
$VerticalWork = Join-Path $ShortsWork "$ShortId\vertical-agent"
$ExtractionReport = Join-Path $ShortsWork "$ShortId\extraction-report.json"

python "$SkillRoot\scripts\prepare_visual_context.py" $Horizontal `
  --out "$Work\cache\shorts\$ShortId-vertical-visual" --interval 1

python "$SkillRoot\scripts\vertical_plan.py" `
  --video $Horizontal `
  --input "$VerticalWork\agent_vertical_plan.json" `
  --out $VerticalWork `
  --source-video $FinalVideo `
  --extraction-report $ExtractionReport
```

`vertical_plan.json` preserves exact FPS as `{num, den}` and deterministically
validates geometry, coverage, strategy duration, and warnings. The direct-render
binding hashes the verified main delivery and the exact extraction report. Preview
review still uses the approved horizontal short timeline, while formal rendering maps
that timeline through the recorded `keep_spans` and reads pixels directly from the
verified main delivery.

Render a smaller preview into the user-facing review directory:

```powershell
python "$SkillRoot\scripts\render_vertical.py" `
  --video $Horizontal --plan "$VerticalWork\vertical_plan.json" `
  --out $VerticalWork --review-out $ShortsReview --mode preview
```

Inspect the complete preview, contact sheet, dimensions, crop safety, strategy
transitions, audio, and warnings. Human mode records `vertical-answer`. Delegated
mode records an honest agent decision:

```powershell
python "$SkillRoot\scripts\interaction.py" vertical-agent-approve `
  --out $VerticalWork `
  --rationale "All sampled scenes preserve the subject and essential information."
```

Formal render revalidates every approved artifact:

```powershell
python "$SkillRoot\scripts\render_vertical.py" `
  --video $Horizontal --plan "$VerticalWork\vertical_plan.json" `
  --out $VerticalWork --review-out $ShortsReview --mode final
```

The formal renderer uses rational `num/den`, one H.264/yuv420p generation from the
verified main delivery, `libx264 -preset slow -crf 16`, and encoded continuous audio.
Preview rendering remains `medium` / CRF 20 for faster review. The renderer checks
dimensions, duration, FPS, audio presence, source/report hashes, and keep-span mapping.

## Project Operation

Add one derived operation to `work/project.json`, but not to the main sequence:

```json
{
  "id": "shorts",
  "skill": "video-to-shorts",
  "revision": 1,
  "depends_on": ["understanding", "captions"],
  "based_on": {"understanding": 1, "captions": 1},
  "status": "verified",
  "plan": "shorts/shorts-plan.json",
  "outputs": [
    "../final/shorts/short-001-horizontal.mp4",
    "../final/shorts/short-001-vertical.mp4"
  ],
  "target": {"sequence": "main", "scope": "derivatives"},
  "effects": {
    "changes_timeline": true,
    "changes_geometry": true,
    "changes_video_pixels": true,
    "changes_audio": true,
    "adds_track": null
  },
  "check": {"status": "pass", "report": "../review/06-shorts/shorts-summary.md"}
}
```

Use the actual dependency list/revisions stored in the plan. Project validation checks
the DAG and files; shorts remain outside the main render plan.

## Compatibility

Without `--project-root`, candidates and `shorts-plan.v2` keep their established
standalone paths and input-relative time. The extractor accepts both plan shapes.
Legacy `short_XX/source.mp4` vertical workflows and human review commands remain valid.
Standalone fallback transcription uses the canonical `video-understand` transcriber
and a project-local model cache.

## Self Check

Run:

```powershell
python "$SkillRoot\scripts\check_project_protocol.py"
python "$RepoRoot\skills\video-understand\scripts\validate.py" project `
  "$Work\project.json" $ProjectRoot
```

For every delivered short verify:

- candidate excerpt equals overlapping program words and the thought is complete;
- source/program ranges and dependency revisions resolve;
- horizontal duration approximately equals keep-span sum;
- short transcript starts at zero, ends within media, and excludes removed words;
- horizontal output has expected FPS, H.264 video, synchronized audio, and review still;
- vertical output is 9:16, uses the exact rational FPS, keeps required content safe,
  has synchronized audio, matches its approved preview/plan hashes, and records
  `direct_render: true` with the verified main delivery as `render_source`;
- all user-facing media is under `review/` or `final/`, and disposable material is
  under `work/cache/`;
- `shorts-summary.md` records outputs, decisions, warnings, and checks.

Do not report success from JSON validation alone. Watch the horizontal and vertical
outputs and inspect their review images/contact sheets.
