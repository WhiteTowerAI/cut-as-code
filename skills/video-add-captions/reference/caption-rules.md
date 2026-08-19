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

The maintained semantic scales are `normal=1.0` and
`keyword=number=contrast=1.22`. These values live in
`caption-styles.json.expressiveTreatments`, not in a preset or renderer constant.

## Hero-line phrase emphasis

`hero_line` is one optional phrase-level capability on an Expressive cue. It is
not a presentation mode or preset. Canonical `hero` renders one contiguous phrase
as a gold `#F4C542` line at `1.5` times the normal cue size. Legacy `strong` is
accepted only as a compatibility input and renders identically at `1.5`; new
Agent-authored plans use only `hero`. A cue may contain at most one hero line:

```json
{
  "hero_line": {
    "level": "hero",
    "word_indexes": [2, 3],
    "rationale": "The single conclusion phrase carries the strongest hierarchy."
  }
}
```

`word_indexes` are 1-based, unique, ascending, contiguous, and within the cue's
`words[]`. The rationale is required non-empty single-line text. Standard plans,
legacy cue arrays, cross-cue phrases, non-contiguous words, and a `hero_lines`
array are invalid. Hero words may retain `semantic_role` for explanation, but the
hero level owns their base scale; semantic and hero scales are never multiplied.
With Karaoke, the effective scale remains `max(hero scale, Karaoke active scale)`
and the word remains gold in upcoming, active, and completed states.

Hero lines use `white-space: nowrap` and never shrink or wrap automatically. The
review builder must reject clipping or an alpha bbox that reaches the horizontal
edge of its allowed region. Shorten the phrase, split the cue at a valid word gap,
or remove the hero line; never silently shrink, wrap, or downgrade it.

## Composite-aware placement

Composite-aware captions consume an already approved B-roll speaker-inset
composition without changing or reselecting it. Preset, presentation mode, and
resolved placement remain separate:

| Visual context | Standard | Expressive `bottom-standard` | Expressive `center-emphasis` |
|---|---|---|---|
| A-roll | `preset-bottom` | `preset-bottom` | `frame-center` |
| `focused-panel` | `panel-center` | `panel-center` | `panel-center` |
| `full-bleed-wash` | `preset-bottom` | `preset-bottom` | `frame-center` |
| `corner-pip` | `preset-bottom` | `preset-bottom` | `frame-center` |

`panel-center` and `panel-bottom` are resolved placements, not Expressive layout
variants. `panel-center` anchors to the center of the maintained focused panel rect
`{x:0.04,y:0.08,width:0.92,height:0.40}`. `panel-bottom` is a boundary-only fallback:
when an `unsplittable_word_boundary` touches a lower-center focused panel, center
the stable cue in the reserved strip between the structured speaker rect bottom
and the frame's maintained 4% safe margin. `preset-bottom` preserves the selected
preset's existing `paddingBottomRatio`; do not move `shorts` globally and do not
create layout-specific combination presets.

Before Expressive planning, run `caption_spatial_context.py align`. For every
B-roll start/end boundary strictly inside a cue, split at the nearest gap between
complete words. Derived cues rebuild text, lines, program/source ranges and
indexes, retain `original_cue_id`, and bind original/derived word signatures. If
the boundary falls inside a word, keep the complete word, record its midpoint side
as provenance, add `unsplittable_word_boundary`, and force evidence on both sides.
Midpoint ownership is not the collision model: record every visual context and
structured rectangle intersected by the cue. Never split a word or switch placement
inside a cue. If either side is a lower-center focused panel, resolve the whole
stable cue to `panel-bottom`; other unsplittable boundaries retain their existing
placement unless an actual sampled context reports a structured collision.

After final cue IDs and Expressive layout beats exist, `build` emits
`caption-spatial-context.json`; `attach` adds this optional plan binding:

```json
{
  "spatial_context": {
    "policy": "composite-aware",
    "path": "captions/caption-spatial-context.json",
    "sha256": "<64 lowercase hex>",
    "source_operation": "b-roll",
    "source_revision": 4
  }
}
```

The context binds the active B-roll operation/revision/status, reviewed B-roll
plan, speaker-inset analysis, Agent input, preview, clearance, and every normalized
composite by SHA-256. It records `cue_alignment` and ordered, non-overlapping
`placement_beats` that cover every aligned cue exactly once. `approved` with
`check.status=pending` remains `approved`; captions must not report it as an
upstream `verified` result. Any source revision, file hash, context, cue, placement,
review payload, or project-metadata change invalidates preview approval.

Composite-aware review densely samples only placement beats with a composite
background, plus B-roll visual boundaries, every hero-line cue, every
unsplittable word boundary, the maintained base evidence,
and a no-caption frame. B-roll samples use the hash-bound normalized composite at
`program_s - program_start_s`, never the raw A-roll source. Alpha-bbox clearance
must keep `panel-center` and `panel-bottom` inside their `allowed_rect`, compare
every visible caption bbox with the actual sampled context's structured speaker
rect, and reject hero-line clipping before approval. Boundary lookup uses integer
frame identity and the exact rational timeline FPS. A frame-aligned rounded decimal
boundary is snapped to its frame; otherwise the first active frame is the first
frame at or after the half-open interval start.

Standard HTML review keeps exactly `early`, `middle`, `late`, and `no-caption`.
For Expressive or composite-aware review, `samples` remains the exhaustive machine
set and `review_samples` references a compact human set. Human categories are
`bottom-standard`, `center-emphasis`, `preset-bottom`, `frame-center`,
`panel-center`, and `hero-1.5x`; each present category appears at most once, one PNG
may carry several categories, absent categories are not invented, and there are at
most six unique representative PNGs. `no-caption`, dense spatial purposes, visual
boundaries, and unsplittable-boundary samples remain machine-only. The two Karaoke
comparison PNGs are hash-bound separately and do not increase the representative
count. The receipt binds representative PNG hashes and the complete
`captions-evidence.json` hash, so changing hidden machine evidence invalidates
approval. Standard without spatial context remains exactly `early`, `middle`,
`late`, and `no-caption`.

Formal Expressive overlay generation preserves that distinction in the canonical
plan. `review.representative_evidence` lists only the Human-visible representative
PNGs. `review.evidence` remains the shared delivery compiler compatibility field and
contains one hash-bound `layout-beat` machine sample per planned layout beat plus the
single `no-caption` sample. `review.machine_evidence_document` records the complete
document path, SHA-256, and sample count. These compatibility entries are not extra
human-review claims.

Run `python scripts/build_captions.py --validate-plan <captions-plan.json>` after
Agent planning and before preview generation. `generate_caption_project.mjs` repeats
the Expressive validation as a generation guard. Generate preview evidence only
after this validation passes.
