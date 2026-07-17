---
name: video-vertical-reframe
description: >
  Reframe horizontal or wide videos into vertical video using explicit
  subject tracks, readable reframe plans, crop paths, visual review artifacts,
  and a gated preview-before-production workflow. Use when Codex needs to
  convert video to a 9:16 vertical composition, plan subject-aware crops,
  preserve full-frame shots with letterbox when needed, or render a final
  vertical MP4 only after the preview has passed human review.
---

# Video Vertical Reframe

Turn a source video into a vertical version through a staged, reviewable
pipeline:

```text
source video
  -> tracks.json
  -> reframe_plan.json
  -> crop_path.json
  -> preview artifacts
  -> vertical.mp4
```

Phase 0 defines only the skill contract, schemas, examples, and CLI shape. It
does not implement detection, planning, preview rendering, or production
rendering.

## Responsibility Boundary

`video-vertical-reframe` is responsible for:

- detecting visible person subjects when no external `tracks.json` is provided;
- accepting an external `subject-tracks.v1` file when the caller already has one;
- planning vertical crop and letterbox strategy from subject tracks;
- writing `reframe_plan.json` and `crop_path.json`;
- producing visual review artifacts before final render;
- rendering a final vertical MP4 only after preview review passes.

It is not responsible for:

- rough cuts or content removal;
- captions or subtitles;
- motion graphics or overlay cards;
- speaker identification or face identity;
- cross-video person identity;
- changing the source editorial content.

## Separation of Layers

Keep these layers separate:

- `subject detection`: answers where people are and writes `tracks.json`;
- `reframe planning`: answers how to crop or letterbox and writes
  `reframe_plan.json` plus `crop_path.json`;
- `rendering`: consumes the approved plan and crop path to create previews or
  final video, without re-detecting or re-planning.

Do not let rendering silently change crop strategy. If the strategy is wrong,
return to planning and regenerate the plan.

## Inputs

- Source video.
- Optional external `tracks.json`.
- Optional working directory.
- Optional encoder/render settings in later phases.

## Outputs

A complete run should write durable outputs under the caller-provided work
directory:

```text
work/vertical-reframe/
  tracks.json
  metrics.json
  reframe_plan.json
  crop_path.json
  artifacts/
    contact_sheet.jpg
    preview.mp4
    summary.md
    plan_contact_sheet.jpg
    plan_preview.mp4
    plan_summary.md
    reframe_preview.mp4
    reframe_preview_contact_sheet.jpg
    reframe_preview_summary.md
    final_contact_sheet.jpg
    final_summary.md
    media_probe.json
  out/
    vertical.mp4
```

Phase 0 creates only schema and example files. Later phases must create the
runtime outputs above.

## Phase 1 Subject Detection Commands

Phase 1 implements only the detection layer. It migrates the validated
`video-subject-detect` behavior into this skill so `video-vertical-reframe` can
keep working even if the standalone subject-detect skill is removed later.

Detect subjects:

```powershell
python skills/video-vertical-reframe/scripts/detect_subjects.py SOURCE.mp4 --out WORK --sample-fps 0.1 --max-frames 72
```

Render detection debug artifacts:

```powershell
python skills/video-vertical-reframe/scripts/render_detection_debug.py WORK/tracks.json SOURCE.mp4 --out WORK/artifacts
```

Phase 1 must produce:

- `WORK/tracks.json`
- `WORK/metrics.json`
- `WORK/artifacts/contact_sheet.jpg`
- `WORK/artifacts/preview.mp4`
- `WORK/artifacts/summary.md`

Phase 1 must not produce `reframe_plan.json`, `crop_path.json`, or
`vertical.mp4`.

## Phase 2 Reframe Planning Commands

Phase 2 consumes an existing `tracks.json` and does not run subject detection.
It writes the planning artifacts used for human review:

```text
tracks.json -> reframe_plan.json -> crop_path.json
```

Plan from external tracks:

```powershell
python skills/video-vertical-reframe/scripts/plan_reframe.py SOURCE.mp4 --tracks WORK/tracks.json --out WORK --ffprobe C:\path\to\ffprobe.exe
```

Render planning review artifacts:

```powershell
python skills/video-vertical-reframe/scripts/render_plan_debug.py SOURCE.mp4 --tracks WORK/tracks.json --plan WORK/reframe_plan.json --crop-path WORK/crop_path.json --out WORK/artifacts --ffmpeg C:\path\to\ffmpeg.exe
```

Phase 2 must produce:

- `WORK/reframe_plan.json`
- `WORK/crop_path.json`
- `WORK/plan_metrics.json`
- `WORK/artifacts/plan_contact_sheet.jpg`
- `WORK/artifacts/plan_preview.mp4`
- `WORK/artifacts/plan_summary.md`

Phase 2 strategies are:

- `TRACK`: reliable subject or subject group fits inside the 9:16 crop;
- `CENTER_FALLBACK`: no subject, low confidence, or high crop-edge risk;
- `LETTERBOX`: preserve the full frame when multiple subjects are too spread
  out or a shared crop would lose an important subject.

Phase 2 must not render `vertical.mp4`.

## Phase 3 Reframe Preview Command

Phase 3 consumes the approved `tracks.json`, `reframe_plan.json`, and
`crop_path.json`. It does not re-run detection and does not regenerate the plan.
It renders a low-resolution audit preview that shows the actual 9:16 reframed
view plus source-frame context for review.

```powershell
python skills/video-vertical-reframe/scripts/render_preview.py SOURCE.mp4 --tracks WORK/tracks.json --plan WORK/reframe_plan.json --crop-path WORK/crop_path.json --out-dir WORK/artifacts --ffmpeg C:\path\to\ffmpeg.exe
```

Phase 3 must produce:

- `WORK/artifacts/reframe_preview.mp4`
- `WORK/artifacts/reframe_preview_contact_sheet.jpg`
- `WORK/artifacts/reframe_preview_summary.md`

The preview must show the subject bbox, planned crop window, 9:16 visible area,
strategy, scene id, warnings, timestamp, crop center, and a simple sampled
center trail. Phase 3 must not render production `vertical.mp4`.

## Phase 4 Production Render Command

Phase 4 consumes the approved `reframe_plan.json` and `crop_path.json` and
renders the final vertical MP4. It does not re-run detection and does not
regenerate planning.

```powershell
python skills/video-vertical-reframe/scripts/render_reframe.py SOURCE.mp4 --plan WORK/reframe_plan.json --crop-path WORK/crop_path.json --out WORK/out/vertical.mp4 --ffmpeg C:\path\to\ffmpeg.exe --ffprobe C:\path\to\ffprobe.exe
```

Phase 4 must produce:

- `WORK/out/vertical.mp4`
- `WORK/artifacts/final_contact_sheet.jpg`
- `WORK/artifacts/final_summary.md`
- `WORK/artifacts/media_probe.json`

Defaults:

- target aspect ratio: `9:16`;
- output height: source video height;
- output width: `round(height * 9 / 16)` corrected to an even value;
- video encoder: `libx264`;
- pixel format: `yuv420p`;
- muxing: `+faststart`;
- audio: copy source audio when present.

## CLI Shape

This is the intended command shape for the full skill. Scripts appear as their
phase is implemented.

Subject detection:

```powershell
python skills/video-vertical-reframe/scripts/detect_subjects.py SOURCE.mp4 --out WORK --sample-fps 1 --max-frames 72
```

Reframe planning with external tracks:

```powershell
python skills/video-vertical-reframe/scripts/plan_reframe.py SOURCE.mp4 --tracks WORK/tracks.json --out WORK
```

Reframe planning with internal detection:

```powershell
python skills/video-vertical-reframe/scripts/plan_reframe.py SOURCE.mp4 --auto-detect --out WORK
```

Plan debug rendering:

```powershell
python skills/video-vertical-reframe/scripts/render_plan_debug.py SOURCE.mp4 --plan WORK/reframe_plan.json --crop-path WORK/crop_path.json --out WORK/artifacts
```

Low-resolution reframe preview:

```powershell
python skills/video-vertical-reframe/scripts/render_preview.py SOURCE.mp4 --plan WORK/reframe_plan.json --crop-path WORK/crop_path.json --tracks WORK/tracks.json --out WORK/artifacts/reframe_preview.mp4
```

Production render:

```powershell
python skills/video-vertical-reframe/scripts/render_reframe.py SOURCE.mp4 --plan WORK/reframe_plan.json --crop-path WORK/crop_path.json --out WORK/out/vertical.mp4
```

Optional encoder selection:

```powershell
python skills/video-vertical-reframe/scripts/render_reframe.py SOURCE.mp4 --plan WORK/reframe_plan.json --crop-path WORK/crop_path.json --out WORK/out/vertical.mp4 --encoder auto
```

## Phase Plan

### Phase 0: Project Skeleton

Create this skill package, schemas, examples, and CLI design. Do not implement
functional scripts. Stop after the contract is reviewable.

### Phase 1: Subject Detection

Migrate the validated `video-subject-detect` detection capability into this
skill. Preserve `tracks.json`, contact sheet, preview, metrics, and summary.
Run the three previously validated videos and stop for human review.

### Phase 2: Reframe Planning

Implement:

```text
tracks.json -> reframe_plan.json -> crop_path.json
```

Borrow Autocrop-vertical ideas such as content-aware cropping, scene strategy,
letterbox, and preserving full frame when subjects are too spread out. Do not
copy its code or its detection behavior. Do not render a final video.

### Phase 3: Reframe Preview

Render a low-resolution review video from the approved plan and crop path. Show
subject bbox, crop window, strategy, scene, warnings, and reasons. If strategy is
wrong, revise planning in this phase. Do not render production output.

### Phase 4: Production Render

After the preview passes human review, render `vertical.mp4` and complete
engineering hardening for scene optimization, crop smoothing, letterbox
optimization, audio sync, VFR handling, and encoder selection.

## Review Gates

Every phase must:

- complete only that phase;
- write a Diff Summary;
- provide runnable commands and their results;
- produce reviewable artifacts for the phase;
- state what to inspect, what passes, and what requires rework;
- stop and wait for human confirmation before the next phase.

## Contract Files

- `reference/subject-tracks.schema.json`: stable subject detection contract.
- `reference/reframe-plan.schema.json`: strategy-level crop and letterbox plan.
- `reference/crop-path.schema.json`: time-sampled crop boxes used by renderers.
- `examples/tracks.example.json`: minimal valid subject tracks example.
- `examples/reframe_plan.example.json`: minimal valid planning example.
- `examples/crop_path.example.json`: minimal valid crop path example.
