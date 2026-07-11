---
name: video-add-hyperframes
description: >
  Watch a video's own content and auto-generate the HyperFrames (HTML + GSAP)
  motion-graphics it needs — no designer frames, no React. Transcribe the video
  word-by-word, scan the transcript (and scene cuts) to surface graphic
  *opportunities* (intro/outro title card, chapter card, speaker lower-third, stat
  callout, enumerated list, key-quote), then write ONE index.html: a paused GSAP
  timeline of scene divs, all on one design language (each rides a scrim/card,
  edge-anchored so it never covers the face, sized in vh so it reads at any
  resolution) with *editorial copy* written from the content (ASR-garbled names
  corrected). Render a transparent overlay at the source's own size, ffmpeg-composite
  it onto the source while copying audio, and screenshot stills to self-review. This
  is the HyperFrames sibling of video-to-remotion (same content-driven, code-is-the-edit
  pipeline; the edit is HTML you write instead of React). Use when asked to
  "auto-generate HyperFrames graphics from this video", "watch the video and add the
  graphics it needs as HTML", "turn this talking-head into a HyperFrames motion-graphics
  cut", 用 hyperframes 根据视频内容自动生成动态图形, 把视频做成 HTML 动画叠层. NOT for cutting
  footage (rough-cut), plain every-line subtitles (captions), designer-supplied PNG
  frames (design-frames-to-motion), or the React/Remotion version (video-to-remotion).
---

# Video → Auto-Generated HyperFrames Graphics

Point this at a talking-head / podcast / explainer and it **reads the content**
to decide which motion graphics the video wants, then **writes them as one
HyperFrames `index.html`** — a paused GSAP timeline of scene divs, each timed to
land on the spoken word. Same idea as `video-to-remotion`, but the edit is
**HTML + GSAP you write**, not React components you compile. No bundler, no
`react`/`react-dom` pinning — the composition plays as-is and renders to video.

## The one idea
**The video is the brief.** Graphic decisions come from the transcript (and scene
cuts), not a storyboard. The analyzer proposes opportunities; you prune them; each
survivor becomes a scene div + a GSAP entrance on one timeline. The edit stays
text — an HTML file you can read, diff, and re-render.

**One design language.** The overlays sit on REAL footage, so every scene: rides
its OWN background (a **scrim** or a **solid card**, or a **fullBleed** opaque
takeover) so it's legible on any picture; is **edge-anchored** (bottom by default —
the lower-third safe zone; flip to top to clear captions) so it never covers the
face; and is sized in **vh** so it reads at any resolution. One accent color,
~0.3s fades. The shipped look is **almanac** (cream cards, Newsreader serif,
terracotta-coral) — re-theme by changing 5 CSS vars + the font `<link>`.

## Relationship to video-to-remotion
This skill **reuses that skill's Python pipeline verbatim** (transcribe / analyze /
draft_cues / probe) — the transcript and `cues.json` are framework-agnostic
interchange formats. Only the render target differs: HTML+GSAP here, React there.
The 5 themes and card catalog documented in `video-to-remotion/SKILL.md` are the
design reference; this skill ports the **almanac** look as the worked example.

## When to use
- A finished/near-finished video needs on-screen graphics derived from its
  content, authored as **HTML** (agents iterate HTML faster than React/Remotion).
- The ask names HyperFrames / HTML, or "add the graphics as an HTML overlay".
- NOT for: cutting footage (rough-cut); plain every-line subtitles (captions);
  designer-supplied frames (design-frames-to-motion); the React version
  (video-to-remotion — same output, different framework).

## Dependencies
- **Node** (HyperFrames CLI via `npx hyperframes`) + **ffmpeg**. GSAP loads from a
  CDN `<script>` (HF inlines it at render). Fonts load via a Google Fonts `<link>`
  (HF inlines them too) or a self-hosted `@font-face`.
- **Python + faster-whisper** for the transcript — reuses
  `../video-rough-cut/scripts/transcribe.py` (segments → words with start/end).
  Default model is English-only (`base.en`); other languages pass a multilingual
  model + `--lang`.
- The analyzer/cue scripts are reused by relative path from `video-to-remotion`
  (no copy): `../video-to-remotion/scripts/analyze_content.py`, `draft_cues.py`,
  `probe.py`.
- ffmpeg for scene detection (optional; single-shot talking-heads often find 0).

### Windows / rendering gotcha (READ FIRST if render fails)
If `hyperframes render` / `snapshot` fail with **`spawn EFTYPE`** ("Exec format
error"), the cached `chrome-headless-shell.exe` download is corrupt/truncated
(check its size — a good one is ~200 MB, a bad one ~60 MB). `hyperframes lint`
and `validate` still work because they launch Chrome differently. Two fixes:
- **Repair HF's browser (primary):** `npx hyperframes browser ensure --force`
  purges and re-downloads it (slow on a thin link — may need a couple of tries;
  an `EPERM unlink` at the end is harmless if the new binary is full-size). This
  clears the EFTYPE error. On a **RAM-starved** box (software rendering, <2 GB
  free) the native render can then still stall with `Network.enable timed out` at
  the 5-min protocol cap — bump it (`--protocol-timeout 1200000`) and/or free RAM,
  or use the bypass below. Add `--low-memory-mode` on <8 GB RAM regardless.
- **Bypass it (offline / can't re-download):** `examples/shoot.mjs` drives the
  real installed system Chrome via `puppeteer-core` for the self-check stills; for
  the final video, render a PNG sequence the same way and ffmpeg-composite it. The
  harness mimics the runtime (windows each `.clip` by `data-start`/`data-duration`,
  toggles `visibility`) so a broken composition can't hide behind it.

## Working layout
```
work/source.mp4          # the video
work/transcript.json     # word-level timestamps (video-rough-cut/transcribe.py)
work/scenes.txt          # optional: one scene-cut timestamp per line (ffmpeg)
work/content.json        # detected graphic opportunities (analyze_content.py)
work/cues.json           # draft cue sheet (draft_cues.py)
index.html               # *** THE COMPOSITION *** (scene divs + one GSAP timeline)
out/graphics-overlay.mov # transparent overlay (or a PNG sequence)
out/final.mp4            # THE DELIVERABLE
```
The worked composition is `examples/index-almanac.html` (almanac, 5 core cues). The
self-check harness is `examples/shoot.mjs`.

## The pipeline (6 steps)

### 1. Transcribe the video (word level)
```
ffmpeg -y -i work/source.mp4 -ac 1 -ar 16000 work/audio16k.wav
python ../video-rough-cut/scripts/transcribe.py work/audio16k.wav work/transcript
```
Already ran `video-rough-cut`? Reuse its `work/selfcheck/cut_transcript.json` as
`work/transcript.json` and skip this (~15–20 min CPU saved).

### 2. (Optional) Detect scene cuts
On Windows/PowerShell the bash `grep`/`sed` one-liner won't run — capture ffmpeg's
`showinfo` to a file and parse `pts_time` with Python.

### 3. Analyze the content → opportunities
```
python ../video-to-remotion/scripts/analyze_content.py work/transcript.json work/content.json --scenes work/scenes.txt
```
Surfaces `lower-third / stat / list / keypoint / section` opportunities, each with
a word-accurate `at`, suggested `dur`, draft `props`, and the `quote` it came
from. **Detection is a draft** — read each `quote` and decide what earns screen time.

### 4. Draft the cue sheet
```
python ../video-to-remotion/scripts/draft_cues.py work/content.json work/cues.json
```
Writes `work/cues.json` (de-stacked, durations clamped). See
`reference/graphic-types.md` for the cue → scene mapping.

### 5. Write index.html (copy + scenes)
Start from `examples/index-almanac.html`. For each kept cue, add/refill a scene div and
its GSAP entrance (`reference/graphic-types.md` has the per-type table + the
cue → HTML pattern). The real work is the **copy**, not the markup:
- **Write, don't paste.** A lower-third is `line1` (the entity) + `line2` (a
  one-line editorial gloss you write). Chapter titles and list items are rewritten
  from the transcript, not raw fragments.
- **Get names right.** `base.en` mangles proper nouns — correct from context;
  **verify a headline name/brand online** if it's the intro card.
- **Ground every scene** in what's said at its `at` — nothing invented.
- Place **Intro** over the cold open, **Outro** over the sign-off (hand-placed).
- Set the stage `data-width`/`data-height`/`data-fps`/`data-duration` to the
  source (read it from `video-to-remotion/scripts/probe.py`'s `source-meta.json`).

**Two seek-safety rules the linter enforces** (both are in the template):
1. Fade an INNER wrapper, never the `.clip` div (the runtime owns clip visibility).
2. Animate CSS-initialized transforms (`scaleX`/`rotate`) with `fromTo`, not `to`.

Then check structure + runtime:
```
npx hyperframes lint        # static structure + seek-safety
npx hyperframes validate    # headless Chrome: JS errors, missing assets, contrast
```
Both must pass. (`validate` works even when `render` hits the EFTYPE bug.)

### 6. Render transparent overlay + composite + self-review
Preferred (HF browser healthy):
```
npx hyperframes render --format mov -o out/graphics-overlay.mov   # transparent ProRes 4444
# or --format webm for VP9-alpha (smaller; editors ignore its alpha, ffmpeg composites fine)
```
Fallback (EFTYPE / offline): drive the system Chrome yourself — `examples/shoot.mjs`
for stills; a PNG sequence + ffmpeg for the video. Either way, composite onto the
source **copying audio** (this is the same overlay-then-composite architecture as
the other Remotion skills):
```
ffmpeg -y -i work/source.mp4 -i out/graphics-overlay.mov \
  -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" \
  -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset veryfast -c:a copy \
  -pix_fmt yuv420p -movflags +faststart out/final.mp4
```
The transparent overlay is a large, deletable intermediate — keep `out/final.mp4`,
delete the overlay after compositing. Force `-pix_fmt yuv420p` (a 444 overlay can
emit unplayable output) and assert it in self-check.

Self-review the stills (from `shoot.mjs` or HF's `snapshot`), one mid-window per cue:
- **Legible** on its scrim/card against THIS frame (not dark-on-dark).
- **Face clear** — anchored to its edge, not over the speaker, not off-frame.
- **On the word** — the scene lands on its phrase (re-check at each `at`).
- **Content true** — copy matches what's said; names/numbers correct (grep the
  transcript at that time).
- **Alpha correct** — footage shows through non-card areas; fullBleed scenes are
  fully opaque (no gradient bleed-through).

## Combining with captions (video-add-captions)
Both are bottom-anchored, so they'd overlap. Keep captions at the bottom; re-anchor
these scenes to the TOP (flip the anchor wrappers' `justify-content` to
`flex-start` and move padding to the top). Render both transparent overlays, then
composite serially in one ffmpeg pass (captions first, graphics on top), copying
audio. See `video-add-captions/SKILL.md` for the two-overlay command.
