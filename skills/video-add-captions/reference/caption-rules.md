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

`captions.srt` is the same content as portable SubRip. Use it as a sanity read
or to hand to a player or another tool.

## Renderer Contract

- Treat `captions.json` as renderer-neutral cue data.
- Preserve `start`, `end`, `text`, `lines[]`, and per-word timings when passing cues
  to a renderer.
- Karaoke is a true/false option, not a preset. Use `karaoke: true` for per-word
  highlight and `karaoke: false` for plain blocks.
- Keep style and compositing implementation outside this data-shaping contract.
