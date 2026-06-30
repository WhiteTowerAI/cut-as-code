---
name: video-to-captions
description: >
  Auto-caption a video as Remotion (React): transcribe it word-by-word, group the
  words into readable caption cues (broken on punctuation, line budget, duration and
  speech gaps), and render styled subtitles with optional per-word karaoke highlight.
  Render a transparent caption overlay by default, then
  composite that overlay onto the source with ffmpeg (`-c:a copy`) so Remotion does not
  decode the source on every frame. A simple full-frame <OffthreadVideo> render path is
  also provided for short clips. Also emits a standard .srt. Use when asked to
  "add captions/subtitles to this video",
  "auto-caption / burn in subtitles", "karaoke / word-by-word captions", 给视频自动加
  字幕, 烧录字幕, 逐词高亮字幕. Same content-driven, transcript-timed, code-is-the-edit
  approach as video-to-remotion — but this one covers EVERY line, where
  video-to-remotion adds selective graphics (lower-thirds, stats, section cards).
  NOT for cutting footage (rough-cut) or selective callouts (video-to-remotion).
---

# Video → Auto Captions (Remotion)

Turn a video's speech into **styled, burned-in subtitles** — every line covered,
timed to the word, optionally karaoke-highlighted — by rendering a transparent caption
overlay and compositing it onto the source with ffmpeg. Same philosophy as
`video-to-remotion` (transcript → cue sheet → Remotion → render, all text), but where
that skill adds *selective* graphics, this one provides *full* caption coverage.

## The one idea
**Captions are data, not a timeline.** The transcript becomes `captions.json` (cues
with per-word timings); one Remotion component reads it and draws the active cue,
highlighting the current word. Re-chunk or restyle by editing text + re-rendering.

## When to use
- Any video that needs subtitles / captions burned in (talking-head, podcast, social
  vertical, explainer).
- The ask is "add captions", "auto-subtitle this", "karaoke / word-by-word captions",
  "burn in subtitles with the original audio".
- NOT for: cutting the footage (rough-cut); *selective* callouts/lower-thirds/stats
  (→ `video-to-remotion`); design-frame interludes (→ `design-frames-to-motion`).

## Dependencies
- **Node + Remotion** project (`npx create-video@latest`), ffmpeg + ffprobe
  (ffprobe drives `scripts/probe.py`, which sizes the render — see step 4).
- Python with **faster-whisper** for the transcript (CPU/int8 works). Reuses the
  `video-rough-cut` skill's `transcribe.py` and its exact `work/transcript.json`
  format (segments → words with start/end).
- **Languages.** The chunker handles both space-delimited (English) and CJK
  (Chinese/Japanese/Korean wrap by character, break on `。！？`). The bundled
  `transcribe.py` defaults to English (`base.en`); for any other language pass a
  multilingual model + `--lang` (e.g. `transcribe.py audio.wav out medium --lang zh`).
  This skill consumes only the resulting transcript. For CJK, use a smaller
  `--max-chars` (≈12–16) since each char is one display unit.

## Working layout
```
public/source.mp4       # the video (Remotion staticFile root)
work/transcript.json    # word-level timestamps  (video-rough-cut/transcribe.py)
src/captions.json       # *** caption cues w/ per-word timings ***  (build_captions.py)
out/captions.srt        # portable SubRip (bonus / sanity read)
src/anim.tsx            # palette + caption timing knobs
src/Caption.tsx         # draws the active cue (+ karaoke highlight)
src/CaptionsOverlay.tsx # default composition: transparent Caption-only overlay
src/Captions.tsx        # simple, slow fallback: OffthreadVideo(source) + Caption
src/source-meta.json    # {width,height,durationInSeconds} from scripts/probe.py
src/Root.tsx            # registers both, sized from src/source-meta.json
out/caption-overlay.mov # transparent ProRes overlay
out/captioned.mp4       # THE DELIVERABLE
```
Worked versions of the `src/` files are in `examples/`.

## The pipeline (5 steps)

### 1. Transcribe the video (word level)
```
ffmpeg -y -i public/source.mp4 -ac 1 -ar 16000 work/audio16k.wav
python ../video-rough-cut/scripts/transcribe.py work/audio16k.wav work/transcript
```
**Already ran `video-rough-cut` on this clip?** Its self-check wrote
`work/selfcheck/cut_transcript.json` — a word-level transcript of the exact cut you're
captioning. Reuse it as `work/transcript.json` and skip this step (saves a ~15–20 min
CPU transcription).
**Non-English:** pass a multilingual model + `--lang` to `transcribe.py` (e.g.
`python ../video-rough-cut/scripts/transcribe.py work/audio16k.wav work/transcript medium --lang zh`),
or run your own Whisper. This skill only needs `transcript.json`.

### 2. Build caption cues
```
python scripts/build_captions.py work/transcript.json src/captions.json out/captions.srt
```
Groups words into readable cues — broken on sentence punctuation, a line budget
(`--max-chars`×`--max-lines`), `--max-dur`, and speech `--gap` — keeping per-word
timings for karaoke. Writes `src/captions.json` (drives the render) and `out/captions.srt`
(portable). See `reference/caption-rules.md` for the rules, schema and tunables. Skim the
`.srt` to confirm the chunking reads well before rendering.

**Correct recurring proper-noun / domain-term ASR errors before rendering.** "Faithful to
the transcript" must not burn real ASR *errors* into every cue — e.g. a host's name heard
as "social front" (actually "Herschel Fruean"), or "first XV" heard as "first 13 / first
15". These don't match the audio; they're mistakes. This is a **cheap, targeted
find-replace on a handful of systematic strings** in `src/captions.json` — NOT an
editorial rewrite of every line. For each fix, edit **both**:
- the cue's `text` and `lines[]` (these drive the `.srt`), and
- the cue's **`words[]` entries** — `Caption.tsx` renders the karaoke from `words[]`, so
  fixing only `text` does NOT change the burned-in display.
Scope each replacement so it can't over-fire (e.g. "first 13/15" → "first XV" but **leave**
genuine "first 15 **minutes**"). Then continue to render. This is distinct from editorially
rewriting cues.

### 3. Style the caption component
`examples/Caption.tsx` spans the whole video and draws whichever cue is active for the
current frame; with `karaoke` on, the spoken word is highlighted (`CLAY`) and upcoming
words are dimmed. Tune position/size/look there and in `anim.tsx` (bottom-center default;
raise `paddingBottom` for vertical video).

### 4. Put captions into a transparent overlay
`examples/CaptionsOverlay.tsx` draws `<Caption>` on a transparent background. This is the
default for any clip longer than ~1-2 minutes because Remotion only renders the caption
layer; it does not seek/decode the H.264 source on every frame. `examples/Captions.tsx`
is the simple, slow fallback that plays `source.mp4` via `<OffthreadVideo>` and burns the
captions in during one render. Size both compositions to the source first:
```
python scripts/probe.py public/source.mp4 src/source-meta.json
```
`Root.tsx` imports `src/source-meta.json` and sets `width`/`height`/`durationInFrames`
from it (`durationInFrames = ceil(durationInSeconds × 24)`). This replaces the old
runtime `getVideoMetadata`/`calculateMetadata`, which failed on some server-side render
paths and silently fell back to a 4K render. No `source-meta.json`? Hand-write it with
the real `{width, height, durationInSeconds}`.

### 5. Render the overlay, ffmpeg-composite it, then self-review
Render cost starts with `frames = duration_s x fps`. The full-frame fallback decodes the
source for every frame; the transparent overlay path avoids that and then uses one ffmpeg
pass to combine the overlay with the source while copying audio.
```
npx remotion still src/index.ts Captions work/stills/t12.png --frame=290
npx remotion render src/index.ts CaptionsOverlay out/caption-overlay.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
ffmpeg -y -i public/source.mp4 -i out/caption-overlay.mov -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset veryfast -c:a copy -movflags +faststart out/captioned.mp4
```
Use the `Captions` still for self-review because it shows captions on the real frame; it
only decodes selected frames.
The transparent ProRes 4444 `out/caption-overlay.mov` is a **large, deletable intermediate**
(it stores a full alpha frame every frame — multiple GB even at low resolution). The final
`out/captioned.mp4` is the deliverable; delete the `.mov` after compositing (or use a lighter
alpha codec like `qtrle` / VP9-webm-alpha if you want to keep it).
For long renders, keep the render under a foreground/monitoring process that emits
progress. Detached fire-and-forget background jobs can be killed when the controlling
session goes idle.

Simple, slow one-pass fallback for very short clips:
```
npx remotion still src/index.ts Captions work/stills/t12.png --frame=290
npx remotion render src/index.ts Captions out/captioned.mp4
```

## Combining captions + overlays (with video-to-remotion)
Captions (this skill) and the `video-to-remotion` cards are both **bottom-anchored**, so
layering them as-is makes them overlap. To ship one video with BOTH:
1. **Keep captions at the bottom** (unchanged — `Caption.tsx` is `justifyContent:"flex-end"`).
2. **Re-anchor the remotion cards to the TOP** so they clear the captions: set `ANCHOR = "top"`
   in `video-to-remotion/examples/anim.tsx`. That single knob flips every card's
   `justifyContent` + edge padding and the `Scrim` (top band, reversed gradient) together — no
   per-component edits. Its default is `"bottom"`; only flip it for this combined layout.
3. **Render BOTH transparent overlays, then composite serially in one ffmpeg pass** (captions
   first, cards on top), copying audio:
   ```
   ffmpeg -y -i first_cut.mp4 -i out/caption-overlay.mov -i out/graphics-overlay.mov \
     -filter_complex "[0:v][1:v]overlay[a];[a][2:v]overlay[v]" \
     -map "[v]" -map 0:a? -c:a copy -c:v libx264 -crf 18 -preset veryfast out/final.mp4
   ```

## Self-check
- Read `out/captions.srt`: cues are readable length, break on sense, and match the audio.
- Spot-check stills mid-cue: the right line shows, and (karaoke) the highlight is on the
  word actually being said.
- No caption overruns its audio or collides with the next (gaps/`--max-dur` respected).
- Composition length + frame size match the source (no captions past the end, no letterbox).
- The whole edit is text — re-chunk or restyle and re-render.
