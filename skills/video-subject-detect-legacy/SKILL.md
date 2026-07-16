---
name: video-subject-detect
description: >
  Detect person subjects in a video and emit a stable, reusable subject-tracks
  interchange file for other Open-Recut skills. This skill is a low-level Vision
  primitive: it produces subject position data plus review artifacts, not final
  crops, captions, overlays, or edited videos.
---

# Video Subject Detect

Turn a source video into a stable `subject-tracks.v1` data file that downstream
skills can consume when they need to know where the visible person subject is.
This is the Vision analogue of the shared transcript format: a reusable fact
layer, not a final edit.

## Goal

`video-subject-detect` is responsible for:

- detecting visible person subjects in the source video;
- grouping continuous visibility into tracks;
- writing `tracks.json` using the schema in `reference/subject-tracks.schema.json`;
- writing machine-readable run metrics;
- producing visual review artifacts so a human can confirm the detections before
  another skill relies on them.

It is not responsible for:

- final crop or reframe decisions;
- subtitle, sticker, animation, or overlay placement;
- speaker identification;
- face identity;
- object, animal, or logo detection;
- cross-shot or cross-video identity consistency.

## Inputs

- A source video file.
- Optional detector configuration, once implementation exists.
- Optional sampling settings, once implementation exists.

Phase 0 defines the contract only. It does not provide detection scripts.

## Outputs

A run should write durable, reviewable outputs under a caller-provided work
directory, for example:

```text
work/subject-detect/
  tracks.json
  metrics.json
  artifacts/
    contact_sheet.jpg
    preview.mp4
    summary.md
```

Required contract files in this skill package:

- `reference/subject-tracks.schema.json` is the stable downstream contract.
- `examples/tracks.example.json` is the smallest valid example of that contract.

Phase 1 and later runs must produce `artifacts/contact_sheet.jpg`. A run without a
visual review artifact is incomplete, even if `tracks.json` exists.

## Definitions

### Subject

In MVP, a subject is a visible person.

`Subject = Person`

MVP does not support animals, objects, logos, speaker identification, or face
identity.

### Track

A track is one continuous visible segment of a subject's motion through time.
In MVP, `subject_id` is equal to `track_id`. It is a track-local identifier, not
a promise that the same real person will keep the same id across shots, scenes,
or separate videos.

### Bounding Box

A bounding box is the visible person region in source-video pixel coordinates.
The preferred box is full body. If full body is not detectable, an upper-body
box is allowed and must be marked with `bbox_kind: "upper_body"`.

`bbox` uses `{ "x", "y", "w", "h" }`, measured in source pixels.

## Schema Contract

Downstream skills should consume only `subject-tracks.v1` fields defined in
`reference/subject-tracks.schema.json`. Detector names, model versions, and
debug-only overlays may change without changing the contract.

Stable fields include:

- `schema_version`
- `video.width`, `video.height`, `video.fps`, `video.duration_s`
- `coordinate_space`
- `frames[].time_s`
- `frames[].subjects[].subject_id`
- `frames[].subjects[].track_id`
- `frames[].subjects[].class`
- `frames[].subjects[].bbox`
- `frames[].subjects[].bbox_kind`
- `frames[].subjects[].confidence`
- `tracks[].track_id`
- `tracks[].start_s`
- `tracks[].end_s`
- `tracks[].coverage`

Future crop windows, safe areas, and reframe decisions are not part of
`subject-tracks.v1`. They may appear only in debug overlays or downstream skill
outputs.

## Visual Review Requirement

Every implemented run must produce visual review artifacts. Phase 1 must produce
at least:

- `artifacts/contact_sheet.jpg`

Later phases may also produce:

- `artifacts/preview.mp4`
- `artifacts/summary.md`
- sampled frame stills

The contact sheet should make it easy to inspect timestamps, subject ids, track
ids, bounding boxes, confidence, and whether a box is full-body or upper-body.

## Phase 0 Status

This phase intentionally adds documentation and schema only:

- no detector implementation;
- no tracker implementation;
- no ffmpeg or model integration;
- no preview renderer.

Stop after the contract is reviewable.

## Phase 1: Minimal Detection + Contact Sheet

Phase 1 adds the smallest runnable implementation:

- person detection only;
- no preview video;
- no automatic crop;
- no subtitle avoidance;
- no complex tracking;
- `subject_id` is equal to `track_id`;
- every run writes `tracks.json`, `metrics.json`, and
  `artifacts/contact_sheet.jpg`.

The MVP track assignment is intentionally simple: subjects are sorted left to
right in each sampled frame and assigned `t1`, `t2`, and so on. This is enough
to validate the interchange format and visual review loop, but it is not
identity tracking.

Example command:

```powershell
python scripts/detect_subjects.py SOURCE.mp4 --out work/subject-detect --sample-fps 1 --max-frames 36
```

If `ffmpeg` and `ffprobe` are not on PATH, pass them explicitly:

```powershell
python scripts/detect_subjects.py SOURCE.mp4 --out work/subject-detect --ffmpeg C:\path\to\ffmpeg.exe --ffprobe C:\path\to\ffprobe.exe
```

Review `work/subject-detect/artifacts/contact_sheet.jpg` before any downstream
skill consumes `tracks.json`.

## Phase 2: Low-Res Debug Preview

Phase 2 adds a dynamic review artifact:

- reads an existing `tracks.json`;
- extracts the sampled timestamps from the source video;
- draws bbox, `track_id` / `subject_id`, confidence, timestamp, and `NO SUBJECT`;
- writes `artifacts/preview.mp4`;
- writes or updates `artifacts/summary.md`.

This preview is a debug artifact only. It is not a final edit, not a real
horizontal-to-vertical crop, and it must not write future crop windows back into
`subject-tracks.v1`.

Example command:

```powershell
python scripts/render_debug.py work/subject-detect/tracks.json SOURCE.mp4 --out work/subject-detect/artifacts
```

Optional future crop windows may be displayed only as an overlay:

```powershell
python scripts/render_debug.py work/subject-detect/tracks.json SOURCE.mp4 --show-future-crop-window
```
