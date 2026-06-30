---
name: video-to-remotion
description: >
  Watch a video's own content and auto-generate the Remotion (React) motion-graphics
  components it needs — no designer frames required. Transcribe the video word-by-word,
  scan the transcript (and scene cuts) to surface graphic *opportunities* (intro/outro title
  card, chapter card, speaker lower-third, stat callout, enumerated list, key-quote), then emit
  one parametric Remotion component per graphic — all on ONE design language (each rides a
  bottom scrim/card, bottom-anchored so it never covers the face, sized to the canvas) with
  *editorial copy* written from the content (ASR-garbled names corrected), and a cue sheet that
  fires each overlay on the spoken word. Render a transparent overlay at the source's own size
  (not 4K), ffmpeg-composite it onto the source while copying audio, and screenshot stills to
  self-review. Use when asked to "auto-generate
  Remotion components from this video", "watch the video and add the graphics it needs",
  "turn this talking-head into a motion-graphics cut", 根据视频内容自动生成 remotion 组件,
  自动给视频加字幕条/数据callout/章节卡. This is the content-driven sibling of
  design-frames-to-motion (which instead rebuilds designer-supplied PNG frames). NOT for
  cutting the footage (rough-cut), plain every-line subtitles (captions), or when a
  designer already handed you the frames (use design-frames-to-motion).
---

# Video → Auto-Generated Remotion Components

Point this at a talking-head / podcast / explainer video and it **reads the content**
to decide which motion graphics the video wants, then **writes the Remotion components**
for them — speaker bars, stat callouts, key-quote pins, list reveals, section cards —
each timed to land on the spoken word. The designer-frame workflow
(`design-frames-to-motion`) starts from PNGs someone drew; **this one starts from the
video itself** and generates the graphics from what is actually said and shown.

## The one idea
**The video is the brief.** Graphic decisions come from the transcript (and scene cuts),
not from a storyboard. The analyzer proposes opportunities; the agent prunes them; each
survivor becomes a parametric React component whose every word/color/beat is a prop. The
edit stays text — a cue sheet you can read, diff, and re-render.

**One design language.** The overlays sit on REAL footage, not light designer frames, so
every card obeys three rules (in `anim.tsx` + the components): it rides on its OWN
background (a **scrim** or a **dark card**) so it's legible on any picture; it is
**edge-anchored** so it never covers the speaker's face — the `ANCHOR` knob in `anim.tsx`
sets which edge, defaulting to **bottom** (the lower-third safe zone), flip to **top** to
clear bottom captions; and its sizes are a **% of canvas height** so it reads at any
resolution. One teal accent, 0.3 s fades. Four card jobs —
**intro / chapter / lower-third / outro** (+ optional stat / keypoint / list) — written in
editorial copy, not raw transcript fragments.

## When to use
- A finished/near-finished video needs **on-screen graphics derived from its content**:
  who's talking, the numbers they cite, the questions they pose, the lists they walk
  through, where the topics turn.
- The ask is "auto-generate the Remotion components for this video", "watch it and add
  the graphics", "dress this talking-head with data callouts / lower-thirds / chapter
  cards from what's said".
- NOT for: cutting the footage (rough-cut); plain every-line subtitles (captions);
  inputs where a **designer already supplied the frames** (→ `design-frames-to-motion`).

## Dependencies
- **Node + Remotion** project, React + TypeScript, ffmpeg. Scaffold (the `examples/` ship
  only `src/` — you must add the project shell):
  - `package.json` with `remotion` + `@remotion/cli` (pin one 4.x, e.g. `4.0.230`) and
    **`react`/`react-dom` pinned to `18.3.1`** (don't let npm pull React 19 against an older
    Remotion), `tsconfig.json`, and `src/index.ts` → `registerRoot(RemotionRoot)`.
  - `public/source.mp4` — needed for `FinalEdit` still checks and the slow fallback because
    `OffthreadVideo` loads via `staticFile("source.mp4")`, which only resolves inside
    `public/`; an arbitrary path won't load. `npm install`, then render.
- Python with **faster-whisper** for the transcript (CPU/int8 works). The
  `video-rough-cut` skill's `transcribe.py` produces the exact `work/transcript.json`
  format this skill consumes (segments → words with start/end). Default model is
  English-only (`base.en`); for other languages pass a multilingual model + `--lang`
  (e.g. `transcribe.py audio.wav out medium --lang zh`).
- ffmpeg for **scene detection** (optional; on a single-shot talking-head it often finds 0
  cuts, so section cards then come from transcript pauses — that's fine).
- On Windows/PowerShell the bash `grep`/`sed` one-liner in step 2 won't run — capture
  ffmpeg's `showinfo` to a file and parse `pts_time` with Python instead.

## Working layout
```
work/source.mp4         # the video
work/transcript.json    # word-level timestamps  (video-rough-cut/transcribe.py)
work/scenes.txt         # optional: one scene-cut timestamp per line (ffmpeg)
work/content.json       # *** detected graphic opportunities ***  (analyze_content.py)
work/cues.json          # draft cue sheet                         (draft_cues.py)
package.json            # Remotion project (pin React 18) — see Dependencies
public/source.mp4       # only needed for the slow OffthreadVideo fallback
src/index.ts            # entry: registerRoot(RemotionRoot)
src/anim.tsx            # design system: timing + palette + Scrim + height-relative scale
src/components/*.tsx    # Intro, SectionCard(chapter), LowerThird, StatCallout, Keypoint, ListReveal, Outro
src/FinalEdit.tsx       # the cue sheet, transparent overlay, slow OffthreadVideo fallback
src/source-meta.json    # {width,height,durationInSeconds} from scripts/probe.py
src/Root.tsx            # composition @ SOURCE size / 24fps (NOT 4K), sized from source-meta.json
out/graphics-overlay.mov # transparent ProRes overlay
out/final.mp4           # THE DELIVERABLE
```
Worked versions of every `src/` file are in `examples/` (you still scaffold `package.json`,
`src/index.ts`, `public/`, `tsconfig.json` — see Dependencies).

## The pipeline (6 steps)

### 1. Transcribe the video (word level)
Overlays are timed off the transcript, so get per-word timestamps first:
```
ffmpeg -y -i work/source.mp4 -ac 1 -ar 16000 work/audio16k.wav
python ../video-rough-cut/scripts/transcribe.py work/audio16k.wav work/transcript
```
**Already ran `video-rough-cut` on this clip?** Its self-check wrote
`work/selfcheck/cut_transcript.json` — a word-level transcript of the exact cut you're
dressing. Reuse it as `work/transcript.json` and skip this step (saves a ~15–20 min CPU
transcription).

### 2. (Optional) Detect scene cuts
For section cards, list where the picture changes:
```
ffmpeg -i work/source.mp4 -filter:v "select='gt(scene,0.4)',showinfo" -f null - 2>&1 \
  | grep showinfo | sed -n 's/.*pts_time:\([0-9.]*\).*/\1/p' > work/scenes.txt
```

### 3. Analyze the content → opportunities
```
python scripts/analyze_content.py work/transcript.json work/content.json --scenes work/scenes.txt
```
Surfaces `lower-third / stat / list / keypoint / section` opportunities, each with a
word-accurate `at`, a suggested `dur`, draft `props`, and the `quote` it came from. See
`reference/graphic-types.md` for the trigger→component table and the JSON schema.
**Detection is a draft** — read each `quote` and decide what actually earns screen time.

### 4. Decide the graphics → cue sheet
```
python scripts/draft_cues.py work/content.json work/cues.json
```
Prints a ready-to-paste `CUES` array (component + props + at/dur), de-stacked so overlays
don't collide. Paste it into `src/FinalEdit.tsx`, then **prune and re-time by hand**: drop
the noise, fill `list` items from the transcript, and nudge each `at` to land on the exact
word (grep `work/transcript.json` for the phrase, read its start time). No timeline scrubbing.

### 5. Write the copy + fill the components
The components already exist in `examples/components/` (`Intro`, `SectionCard` = chapter,
`LowerThird`, `StatCallout`, `KeypointCallout`, `ListReveal`, `Outro`) — all on the one
design language (scrim/card, bottom-anchored, height-relative, teal accent, reading timing
from `anim.tsx`). You rarely redraw them; the real work is the **copy**:
- **Write, don't paste.** A lower-third is `line1` (the entity) + `line2` (a one-line
  *editorial gloss* you write — "a 62–19 blowout", "#1 in the country"), not a raw clause.
  Chapter `title` is an editorial label; `ListReveal.items` are rewritten from the transcript.
- **Get names right.** `base.en` mangles proper nouns (e.g. "Auckland Grandma" → *Grammar*,
  "Saffron" → *Southland*). Correct them from context; **verify a headline name/brand online**
  if it's the intro card. Prefer verifiable facts (names, scores) over shaky ASR surnames.
- **Ground every card** in what's actually said at its `at` — no invented content.
- Place **Intro** over the cold open and **Outro** over the sign-off (fixed, not detected).
Register any new component in `FinalEdit`'s `COMPONENTS` map; pass `durFrames` so cards fade.

### 6. Render transparent overlay at SOURCE size + self-review
Size the composition to the source first — do NOT render a 640-px clip at 4K (it only
blurs the picture and adds letterbox bars):
```
python scripts/probe.py work/source.mp4 src/source-meta.json
```
`Root.tsx` imports `src/source-meta.json` and sets `width`/`height`/`durationInFrames`
from it (`durationInFrames = ceil(durationInSeconds × 24)`) — no more hand-edited
`SRC_W`/`SRC_H`/`DURATION_S` placeholders to forget. No `source-meta.json`? Hand-write it
with the real `{width, height, durationInSeconds}`. Cards are vector text, so they stay
sharp; pass `--scale 2` for a bigger file instead of inflating the composition.

Default for any clip longer than ~1-2 minutes: render `FinalEditOverlay` as transparent
ProRes, then use one ffmpeg overlay pass to composite onto the source while copying audio.
Render cost starts with `frames = duration_s x fps`; the slow fallback pays that cost plus
an `OffthreadVideo` seek/decode on every frame.
```
npx remotion still src/index.ts FinalEdit work/stills/f295.png --frame=295
npx remotion render src/index.ts FinalEditOverlay out/graphics-overlay.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
ffmpeg -y -i work/source.mp4 -i out/graphics-overlay.mov -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset veryfast -c:a copy -movflags +faststart out/final.mp4
```
Use the `FinalEdit` still for self-review because it shows the graphics on the real frame;
it only decodes selected frames. The transparent ProRes 4444 `out/graphics-overlay.mov` is
a **large, deletable intermediate** (a full alpha frame every frame); keep `out/final.mp4`
and delete the `.mov` after compositing (a sparse graphics overlay is far smaller than a
captions one, but it still adds up). For long renders, keep the render under a foreground/
monitoring process that emits progress. Detached fire-and-forget background jobs can be
killed when the controlling session goes idle.

Simple, slow one-pass fallback for very short clips:
```
npx remotion render src/index.ts FinalEdit out/final.mp4
```

## Combining overlays + captions (with video-to-captions)
These cards and the `video-to-captions` captions are both **bottom-anchored**, so layering
them as-is makes them overlap. To ship one video with BOTH:
1. **Keep captions at the bottom** (unchanged in the captions skill).
2. **Re-anchor these cards to the TOP** so they clear the captions: set `ANCHOR = "top"` in
   `examples/anim.tsx`. That one knob flips every component's `justifyContent` + edge padding
   and the `Scrim` (top band, reversed gradient) together — no per-component edits. Default is
   `"bottom"` (the lower-third safe zone); only flip when you're layering over bottom captions.
3. **Render BOTH transparent overlays, then composite serially in one ffmpeg pass** (captions
   first, cards on top), copying audio:
   ```
   ffmpeg -y -i work/source.mp4 -i out/caption-overlay.mov -i out/graphics-overlay.mov \
     -filter_complex "[0:v][1:v]overlay[a];[a][2:v]overlay[v]" \
     -map "[v]" -map 0:a? -c:a copy -c:v libx264 -crf 18 -preset veryfast out/final.mp4
   ```

## Self-check
Grab a still mid-window for each kept cue and confirm all four — this is the loop that
catches the real defects:
- **Legible:** the card rides on its scrim/card and reads against THIS frame (not dark text
  on dark footage).
- **Face clear:** the card is anchored to its edge (bottom by default; top if `ANCHOR="top"`)
  and doesn't cover the speaker's face or run off-frame.
- **On the word:** the overlay lands on its phrase — re-check at each cue's `at`.
- **Content true:** the copy matches what's said there; names/numbers are correct (cross-check
  by grepping the transcript at that time).

Plus:
- Copy is **written**, not pasted — `line1`/`line2`, chapter titles, list items are editorial,
  ASR-garbled names are corrected (a headline name verified online), nothing invented.
- Rendered at the **source's size** (no 4K upscale / no letterbox); cards sized off canvas
  height so they read.
- One rhythm + one look: every component reads timing/palette from `anim.tsx`.
- The whole edit is text — re-readable, diffable, re-renderable.
