# Remotion to HyperFrames migration

## Source

The reference implementation remains:

`skills/video-add-captions`

Do not delete or overwrite it while this migration is incomplete.

## Phase 1 API mapping

| Remotion source | HyperFrames target |
| --- | --- |
| `Composition` | Root `data-composition-*` attributes |
| `AbsoluteFill` | Absolutely positioned HTML container |
| `useCurrentFrame()` | Paused GSAP timeline time |
| `useVideoConfig()` | Root width, height, and fps attributes |
| `interpolate()` | GSAP `fromTo`, `to`, or `set` operations |
| `Easing.bezier()` | GSAP ease approximation |
| `staticFile()` | Relative local asset path |
| Caption React component | Repeated caption HTML generated from cue data |

## Lint expectation

The installed migration lint treats these as blockers:

- React state and reducer driven animation.
- Effects with non-empty dependency arrays.
- Async metadata calculation.
- Unsupported third-party React UI libraries.

The current source inspection found no blocker patterns. `staticFile()` is an
informational migration item and must become a relative local path.

## Preserved boundaries

The migration should preserve these existing responsibilities:

- Python/faster-whisper produces word-timed transcript data.
- Caption grouping remains data preparation, not rendering.
- Presets remain the source of truth for visual defaults.
- HyperFrames owns deterministic HTML/CSS/GSAP rendering.
- ffmpeg performs the final source-video composite and copies audio.

## Phase 2 complete

- Exported the seven official presets into framework-neutral JSON.
- Added highlight, background, and stroke theme registries.
- Added deep-merge resolution with strict unknown-name handling.
- Added `auto|true|false` karaoke resolution.
- Parameterized the HyperFrames generator.
- Verified `clean`, `social-bold`, and three `shorts` highlight variants on a
  real vertical source video.

## Remaining phases

1. Compare representative Remotion and HyperFrames frames.
2. Split long generated timelines into maintainable composition chunks.
3. Update the default skill workflow only after parity verification.

## Phase 3 complete

- Added explicit `preview` and `overlay` generation modes.
- Overlay mode contains no source `<video>` or `<audio>` elements.
- HyperFrames renders the overlay as alpha-capable VP9 WebM.
- FFmpeg composites the overlay onto the source video.
- VP9 alpha WebM uses explicit `overlay=format=yuv420`; `format=auto` caused
  visible black-level lift in dark BT.709 footage.
- The final video keeps source dimensions, frame rate, duration, frame count,
  and BT.709 color metadata.
- Audio is copied from the source with `-c:a copy`; encoded audio stream hashes
  match exactly.
