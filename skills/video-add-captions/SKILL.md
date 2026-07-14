---
name: video-add-captions
description: >
  Add styled, burned-in subtitles to an existing video using Remotion. The skill
  consumes a source video plus word-timed captions, lets the agent map natural
  language style requests to caption presets/options, previews the selected style
  by default, then renders a transparent caption overlay and composites it onto
  the source with ffmpeg while copying audio. Use for auto-captions, subtitles,
  karaoke/word-by-word highlight, and short-video subtitle styling. Do not use
  for rough cutting or selective motion graphics.
---

# Video Add Captions

This skill adds subtitles to a video. It does not cut, trim, diagnose, or
restructure the footage. If the video was already edited by `video-rough-cut` or
another workflow, this skill starts from that finished video and its caption data.

The agent-facing rule is simple:

**User describes the caption result in natural language. The agent maps that to a
stable preset/config, previews it by default, then renders only after confirmation.**

## Scope

Use this skill for:

- Burned-in captions/subtitles on an existing video.
- Every-line captions generated from a word-level transcript.
- Optional per-word karaoke highlight.
- Preset-based visual styles for clean captions, social captions, background bars,
  outlines, and vertical Shorts/Reels/TikTok-style captions.

Do not use this skill for:

- Rough cutting, removing silence, trimming, or editorial selection.
- Selective graphics such as lower-thirds, stats cards, chapter cards, or callouts.
- Asking the final user to manually edit renderer internals.

If rough cutting has already happened, accept the rough-cut output as the input video.
This skill then needs only:

- `public/source.mp4`
- `src/captions.json`
- `src/source-meta.json` or equivalent video metadata
- `src/caption-style.ts` or equivalent final caption style config

## Safe Edit Points

The agent may safely modify:

- `src/caption-style.ts` or `examples/caption-style.ts`: final confirmed style.
- `src/preview-config.ts` or `examples/preview-config.ts`: preview candidates.
- `src/captions.json`: only when fixing caption text/timing data, such as systematic
  ASR errors. If changing displayed text, keep `text`, `lines[]`, and `words[]`
  consistent because the renderer displays `words[]`.

The agent should not modify these for ordinary style feedback:

- `Caption.tsx`
- `Captions.tsx`
- `CaptionsOverlay.tsx`
- `Root.tsx`
- `anim.tsx`
- `caption-style-resolver.ts`
- preset/theme files, unless the task is explicitly a style-system change

## Style Selection Workflow

Preview is the recommended default flow, but it is not mandatory.

1. If the user describes a style, map it to a preset/config, render one preview
   still, show it, and wait for confirmation.
2. If the user does not describe a style, render multiple candidate previews from
   the official presets/options, show them, and let the user choose.
3. If the user explicitly says "skip preview", "do not preview", or "directly
   generate the full video", use the current `caption-style.ts` and render.
4. If the user dislikes a preview, adjust config from natural-language feedback,
   regenerate a preview, and repeat until confirmed.
5. After confirmation, write the final selection to `caption-style.ts` and render
   the complete video.

Do not ask the user to edit `Caption.tsx` or `anim.tsx`. The user speaks in natural
language; the agent edits the config layer.

## Official Presets

Official preset names are exactly:

- `clean`: default clean captions; white/near-white text, no background, light shadow.
- `minimal`: quieter and more restrained; no background, weak or no shadow.
- `social-bold`: large high-impact social captions; preserves the existing bold
  short-video design.
- `pill`: semi-transparent large rounded/capsule background.
- `boxed`: semi-transparent small-radius rectangular background bar.
- `stroked`: no background; white/near-white text with stroke/outline.
- `shorts`: vertical 9:16 trend/shorts style; Cal_Sans, all caps, black stroke,
  no background, lower-mid placement, default karaoke on.

Do not create or document these as official presets:

- `karaoke`
- `pill-yellow`
- `boxed-green`
- `stroked-blue`
- `shorts-yellow`
- `social-bold-karaoke`

Those are preset plus option/theme combinations, or preview candidate ids.

## Themes and Options

Background themes are:

- `gray`
- `yellow`
- `blue`
- `pink`
- `green`

Use them as:

```ts
{
  preset: "pill",
  overrides: {
    background: {
      enabled: true,
      shape: "pill",
      theme: "yellow"
    }
  }
}
```

Stroke themes are:

- `black`
- `yellow`
- `blue`
- `pink`
- `green`

Use them as:

```ts
{
  preset: "stroked",
  overrides: {
    background: { enabled: false },
    stroke: {
      enabled: true,
      theme: "green"
    }
  }
}
```

Shorts highlight colors are:

- `green`: `#21D32E`
- `orange`: `#F8BD6D`
- `yellow`: `#F8F54F`

Use them by overriding `wordHighlight.activeColor` and `wordHighlight.backgroundColor`.
The default `shorts` highlight is green.

Karaoke is an option:

- `karaoke: true` enables per-word highlight.
- `karaoke: false` disables per-word highlight.

It is not an official preset. If an external `karaoke` prop/selection is provided,
it overrides the preset default. Otherwise the renderer uses
`wordHighlight.enabled` from the resolved style.

## Natural Language Mapping Examples

"Subtitle clean, no background, just white text and light shadow":

```ts
{
  preset: "clean",
  karaoke: false,
  overrides: {
    background: { enabled: false }
  }
}
```

"I want big short-video captions":

```ts
{
  preset: "social-bold",
  karaoke: true
}
```

"I want yellow rounded background":

```ts
{
  preset: "pill",
  overrides: {
    background: {
      enabled: true,
      shape: "pill",
      theme: "yellow"
    }
  }
}
```

"I want a blue small rounded background bar":

```ts
{
  preset: "boxed",
  overrides: {
    background: {
      enabled: true,
      shape: "rounded",
      theme: "blue"
    }
  }
}
```

"No background, add black outline":

```ts
{
  preset: "stroked",
  overrides: {
    background: { enabled: false },
    stroke: {
      enabled: true,
      theme: "black"
    }
  }
}
```

"White text with green outline, no background":

```ts
{
  preset: "stroked",
  overrides: {
    background: { enabled: false },
    stroke: {
      enabled: true,
      theme: "green"
    }
  }
}
```

"I want vertical shorts style with green highlight":

```ts
{
  preset: "shorts",
  karaoke: true,
  overrides: {
    wordHighlight: {
      activeColor: "#21D32E",
      backgroundColor: "#21D32E"
    }
  }
}
```

"Shorts style with orange highlight":

```ts
{
  preset: "shorts",
  karaoke: true,
  overrides: {
    wordHighlight: {
      activeColor: "#F8BD6D",
      backgroundColor: "#F8BD6D"
    }
  }
}
```

"Enable word-by-word highlight":

```ts
{
  preset: "clean",
  karaoke: true
}
```

"Do not use word-by-word highlight":

```ts
{
  preset: "clean",
  karaoke: false
}
```

If the user only says "I do not like it", offer a small set of directions instead
of asking a broad open question:

- cleaner
- more eye-catching
- bigger or smaller text
- stronger or weaker background
- change background color
- switch to outline text
- switch to shorts style
- enable or disable karaoke
- generate another preview set

## Working Layout

In a Remotion scaffold, copy the `examples/` files into `src/` or import them from
the skill examples:

```text
public/source.mp4
src/captions.json
src/source-meta.json
src/caption-style.ts
src/caption-presets.ts
src/caption-style-resolver.ts
src/caption-color-themes.ts
src/Caption.tsx
src/CaptionsOverlay.tsx
src/Captions.tsx
src/CaptionPreview.tsx
src/preview-config.ts
src/preview-index.tsx
src/Root.tsx
out/caption-overlay.mov
out/captioned.mp4
```

The example files live in `examples/`. Helper scripts live in `scripts/`.

## Caption Data

If you need to generate captions from a transcript:

```powershell
python scripts/build_captions.py work/transcript.json src/captions.json out/captions.srt
```

The transcript should be word-level JSON compatible with the shared
`video-rough-cut/scripts/transcribe.py` output. This skill can reuse a transcript
from a prior rough-cut run, but it does not perform the rough cut itself.

Before rendering, skim `out/captions.srt` and fix systematic ASR errors in
`src/captions.json` if necessary. If fixing displayed text, update `text`, `lines[]`,
and the relevant `words[]` entries together.

## Source Metadata

Generate source metadata before Remotion render:

```powershell
python scripts/probe.py public/source.mp4 src/source-meta.json
```

`Root.tsx` expects `{ width, height, durationInSeconds }` so the compositions match
the source dimensions and duration.

## Preview Commands

Preview requires a Remotion scaffold with the example preview files available.
Run from the skill/scaffold directory that contains `examples/preview-index.tsx`:

```powershell
node --experimental-strip-types scripts/render-caption-previews.mjs
```

The script:

- reads `examples/preview-config.ts`
- renders each preview candidate through Remotion
- writes PNGs to `out/style-previews`
- uses `Caption.tsx` and the same style resolver as final render

On machines without `npx` on `PATH`, set `REMOTION_BIN`:

```powershell
$env:REMOTION_BIN="F:\path\to\node_modules\.bin\remotion.cmd"
node --experimental-strip-types scripts/render-caption-previews.mjs
```

Use preview output as a decision aid. Do not treat preview candidate ids as official
preset names.

## Render Commands

For long videos, prefer the transparent overlay path:

```powershell
npx remotion still src/index.ts Captions work/stills/t12.png --frame=290
npx remotion render src/index.ts CaptionsOverlay out/caption-overlay.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
ffmpeg -y -i public/source.mp4 -i out/caption-overlay.mov -filter_complex "[0:v][1:v]overlay=shortest=1:format=auto[v]" -map "[v]" -map 0:a? -c:v libx264 -crf 18 -preset veryfast -c:a copy -movflags +faststart out/captioned.mp4
```

For very short clips, the simple full-frame fallback is available:

```powershell
npx remotion still src/index.ts Captions work/stills/t12.png --frame=290
npx remotion render src/index.ts Captions out/captioned.mp4
```

The overlay `.mov` can be large. It is an intermediate artifact; the final deliverable
is `out/captioned.mp4`.

## Testing Guidance

After the real-video tuning work, use this validation order:

1. Short smoke test first: 30-60 seconds, a few representative captions, one or two
   style previews, one final still, then a short final render.
2. Long E2E test second: full duration, final style in `caption-style.ts`, overlay
   render, ffmpeg composite, and spot-check early/middle/late captions.
3. Watch for visual issues: safe area, long words, multiline cues, bright backgrounds,
   vertical/horizontal framing, and subtitle density.
4. Treat visual corrections as Design Tuning. Adjust preset/config values narrowly.
   Do not change architecture or renderer internals unless a real rendering bug requires it.

## Self Check

- `caption-style.ts` contains the confirmed final preset/options.
- Preview and final render use the same resolved style path.
- `captions.json`, `source-meta.json`, and `public/source.mp4` exist.
- Stills show the right cue at the right frame.
- Karaoke highlight, if enabled, follows the spoken word.
- The final video duration, dimensions, audio, and caption placement match expectations.
