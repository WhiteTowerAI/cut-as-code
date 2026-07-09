# Caption Rules and Data Shape

## How build_captions.py chunks words into cues

A new cue is closed when any of these conditions is met:

- the word ends a sentence: `.`, `?`, `!`, or ellipsis
- adding the next word would exceed the line budget: `--max-chars` x `--max-lines`
- adding the next word would exceed `--max-dur` seconds on screen
- there is a speech gap of at least `--gap` seconds before the next word

Each cue keeps per-word timings, so the renderer can highlight the word currently
being spoken. `lines[]` is the cue wrapped to `--max-chars` for display and for
the SRT file.

Useful defaults:

```text
--max-chars 42 --max-lines 2 --max-dur 6 --gap 0.6
```

For fast-cut vertical/social captions, try shorter cues:

```text
--max-chars 24 --max-dur 3
```

## captions.json schema

```jsonc
[
  {
    "index": 1,
    "start": 1.0,
    "end": 3.4,
    "text": "Hey, it's Thariq from the Claude Code team.",
    "lines": ["Hey, it's Thariq from the Claude", "Code team."],
    "words": [
      { "word": "Hey,", "start": 1.0, "end": 1.2 }
    ]
  }
]
```

`out/captions.srt` is the same content as portable SubRip. Use it as a sanity read
or to hand to a player or another tool.

## Styling and Position

- Style is selected through `caption-style.ts`: choose an official preset and optional
  overrides, then let `Caption.tsx` render the resolved style.
- Preview candidates live in `preview-config.ts`; use them to compare styles before
  writing the final choice to `caption-style.ts`.
- Karaoke is a true/false option, not a preset. Use `karaoke: true` for per-word
  highlight and `karaoke: false` for plain blocks.
- Do not edit `Caption.tsx` or `anim.tsx` for ordinary user style feedback.

## Getting the Graphics Into the Video

1. Transparent overlay plus ffmpeg is the default for clips longer than about
   1-2 minutes. Render the `CaptionsOverlay` composition on transparent
   (`--codec=prores --prores-profile=4444 --pixel-format=yuva444p10le
   --image-format=png`), then overlay it onto the source with ffmpeg and
   `-c:a copy`. Remotion only renders the caption layer instead of decoding the
   source on every frame.
2. `OffthreadVideo` background is the simple, slow fallback. `Captions.tsx` plays
   `source.mp4` under the captions, and `remotion render` outputs the final
   captioned MP4 directly. Use it for very short clips or quick experiments.
