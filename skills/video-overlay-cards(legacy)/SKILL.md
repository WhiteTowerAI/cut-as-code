---
name: video-overlay-cards
description: >
  Package an existing talking-head / podcast / interview video (single mostly-static shot)
  with finished-film OVERLAY CARDS — an intro/title card, chapter cards, lower-third name
  bars, and an outro card — composited onto the playing video without re-cutting or changing
  duration. Cards are rendered as transparent PNG layers (PIL) and composited in one ffmpeg
  pass with fades; audio is copied so sync is preserved. Includes a transcript placement
  helper to pick card timestamps and ground card text in what's actually said. Use when asked
  to "package / dress up my video", add 片头卡/章节卡/下三分之一名条/片尾卡, lower-thirds,
  title/chapter cards, or make a talking-head clip look more like a finished cut. NOT for
  subtitles (every line) — that's embedded-captions; NOT for building a video from scratch.
---

# Video Overlay Cards (intro / chapter / lower-third / outro)

Lay timed, designed cards over an existing single-shot talking-head video. The picture and
duration are untouched; you only add an overlay layer. Four card types, one design language:

- **intro** — title card over the cold open (show/brand + host).
- **chapter** — section divider at topic switches (`PART n` kicker + big title).
- **lowerthird** — name bar at the first mention of a person/team/key fact (line1 + line2).
- **outro** — sign-off card over the closing.

Everything is **bottom-anchored** so it never covers a centered face, with a teal accent, a
soft bottom scrim for contrast on busy backgrounds, and 0.3 s fades. The look auto-scales to
the source resolution.

## Contract
- Each card is rendered to a **full-frame RGBA PNG** (transparent except the card region).
- Composited with `overlay=…:enable='between(t,t_in,t_out)'`, alpha fade in/out, `setpts`-shift.
- **Audio is `-c:a copy`** (never re-encoded → A/V sync identical to source).
- Output keeps the source **duration, fps, and dimensions**.

## Inputs
- The source video (`source.mp4`).
- An `overlays.json` describing every card (schema below; see `overlays.example.json`).
- A word-level transcript of the SAME video (faster-whisper / Whisper JSON) — used by the
  placement helper to choose timestamps and ground text. Transcribe the video you're packaging
  so timestamps are already on its own timeline (no edit-mapping needed).

## overlays.json schema
```jsonc
{
  "video": { "w": 1280, "h": 720, "fps": 30, "duration_s": 1234.5 },
  "fade_s": 0.3,
  "elements": [
    { "id": "intro", "type": "intro", "t_in": 0.6, "t_out": 6.4,
      "kicker": "MY SHOW · EP 14", "title": "BIG TITLE", "sub": "with Host Name", "reason": "…" },
    { "id": "ch1", "type": "chapter", "t_in": 78.5, "t_out": 84.0,
      "kicker": "PART 1", "title": "THE TOPIC", "reason": "topic switch at …" },
    { "id": "lt_x", "type": "lowerthird", "t_in": 238.0, "t_out": 245.5,
      "line1": "Person / Team", "line2": "one-line detail", "reason": "first mention of …" },
    { "id": "outro", "type": "outro", "t_in": 1225.0, "t_out": 1234.0,
      "title": "MY SHOW", "sub": "Thanks for watching", "small": "small line", "reason": "sign-off" }
  ]
}
```
`t_in`/`t_out` are seconds on the source timeline. Windows of 5–8 s read comfortably.

## Workflow

1. **Probe the source** — get exact dims/fps/duration/audio; put `w,h,fps,duration_s` into
   `overlays.json` `video`:
   ```
   ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration \
     -show_entries format=duration -of default=nw=1 source.mp4
   ```

2. **Place the cards** (helper) — work off a word-level transcript of this video:
   ```
   python scripts/place_cards.py transcript.json --outline 90        # topic digest → chapter anchors
   python scripts/place_cards.py transcript.json --find "Alice,Acme,62-19"   # first-mentions → name-bar times
   python scripts/place_cards.py transcript.json --window 238 246    # confirm what's said in a card window
   ```
   Decide where each card goes; write `overlays.json`.
   **Grounding rules:** card text comes from the transcript — don't invent content. Fix obvious
   ASR mis-spellings of names (verify a person/brand name if it's the headline). Prefer
   verifiable facts (names, scores) over shaky ASR surnames in a name bar. Chapter titles are
   editorial labels but must describe what is actually said.

3. **Render the cards** → transparent PNGs:
   ```
   python scripts/render_cards.py overlays.json --out cards/
   ```

4. **Composite** → packaged MP4 (one ffmpeg pass, audio copied, duration preserved):
   ```
   python scripts/build_render.py overlays.json source.mp4 out.mp4 --cards cards/
   ```

5. **Eyeball one card** — grab a frame mid-window and confirm the card is readable, doesn't
   cover the face, and matches what's being said:
   ```
   ffmpeg -v error -ss <mid> -i out.mp4 -frames:v 1 -y check.png
   ```

## Design notes / gotchas
- **Bottom-anchored by design.** Assumes a centered subject with the face in the upper/middle
  of frame. If the subject sits low or moves, re-check that cards clear the face.
- **Fades live in ffmpeg, not the PNG.** Cards are drawn fully opaque; `build_render.py` applies
  `fade=…:alpha=1` so each card is solid ~`fade_s` after `t_in` until ~`fade_s` before `t_out`.
- **No `-shortest`.** The looped card images are short inputs; `-shortest` would truncate the
  output to them. The base video governs duration.
- **Fonts** are set at the top of `render_cards.py` (Windows TTFs by default: Arial Black / Arial
  Bold / Segoe UI Semibold). Swap them there for other platforms or a different identity.
- Text-only, no subtitles, no music, no re-cut — by design.
