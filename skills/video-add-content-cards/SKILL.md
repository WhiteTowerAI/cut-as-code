---
name: video-add-content-cards
description: Use when an understood video project needs selective transcript-timed titles, lower-thirds, statistics, lists, quotes, chapter cards, or calls to action authored as HyperFrames HTML graphics.
---

# Video Add Content Cards

Turn approved semantic moments into one coherent HyperFrames graphics overlay. Use shared evidence and the canonical timeline; do not re-transcribe or re-analyze the source inside this skill.

## Dependencies

`/video-understand` is a prerequisite. Run it first so cards use validated
semantic evidence and the canonical timeline.
Before starting, verify that it is installed. If it is not, warn the user that
this prerequisite is missing and stop before processing media.

Require `ffmpeg` on PATH, Python, and Node.js >= 22 (for `npx hyperframes`, fetched on demand). `hyperframes render`/`snapshot` drives a headless Chrome — it manages its own `chrome-headless-shell`, and falls back to a system Chrome (set `CHROME` to override) when the cached one is unusable. Check these before processing media.

## Inputs

- `work/project.json`: operation revisions and dependencies
- `work/understand/understanding.json`: reviewed semantic moments and evidence
- `work/timeline.json`: source-to-program mapping, or an identity timeline when no cut exists
- optional selected color-grade revision when contrast or palette is judged against that look

The skill is valid without a cut or color grade. Declare only dependencies actually consumed and record their current revisions in `based_on`.

## Working Files

```text
work/content-cards/cards-plan.json          # durable editorial plan
work/cache/content-cards/index.html         # code-is-the-edit composition
work/cache/content-cards-overlay.mov        # transparent render contribution
review/03-content-cards/card-stills/        # one useful still per card
review/03-content-cards/content-cards-preview.mp4  # optional short cue windows
review/03-content-cards/content-cards-summary.md
review/03-content-cards/content-cards-review.html  # local candidate review board
review/03-content-cards/content-cards-review-assets/  # one source frame per candidate
review/03-content-cards/content-cards-review.json  # validated human choices
```

The reusable review page is committed at
`skills/video-add-content-cards/assets/content-cards-review.html`.
The populated HTML, screenshots, overlay, and preview renders are reproducible.
Keep the plan outside `cache/`. It must contain every visible string, timing, placement,
visual-treatment value, renderer composition path, renderer asset path, and source FPS needed
to regenerate the disposable HTML and alpha assets after deleting `work/cache/`. Record one
plan-level `renderer_recipe` with the source example/template, composition output path, render
engine, and every local runtime asset's output path, exact version, origin, and SHA-256. A
cached HTML file or downloaded script with no durable recipe does not satisfy regeneration.

## Workflow

### 1. Interview before drafting

Read `understanding.json` and the active timeline first. Count eligible graphic moments and
calculate the target card count recommendation before interviewing:

```text
min(eligible moments, max(1, round(program minutes / 0.75)))
```

This is a target, not an automatic truncation rule. Before asking any question, open the real
animated examples yourself with the native command for the current OS. Run exactly one:

```powershell
# Windows PowerShell
Start-Process (Resolve-Path 'skills/video-add-content-cards/examples/gallery-animated.html')
```

```bash
# macOS
open skills/video-add-content-cards/examples/gallery-animated.html

# Linux desktop
xdg-open skills/video-add-content-cards/examples/gallery-animated.html
```

If the command fails, diagnose and retry it. Do not replace this action with a URI or ask the
user to find and click the file. The gallery compares all five themes and can focus one column
with its native picker:

| Theme | Starting character |
|---|---|
| `almanac` | warm cream, serif, considered |
| `teal` | dark broadcast, cyan accent |
| `editorial` | documentary, ink and amber |
| `dotgrid` | pixel-mono, technical |
| `apex` | high-energy sports, red accent |

Ask exactly one question at a time in this order:

1. Which theme should this edit use?
2. What target card count should this edit use? Offer the calculated recommendation as default.
3. Which card types must be included? Offer `intro`, `key-quote`, `stat`, `list`, and `outro`;
   default to none.

**Present + STOP** after each question. After the third answer, summarize the theme, target
count, required types, and any user-supplied notes; ask for confirmation. If the user cancels,
retain analysis, leave the operation `draft`, and do not author or render cards.

### 2. Draft cards from shared understanding

```powershell
python skills/video-add-content-cards/scripts/build_cards_plan.py `
  work/understand/understanding.json `
  work/timeline.json `
  work/content-cards/cards-plan.json `
  --target-card-count 6 `
  --theme editorial `
  --must-include-type stat `
  --notes "Keep product names verbatim"
```

The script maps kept semantic moments into program time and omits moments removed by the cut. It preserves source ranges and evidence references, clamps duration to the containing clip, and marks copy/placement/visual treatment as `draft`.
The confirmed interview is stored as `brief` in `cards-plan.json`. Repeat
`--must-include-type` for multiple values; omit flags that do not apply. Older optional brief
fields remain accepted for compatibility but are not part of the normal interview.

### 3. Make editorial choices

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

Keep all evidence-backed candidates at this stage. Aim for the brief's target card count, but
allow a stronger or sparser set when the evidence warrants it.

### 4. Review and apply candidate choices

Generate a project-specific browser review after the candidate plan exists. Pass the source
video aligned to the plan's `source_range` and the active timeline. The script clamps each
evidence midpoint to its containing retained clip, then populates the committed template with
one corresponding source frame per candidate:

```powershell
python skills/video-add-content-cards/scripts/build_review_page.py `
  work/content-cards/cards-plan.json `
  review/03-content-cards/content-cards-review.html `
  --video input/source.mp4 `
  --timeline work/timeline.json
```

Immediately open the populated review yourself with the native command for the current OS.
Run exactly one:

```powershell
# Windows PowerShell
Start-Process (Resolve-Path 'review/03-content-cards/content-cards-review.html')
```

```bash
# macOS
open review/03-content-cards/content-cards-review.html

# Linux desktop
xdg-open review/03-content-cards/content-cards-review.html
```

If the command fails, diagnose and retry it; do not ask the user to locate the file. The page
shows each source frame, card ID, program time, editable copy, and placement. Every candidate
starts unselected with placement set to `bottom`. Changing placement moves a gray card proxy
over the real frame so collision risk is visible before approval. The user selects cards,
edits copy, chooses placement, clicks **Copy summary**, and pastes the visible summary back
into the conversation.

**Present + STOP.** Wait for the pasted selection summary. Do not author HTML from unchecked
draft candidates. Convert the summary into
`review/03-content-cards/content-cards-review.json`: write one entry for every plan card, mark
summary IDs selected with their chosen copy and placement, and mark all other IDs unselected
with their current draft copy and an empty placement. Then apply the validated review:

```powershell
python skills/video-add-content-cards/scripts/apply_cards_review.py `
  work/content-cards/cards-plan.json `
  review/03-content-cards/content-cards-review.json
```

The apply step rejects unknown, duplicate, or missing card IDs, blank selected copy, and
invalid placement without changing the plan. On success it keeps selected cards and marks
their copy, placement, visual treatment, and top-level review `approved`. Read the resulting
selected count against the brief target before continuing.

### 5. Author one HyperFrames composition

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

### 6. Review small artifacts

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

**Present + STOP.** Show the card stills and any short motion windows, name the card IDs, and
wait for approval. Do not render the full overlay while copy, placement, or timing is disputed.

Every approved cue must have a matching composited still in
`review/03-content-cards/card-stills/`, `face_clearance: "verified"`, and the still path in
the plan. Record the review result in `review/03-content-cards/content-cards-summary.md`.

### 7. Render the transparent contribution

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
