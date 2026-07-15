---
name: video-add-captions-hyperframes
description: >
  Add styled, transcript-timed captions to an existing video with HyperFrames.
  Use for burned-in subtitles, short-form caption styling, and optional per-word
  karaoke highlighting. Render a caption overlay first, verify visible frames,
  then composite it onto the source video with ffmpeg while copying audio.
---

# Video Add Captions — HyperFrames

This skill is the HyperFrames migration target for `video-add-captions`. The
existing Remotion skill remains the reference implementation until visual and
timing parity are verified.

## Scope

Use this skill for:

- Every-line captions generated from word-timed transcript data.
- Preset-driven caption layout and typography.
- Optional per-word karaoke highlighting.
- A transparent caption overlay that can be composited onto the source video.

Do not use this skill for rough cutting, editorial selection, or selective
motion graphics.

## Current migration status

Phase 3 provides a deterministic HyperFrames caption sample, framework-neutral
style configuration, a deep-merge resolver, a data-driven project generator,
transparent overlay rendering, and ffmpeg compositing with copied source audio.
It intentionally does not replace the existing Remotion skill yet.

The current renderer supports source-video playback, cue JSON, all official
presets, highlight/background/stroke themes, karaoke selection, JSON overrides,
transparent WebM overlays, and final ffmpeg compositing with `-c:a copy`.

## Inputs

- A finished source video.
- Word-timed caption cues produced by the existing caption-building pipeline.
- A selected caption preset.

Caption cue shape:

```json
{
  "start": 0.5,
  "end": 2.8,
  "words": [
    { "text": "Make", "start": 0.5, "end": 0.9 },
    { "text": "every", "start": 0.9, "end": 1.4 },
    { "text": "word", "start": 1.4, "end": 1.9 },
    { "text": "count", "start": 1.9, "end": 2.8 }
  ]
}
```

## Workflow

1. Reuse the existing transcript and caption grouping pipeline.
2. Map the requested look to a stable preset.
3. Generate a HyperFrames composition from caption cues.
4. Run `npx.cmd hyperframes check`.
5. Capture representative snapshots and inspect placement, wrapping, and
   karaoke timing.
6. Render the caption overlay only after the preview passes review.
7. Composite the overlay onto the source with ffmpeg and copy the original
   audio stream.

## Phase 1 example

`examples/index.html` is a fixed 9-second, 1080x1920 caption composition. It
demonstrates:

- Caption cue visibility windows.
- Bottom-safe vertical placement.
- Pop-in motion translated from Remotion frame interpolation.
- Word-level karaoke highlighting.
- One paused GSAP timeline registered with HyperFrames.

Run from the example directory:

```powershell
npx.cmd hyperframes check
npx.cmd hyperframes snapshot --at 1,4,7
npx.cmd hyperframes render --output out/caption-preview.mp4
```

## Generate a real caption project

First build caption cues with the existing deterministic grouping script:

```powershell
py -3 ..\video-add-captions\scripts\build_captions.py transcript.json captions.json captions.srt --max-chars 22 --max-lines 2 --max-dur 4 --gap 0.6
```

Then generate a self-contained HyperFrames project:

```powershell
node scripts\generate_caption_project.mjs `
  --video source.mp4 `
  --captions captions.json `
  --out work\hyperframes-project `
  --preset shorts `
  --highlight-theme yellow `
  --karaoke true
```

The generated composition contains a direct-child muted video element and a
separate direct-child audio element, as required by HyperFrames.

Supported official presets:

- `clean`
- `minimal`
- `social-bold`
- `pill`
- `boxed`
- `stroked`
- `shorts`

Optional theme flags:

- `--highlight-theme bright-green|orange|yellow`
- `--background-theme gray|yellow|blue|pink|green`
- `--stroke-theme black|yellow|blue|pink|green`
- `--karaoke auto|true|false`
- `--mode preview|overlay`
- `--overrides path\to\overrides.json`

Run the style-system guardrail before generating previews:

```powershell
node scripts\check_caption_style_config.mjs
```

## Transparent overlay render

Generate an overlay-only project:

```powershell
node scripts\generate_caption_project.mjs `
  --video source.mp4 `
  --captions captions.json `
  --out work\overlay-project `
  --preset shorts `
  --highlight-theme yellow `
  --karaoke true `
  --mode overlay
```

Render with an alpha-capable format:

```powershell
Set-Location work\overlay-project
npx.cmd hyperframes render --format webm --output out\caption-overlay.webm
```

Composite it onto the source while copying the original audio stream:

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\composite_caption_overlay.ps1 `
  -SourceVideo source.mp4 `
  -OverlayVideo caption-overlay.webm `
  -OutputVideo captioned.mp4
```

The compositor decodes VP9 alpha with `libvpx-vp9` and uses
`overlay=format=yuv420` for WebM overlays. Keep that explicit format: using
`format=auto` can lift black levels in dark limited-range BT.709 footage.

## Verification requirements

Before declaring a migration phase complete:

- The migration lint contains no blockers.
- HyperFrames check reports no errors.
- Openable snapshots exist for at least three caption moments.
- Caption position, wrapping, font, and active-word timing are visually checked.
- A dark no-caption frame preserves source black level and average luma.
- The original `skills/video-add-captions` directory remains unchanged.

## Migration references

- `reference/MIGRATION.md` records the current API mapping and remaining work.
- The installed `remotion-to-hyperframes` skill is a migration tool only and is
  not copied into this skill.
