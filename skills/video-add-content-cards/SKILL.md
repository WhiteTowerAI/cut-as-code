---
name: video-add-content-cards
description: Use when an understood video project needs selective transcript-timed titles, lower-thirds, statistics, lists, quotes, chapter cards, or calls to action authored as HyperFrames HTML graphics.
---

# Video Add Content Cards

Turn approved semantic moments into one coherent HyperFrames graphics overlay. Use shared evidence and the canonical timeline; do not re-transcribe or re-analyze the source inside this skill.

## Inputs

- `work/project.json`: operation revisions and dependencies
- `work/understand/understanding.json`: reviewed semantic moments and evidence
- `work/timeline.json`: source-to-program mapping, or an identity timeline when no rough cut exists
- optional selected color-grade revision when contrast or palette is judged against that look

The skill is valid without rough cut or color grade. Declare only dependencies actually consumed and record their current revisions in `based_on`.

## Working Files

```text
work/content-cards/cards-plan.json          # durable editorial plan
work/cache/content-cards/index.html         # code-is-the-edit composition
work/cache/content-cards-overlay.mov        # transparent render contribution
review/03-content-cards/card-stills/        # one useful still per card
review/03-content-cards/content-cards-preview.mp4  # optional short cue windows
review/03-content-cards/content-cards-summary.md
```

Keep the plan outside `cache/`. It must contain every visible string, timing, placement,
visual-treatment value, renderer composition path, renderer asset path, and source FPS needed
to regenerate the disposable HTML and alpha assets after deleting `work/cache/`. Record one
plan-level `renderer_recipe` with the source example/template, composition output path, render
engine, and every local runtime asset's output path, exact version, origin, and SHA-256. A
cached HTML file or downloaded script with no durable recipe does not satisfy regeneration.

## Workflow

### 1. Draft cards from shared understanding

```powershell
python skills/video-add-content-cards/scripts/build_cards_plan.py `
  work/understand/understanding.json `
  work/timeline.json `
  work/content-cards/cards-plan.json
```

The script maps kept semantic moments into program time and omits moments removed by rough cut. It preserves source ranges and evidence references, clamps duration to the containing clip, and marks copy/placement/visual treatment as `draft`.

### 2. Make editorial choices

Read the evidence at each card time. Correct ASR names and numbers, prune weak candidates, write concise copy, choose placement that clears faces and captions, and approve the visual treatment. Never treat analyzer text as final copy.

Store all on-screen copy under `copy.display` (for example `eyebrow`, `title`, and `detail`),
not only a summary or suggested title. Set `placement.face_clearance` to `verified` only after
reviewing a composited still, and store that still's protocol-relative path in
`placement.review_still`. Store the HyperFrames composition, alpha asset, and exact rational
FPS under `renderer`.

Use these mappings as a starting point:

| Semantic kind | Card type |
|---|---|
| hook | intro |
| key-point, quote, question | key-quote |
| stat | stat |
| list | list |
| cta | outro |

`repetition`, `tangent`, and `risk` are editorial evidence, not automatic cards.

### 3. Author one HyperFrames composition

Use one `index.html` and a paused GSAP timeline. Each approved card becomes one `.clip` keyed by the plan's `program_start_s` and `duration_s`. Keep motion seek-safe and derive timing from data attributes rather than wall-clock timers.

Start from the closest repository example:

- `examples/index-almanac.html`
- `examples/index-apex.html`
- `examples/index-dotgrid.html`
- `examples/index-editorial.html`
- `examples/index-teal.html`

Keep one visual language across all cards. Use edge anchoring, a card or scrim for legibility, source-relative sizing, and enough contrast against the selected grade. Do not cover the speaker or captions.

Pass the source FPS explicitly; preserve fractional rates such as `24000/1001` rather than
rounding to 24 or 30. On Windows use `npx.cmd`, a project-local npm cache, and local assets:

```powershell
$env:npm_config_cache = "$PWD/work/cache/npm"
npx.cmd hyperframes lint
npx.cmd hyperframes validate
```

Do not depend on remote fonts, images, scripts, or styles at render time.

The approved plan must preserve the exact style and motion values used by the composition,
not prose labels such as `edge-slide` alone. At minimum record panel geometry and padding,
colors, borders, type sizes/weights/line heights, and the enter/rule/text/exit durations,
offsets, staggers, and easing. This makes the creative HTML reproducible from the plan rather
than a hidden decision stored only in disposable cache.

### 4. Review small artifacts

Capture a still near the middle of every cue by compositing the card over the actual base-video
frame at that timestamp. Transparent-only HyperFrames screenshots prove alpha, not face
clearance, and are insufficient for approval. Render short motion windows only for timing or
transition decisions. Do not render a full preview by default.

Check:

- copy is true to its `evidence_ref`;
- source and program times map correctly;
- text is legible and fits;
- faces and captions remain clear;
- animation lands on the spoken phrase;
- alpha is transparent outside card regions.

Every approved cue must have a matching composited still in
`review/03-content-cards/card-stills/`, `face_clearance: "verified"`, and the still path in
the plan. Record the review result in `review/03-content-cards/content-cards-summary.md`.

### 5. Render the transparent contribution

Prefer one short alpha MOV per cue so a few seconds of graphics do not create a full-program
transparent video. Render each at the source dimensions and exact source FPS, then declare a
render contribution with its program-time window. A single full-length sparse overlay remains
valid only when it is demonstrably smaller or required by the composition.

Record this operation contribution in `project.json`:

```json
{
"target": {"sequence": "main", "scope": "graphics"},
"effects": {
  "changes_timeline": false,
  "changes_geometry": false,
  "changes_video_pixels": false,
  "changes_audio": false,
  "adds_track": "graphics"
},
"check": {
  "status": "pass",
  "report": "../review/03-content-cards/content-cards-summary.md"
},
"render": [
  {
    "kind": "overlay",
    "asset": "cache/content-cards/card-001.mov",
    "start_s": 12.5,
    "duration_s": 4.0
  }
]
}
```

The shared renderer offsets each short clip to `start_s`, limits it to `duration_s`, and
composites it after base-video grading. Keep the operation's `outputs` and each card's
`renderer.asset` consistent with these declared assets.

Set the operation to `approved` or `verified` only after card review and update its integer `revision` when the plan, timing, or selected input changes. The shared renderer performs the final composite after all active operations pass `based_on` checks:

```powershell
python skills/video-understand/scripts/build_render_plan.py .
python skills/video-understand/scripts/render_project.py work/render/render-plan.json
```

## Combining With Captions

Treat captions and cards as separate overlay contributions. Resolve their placement conflict before rendering, then composite them in declared sequence in the shared delivery pass. Keep captions at the bottom and move cards to the top when both would occupy the same safe area.
