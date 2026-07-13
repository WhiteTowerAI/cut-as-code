# Graphic types — cue → HTML scene + GSAP entrance

`analyze_content.py` (reused from `video-to-remotion`) scans the transcript and
emits *opportunities*; `draft_cues.py` maps each to a cue with `at`/`dur`/`props`
and writes `work/cues.json`. This skill turns each cue into an HTML **scene** (a
`.clip` div) plus a GSAP **entrance**, all on one paused timeline. The analyzer
output is framework-agnostic — the only difference from `video-to-remotion` is
the render target below.

| type          | what triggers it (in the content)                             | scene id / layout          | props → HTML                          | entrance |
|---------------|---------------------------------------------------------------|----------------------------|---------------------------------------|----------|
| `lower-third` | a self-introduction — "I'm X", "it's X from Y"                | `.lt` solid card, anchor-bl | `line1`→`.line1`, `line2`→`.line2`    | card fade; line1 clip-wipe, line2 rise |
| `stat`        | a number worth flagging — `%`, `$`, `3x`, ≥10                 | `.stat` card, anchor bottom-right | `value`→`data-stat-value`, `label`→`.label` | card fade; value counts 0→N; label rise |
| `list`        | an enumeration — "three ways", "first … second …"            | `.list` scene, anchor-bl    | `items[]`→numbered rows (`01/02/…`)   | rows rise, staggered per index |
| `keypoint`    | a question or punchy line worth pinning                       | `.key` card, anchor-bl      | `text`→card body                      | card fade; text clip-wipe |
| `section`     | a topic boundary — a long pause (≥1.8s) and/or a scene cut     | `.section` fullBleed, anchor-bl | `kicker`→`.kicker`, `title`→`.title` | kicker rise, title clip-wipe, rule bar draws |

**Hand-placed (no detector):** `Intro` (fullBleed) over the cold open and `Outro`
(fullBleed, centered diamond + wordmark) over the sign-off — same as
`video-to-remotion`. Write these directly into the composition.

## The cue → scene translation

Each `work/cues.json` entry becomes one `.clip` scene div plus timeline calls.
The example `index.html` is the worked template; copy a scene block and refill it.

**1. The scene div** carries the cue's window in seconds (the runtime shows/hides
it by these — do NOT gate visibility with CSS `opacity:0`):
```html
<div id="lt" class="scene anchor-bl clip"
     data-start="12" data-duration="6" data-track-index="1"> … </div>
```
- `at` → `data-start`, `dur` → `data-duration` (both seconds; `draft_cues.py`
  already emits seconds).
- `data-track-index`: fullBleed takeovers on 0, cards that ride footage on 1.
  Bottom cards + captions collide — see SKILL.md "Combining with captions".

**2. The entrance** is GSAP on the single paused timeline, offset to `data-start`.
Reuse the three helpers in the template:
- `titleIn(el, at)` — clip-path wipe L→R + fade (headline reveal).
- `riseIn(el, at)` — fade + translateY(1.2vh→0) (kicker / sub / list rows / labels).
- `sceneFade(innerSel, start, dur)` — fade the scene's INNER wrapper in/out.
- count-up (stat): tween a `{v:0}` counter, write `textContent` on `onUpdate`.

Stagger beats: kicker@0, title@1×STAG, rule/sub@2–3×STAG (STAG = 0.167s @24fps).

## Two seek-safety rules (the HF linter enforces both)

1. **Fade an inner wrapper, never the `.clip` div.** The runtime owns clip
   visibility; animating opacity on the clip leaves stale state on non-linear
   seeks (`gsap_exit_missing_hard_kill`). Every scene has an inner div for this.
2. **Animate transforms with `fromTo`, not `to`, when CSS sets the initial
   value** (`scaleX`, `rotate`) — otherwise GSAP clobbers the whole transform
   (`gsap_css_transform_conflict`). The rule-bar draw is the worked example.

Run `npx hyperframes lint` after editing — it catches both.

## content.json / cues.json schema

Identical to `video-to-remotion` (same Python). `content.json`:
```jsonc
{
  "duration_s": 70.0, "fps": 24, "n_opportunities": 7,
  "opportunities": [
    { "type": "lower-third", "at": 1.2, "dur": 4.5,
      "props": { "name": "Jordan Reyes", "org": "Field Research" },
      "quote": "it's Jordan from the Field Research team" }
  ]
}
```
`draft_cues.py` then de-stacks, clamps durations, and writes `cues.json` (an
array of `{id, component, at, dur, props}`). The `component` field names the
`video-to-remotion` Remotion component; here it just tells you which scene layout
to use (the table above maps it).

## Notes on the heuristics
- **Detection is a draft, not a verdict.** Read each `quote`; prune the noise;
  WRITE the copy (line2 gloss, chapter titles, list items) — don't paste raw
  transcript. Fix ASR-garbled names (verify a headline name/brand online).
- `list` items come back empty (the analyzer only knows the count) — fill them.
- `section` titles are trimmed transcript fragments — rewrite into real labels.
- To re-theme: change the 5 CSS vars + the fonts `<link>` in `index.html`. A
  structurally new look (different card shape) is new CSS + a new scene block.
