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

## Expressive Planning

Standard is the default. A Standard canonical plan needs no `presentation` field,
and the legacy top-level cue array remains Standard-compatible. Expressive must be
explicitly requested with `--presentation-mode expressive`; it is a presentation
mode, not a preset.

`build_captions.py` creates only the base cues and a draft planning shell. It does
not infer placement. The Agent reads the transcript,
available understanding artifacts, timeline, generated cues, and necessary real
visual evidence, then fills the complete plan once for the whole program.

Agent layout rules:

1. Default to `bottom-standard`.
2. Keep ordinary explanatory sentences in a continuous bottom layout when possible.
3. Use `center-emphasis` for short keywords, numbers, or conclusions when emphasis is justified.
4. Do not mechanically alternate between bottom and center.
5. Do not change position in the middle of a sentence or cue.
6. Prefer merging adjacent ordinary cues into one stable layout beat.
7. Avoid repeated consecutive `center-emphasis` beats.
8. Every position change must have a semantic reason recorded in the beat rationale.
9. When uncertain, fall back to `bottom-standard`.

A layout beat covers one or more complete, contiguous cues. Beat IDs must be unique;
beats must follow time and cue order, must not overlap, and must not start or end
inside a cue. A completed Expressive plan covers every cue exactly once and contains
one whole-program Agent rationale plus a non-empty rationale for every beat.

The supported word roles are `normal`, `keyword`, `number`, and `contrast`. A missing
`semantic_role` is interpreted as `normal`. Semantic role is independent of the
existing karaoke `upcoming`, `active`, and `completed` playback states.

The renderer applies the approved layout beat for the complete cue: familiar lower
placement for `bottom-standard` or the central safe region for `center-emphasis`.
It never infers a variant or changes position inside a beat. A plan containing the
removed `top-statement` variant must be rejected and replanned; it must not be
silently remapped. In Expressive mode, non-`normal` semantic roles remain visibly
emphasized for the full cue; Standard ignores semantic-role styling.

Expressive supports two stable configurations. `semantic-only` uses Expressive
with Karaoke off. `semantic-plus-karaoke` keeps the same full-cue semantic emphasis
while the existing upcoming, active, and completed Karaoke states progress. In
coexistence mode, semantic emphasis and the active Karaoke word both use
`style.wordHighlight.activeColor` as their foreground color, even when
`wordHighlight.mode` is `background`; the configured background remains an
additional effect. The effective scale is the larger of semantic scale and Karaoke
active scale, never their product.

Expressive never renders an underline in either configuration. The compatible
`contrast` semantic role may use color, scale, glow, or another non-underline
treatment.

Standard HTML review keeps exactly `early`, `middle`, `late`, and `no-caption`.
Expressive HTML review uses one source-backed primary sample per layout beat plus
`no-caption`; the coexistence comparison is hash-bound separately and does not
increase the primary approval count.

Run `python scripts/build_captions.py --validate-plan <captions-plan.json>` after
Agent planning and before preview generation. `generate_caption_project.mjs` repeats
the Expressive validation as a generation guard. Generate preview evidence only
after this validation passes.
