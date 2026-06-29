---
name: video-to-captions
description: >
  Auto-caption a video as Remotion (React): transcribe it word-by-word, group the
  words into readable caption cues (broken on punctuation, line budget, duration and
  speech gaps), and render styled subtitles burned onto the footage — with optional
  per-word karaoke highlight. The source video is fed into the composition via
  <OffthreadVideo>, so a single `remotion render` outputs the final captioned MP4 with
  the original audio (a lossless transparent + ffmpeg path is also provided). Also
  emits a standard .srt. Use when asked to "add captions/subtitles to this video",
  "auto-caption / burn in subtitles", "karaoke / word-by-word captions", 给视频自动加
  字幕, 烧录字幕, 逐词高亮字幕. Same content-driven, transcript-timed, code-is-the-edit
  approach as video-to-remotion — but this one covers EVERY line, where
  video-to-remotion adds selective graphics (lower-thirds, stats, section cards).
  NOT for cutting footage (rough-cut) or selective callouts (video-to-remotion).
---

# Video → Auto Captions (Remotion)

Turn a video's speech into **styled, burned-in subtitles** — every line covered,
timed to the word, optionally karaoke-highlighted — and render the captioned film in
one pass. Same philosophy as `video-to-remotion` (transcript → cue sheet → Remotion →
render, all text), but where that skill adds *selective* graphics, this one provides
*full* caption coverage.

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
- **Node + Remotion** project (`npx create-video@latest`), `@remotion/media-utils`
  (for `getVideoMetadata`), ffmpeg.
- Python with **faster-whisper** for the transcript (CPU/int8 works). Reuses the
  `video-rough-cut` skill's `transcribe.py` and its exact `work/transcript.json`
  format (segments → words with start/end).
- **Languages.** The chunker handles both space-delimited (English) and CJK
  (Chinese/Japanese/Korean wrap by character, break on `。！？`). BUT the bundled
  `transcribe.py` is hardcoded English (`base.en`, `language="en"`) — for any other
  language you must transcribe with a multilingual Whisper model and set the language
  (e.g. `medium`, `language="zh"`). This skill consumes only the resulting transcript.
  For CJK, use a smaller `--max-chars` (≈12–16) since each char is one display unit.

## Working layout
```
public/source.mp4       # the video (Remotion staticFile root)
work/transcript.json    # word-level timestamps  (video-rough-cut/transcribe.py)
src/captions.json       # *** caption cues w/ per-word timings ***  (build_captions.py)
out/captions.srt        # portable SubRip (bonus / sanity read)
src/anim.tsx            # palette + caption timing knobs
src/Caption.tsx         # draws the active cue (+ karaoke highlight)
src/Captions.tsx        # composition: OffthreadVideo(source) + Caption
src/CaptionsOverlay.tsx # composition: transparent Caption-only overlay
src/Root.tsx            # registers it, matched to the source via calculateMetadata
out/captioned.mp4       # THE DELIVERABLE
```
Worked versions of the `src/` files are in `examples/`.

## The pipeline (5 steps)

### 1. Transcribe the video (word level)
```
ffmpeg -y -i public/source.mp4 -ac 1 -ar 16000 work/audio16k.wav
python ../video-rough-cut/scripts/transcribe.py work/audio16k.wav work/transcript
```
**Non-English:** the bundled `transcribe.py` is English-only — transcribe with a
multilingual model + language instead (e.g. `WhisperModel("medium")`,
`language="zh"`), or run your own Whisper. This skill only needs `transcript.json`.

### 2. Build caption cues
```
python scripts/build_captions.py work/transcript.json src/captions.json out/captions.srt
```
Groups words into readable cues — broken on sentence punctuation, a line budget
(`--max-chars`×`--max-lines`), `--max-dur`, and speech `--gap` — keeping per-word
timings for karaoke. Writes `src/captions.json` (drives the render) and `out/captions.srt`
(portable). See `reference/caption-rules.md` for the rules, schema and tunables. Skim the
`.srt` to confirm the chunking reads well before rendering.

### 3. Style the caption component
`examples/Caption.tsx` spans the whole video and draws whichever cue is active for the
current frame; with `karaoke` on, the spoken word is highlighted (`CLAY`) and upcoming
words are dimmed. Tune position/size/look there and in `anim.tsx` (bottom-center default;
raise `paddingBottom` for vertical video).

### 4. Put captions INTO the video
`examples/Captions.tsx` plays `source.mp4` via `<OffthreadVideo>` as the background and
layers `<Caption>` on top — so the render *is* the captioned video, with the original
audio carried through. `examples/CaptionsOverlay.tsx` renders the same captions on a
transparent background for the lossless overlay path. `Root.tsx` matches both composition
lengths + dimensions to the source via `calculateMetadata`/`getVideoMetadata`.

### 5. Render (or composite losslessly) + self-review
Default — one pass outputs the final MP4:
```
npx remotion still   Captions work/stills/t12.png --frame=290   # check a cue + karaoke
npx remotion render  Captions out/captioned.mp4
```
Lossless alternative — keep the source bytes/audio untouched: render the transparent
caption-only composition and ffmpeg-overlay it:
```
npx remotion render src/index.ts CaptionsOverlay out/overlay.mov \
  --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
ffmpeg -i public/source.mp4 -i out/overlay.mov \
  -filter_complex "[0][1]overlay" -c:a copy out/captioned.mp4
```

## Self-check
- Read `out/captions.srt`: cues are readable length, break on sense, and match the audio.
- Spot-check stills mid-cue: the right line shows, and (karaoke) the highlight is on the
  word actually being said.
- No caption overruns its audio or collides with the next (gaps/`--max-dur` respected).
- Composition length + frame size match the source (no captions past the end, no letterbox).
- The whole edit is text — re-chunk or restyle and re-render.
