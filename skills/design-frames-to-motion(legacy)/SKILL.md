---
name: design-frames-to-motion
description: >
  Turn a folder of static design frames (PNGs / exported graphics from designers)
  into a transcript-synced motion-graphics clip, built entirely as code in Remotion
  (React). Each frame is rebuilt as a parametric component (every word, color and
  beat is a prop you can prompt); timing lives in one global knobs file; overlays
  fire from a cue sheet timed to the word-level transcript so beats land on the
  spoken word — no timeline scrubbing. Optional Figma round-trip lets designers
  tweak the components; final headless 4K render with the agent screenshotting its
  own stills to self-review before each full pass. Use when asked to "use remotion
  to stitch these design assets into a clip", "rebuild these graphics / interludes
  as code", "animate in these PNG frames", "sync these overlays to what's said",
  用 remotion 把设计帧拼成动画, 把设计稿/静态帧做成代码动效. NOT for cutting the
  talking-head footage itself (rough-cut), plain every-line subtitles (captions),
  or inputs that are not design frames.
---

# Design Frames → Coded Motion Graphics (Remotion)

Turn a stack of **static design frames** (the PNGs a design team hands you) into a
finished, transcript-synced **motion-graphics clip** — interludes and overlays that
animate in over a talking-head cut. Nothing is drawn on a timeline: every frame is
**rebuilt as a Remotion React component**, every word/color/beat is a prop, and the
edit is a **cue sheet timed off the transcript**.

## The one idea
**The graphic is code, not a timeline.** A flat PNG becomes JSX where every word,
color and beat is a parameter you can prompt. Timing is centralized in one knobs
file. Overlays fire from a transcript-driven cue sheet. Review by screenshotting
stills. Because it is all text, the agent can read it, diff it, and re-render it.

## When to use
- You have **static design frames / interlude graphics** (PNGs, design exports) and
  want them animated into a clip or layered as overlays over existing footage.
- The ask is "use Remotion to stitch these assets into a clip that smoothly animates
  them in", "rebuild these graphics as code", "make every word/color a prop",
  "sync these overlays to what's said".
- NOT for: cutting the talking-head footage itself (that is the rough-cut workflow);
  plain every-line subtitles; inputs that aren't design frames.

## Dependencies
- **Node + Remotion** project (`npx create-video@latest`), React + TypeScript.
- **ffmpeg** (Remotion drives it for the final encode).
- A **word-level transcript** of the video's audio (Whisper JSON with per-word
  start/end) — overlays are timed off it. Keep it at `work/transcript.json`.
- (Optional) **Figma** for the designer round-trip.

## Working layout
```
assets/                 # INPUT: the static design frames (PNGs) from designers
src/anim.tsx            # *** global timing knobs — tweak these first ***
src/KeypointLedger.tsx  # one parametric component per design frame
src/FinalEdit.tsx       # the cue sheet: which overlay fires at which second
src/Root.tsx            # composition registered at 4K / 24fps
work/transcript.json    # word-level timestamps (grep phrases -> cue `at`)
work/stills/            # self-review screenshots
out/final.mp4           # THE DELIVERABLE (headless 4K render)
```
Worked versions of the four `src/` files are in `examples/`.

## The pipeline (7 steps)

### 1. Ingest the design frames
Point the agent at the folder of PNGs and ask for a first pass. The real prompt that
kicked this off:
> *"I've added a bunch of design files for interludes in `@assets/` — I want to use
> Remotion to stitch these all together into a final clip that smoothly animates in
> the assets… please do a first pass."*

### 2. Rebuild each PNG as a parametric component
One frame → one Remotion component driven by `useCurrentFrame()`. Animate beats with
`interpolate(frame, [from, to], [0, 1], { easing })`. **Every word, color and beat
becomes a prop** — the static design "becomes JSX… now a parameter you can prompt."
See `examples/KeypointLedger.tsx` (the real component — a multi-beat reveal where the
right column lights up while the left grays out and strikes through).

### 3. Centralize the feel in one knobs file
`src/anim.tsx` holds the global timing (frames @ 24fps) and shared easing. **Tweak
these first** — every component imports them, so the whole piece keeps one rhythm and
you change the feel in one place. See `examples/anim.tsx`.

### 4. Write the cue sheet, timed by the transcript
`src/FinalEdit.tsx` is a list of cues `{ id, at, dur }` — which overlay, at what
second, for how long. **No timeline scrubbing:** grep `work/transcript.json` for the
phrase you want, read its start time, and set `at`. The agent moves a cue by editing
text, not by dragging. See `examples/FinalEdit.tsx`.

### 5. Land each beat on the spoken word
Pass frame-precise props so a beat hits exactly when a word is said:
`<KeypointLedger beat2At={295} />` — **frame 295 is the word "right."** Convert with
`frame = word_start_seconds × fps` (here 295 / 24 ≈ 12.3s).

### 6. (Optional) Figma round-trip for designers
Export the components to Figma so the design team can tweak them in a live "control
room" — drag grade sliders, replay animations, then **"copy feedback as prompt"** to
get exact numbers ready to paste back into Claude Code.
> *"I want my design team to be able to make tweaks to these components…"*
> → *"great now can you also export it to a Figma file"*

Pull their changes back in:
> *"the design has been updated in this Figma… can you update the video to match?"*

### 7. Render 4K headless + self-review
Register the composition at 4K / 24fps (`examples/Root.tsx`), then render headless:
```
npx remotion render FinalEdit out/final.mp4
```
Before each full pass, the agent **screenshots stills** (e.g. `npx remotion still
FinalEdit work/stills/f295.png --frame=295`) to review its own work — catch a
mistimed beat or wrong color before burning a multi-thousand-frame 4K render.

## Self-check
- Each overlay appears/disappears on its intended phrase — re-watch at every cue's
  `at`, and confirm frame-precise beats land on the exact word.
- Stills at the key frames look right (color, text, layout) before the full render.
- One rhythm: every component reads its timing from `anim.tsx` (no stray local
  durations drifting out of sync).
- The whole edit is text — re-readable, diffable, re-renderable.
