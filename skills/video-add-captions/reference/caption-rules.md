# Caption rules & data shape

## How `build_captions.py` chunks words into cues
A new cue is closed when **any** of these hits (checked per word):
- the word ends a sentence — `.` `?` `!` `…` (hard break right after);
- adding the next word would exceed the **line budget** (`--max-chars` × `--max-lines`, default 42×2 = 84);
- adding it would exceed `--max-dur` seconds on screen (default 6s);
- there is a speech **gap** ≥ `--gap` seconds before the next word (default 0.6s).

Each cue keeps its **per-word timings**, so the renderer can highlight the word
currently being spoken. `lines[]` is the cue wrapped to `--max-chars` for display
and for the SRT file.

Tunables: `--max-chars 42 --max-lines 2 --max-dur 6 --gap 0.6`. For fast-cut
vertical/social captions, try shorter cues: `--max-chars 24 --max-dur 3`.

## captions.json schema
```jsonc
[
  {
    "index": 1,
    "start": 1.0,                 // seconds (first word's start)
    "end": 3.4,                   // seconds (last word's end)
    "text": "Hey, it's Thariq from the Claude Code team.",
    "lines": ["Hey, it's Thariq from the Claude", "Code team."],  // wrapped
    "words": [ { "word": "Hey,", "start": 1.0, "end": 1.2 }, ... ] // for karaoke
  }
]
```
`out/captions.srt` is the same content as portable SubRip — useful as a sanity
read, or to hand to any player / another tool.

## Styling & position (in `Caption.tsx`)
- Position: bottom-center is the default (`justifyContent:"flex-end"`, `paddingBottom`).
  For vertical video raise the padding so captions clear UI chrome.
- Readability: heavy weight + `textShadow` (or a semi-opaque pill behind the text).
- Karaoke: `karaoke` prop on. Current word → `CLAY`; not-yet-spoken words dimmed to
  `DIM`; already-spoken words full `CREAM`. Set `karaoke={false}` for plain blocks.
- One look in `anim.tsx` (palette + pop timing) so every cue matches.

## Getting the graphics INTO the video (two paths)
1. **Transparent overlay + ffmpeg (default for clips > ~1-2 min).** Render the
   `CaptionsOverlay` composition on transparent (`--codec=prores
   --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png`), then
   overlay it onto the source with ffmpeg and `-c:a copy`. Remotion only renders
   the caption layer instead of seeking/decoding the source on every frame; ffmpeg
   copies the original audio while compositing the final picture.
2. **OffthreadVideo background (simple, slow fallback).** `Captions.tsx` plays
   `source.mp4` under the captions; `remotion render` outputs the final captioned
   MP4 directly. Use this for very short clips or quick experiments.
