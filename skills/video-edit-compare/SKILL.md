---
name: video-edit-compare
description: >
  Build a side-by-side visualization that shows what an edit kept, cut, and changed.
  LEFT = original (full length), RIGHT = the edited version laid on the SAME original
  timeline with every removed span filled black; one shared (original) audio track;
  perfectly time-synced. Use when asked to "see the edit", "compare original vs cut",
  "可视化对比/对比视频/直观看剪掉了哪些", or to review an edit plan (in/out keep+drop
  spans, e.g. edit_final.json) before trusting the cut. Pairs with video-rough-cut.
---

# Video Edit Compare (split-screen diff)

Make the edit legible at a glance: left plays the untouched original; right plays the
same footage on the original timeline but goes BLACK wherever a span was removed.
Because both sides share the original timeline and audio, you literally watch the cut
parts blink out while still hearing them — so kept / cut / changed is obvious.

## When to use
- You have an edit plan with keep spans (in/out) and want to visually verify it.
- Someone asks for a comparison/preview of original vs edited.
- NOT for delivering the actual cut (that's the rough-cut render) — this is a review aid.

## Inputs
- The original video (same one the plan was built from).
- An edit JSON with a `keep` list of `{in, out}` (seconds) and `source_duration_s`.
  Drops are derived as the complement of keep over `[0, source_duration_s]`.

## How it works (ffmpeg, one pass)
1. Decode source once, `split` into LEFT and RIGHT copies (scale both to per-side WxH).
2. LEFT: `drawtext=ORIGINAL`.
3. RIGHT: `drawbox=t=fill:color=black:enable='between(t,a1,b1)+between(t,a2,b2)+...'`
   over every DROP span (quote the enable expr so its commas don't split the graph),
   then `drawtext=CUT` (after the box so the label stays visible on black).
4. `hstack` the two; map `[v]` + original `0:a:0`.
5. Encode `libx264 -profile:v main -level 4.0 -pix_fmt yuv420p -movflags +faststart`
   (broadly playable; needed on systems lacking modern codecs).

Granularity = whatever spans you feed it: coarse blocks → few long blackouts (clear
overview); micro-trimmed segments → right side also blinks black on every trimmed
pause (exact, but flickery). Use a TTF via `fontfile=` (escape the `:` in Windows
paths, e.g. `C\:/Windows/Fonts/arialbd.ttf`).

## Verify before full render
Render ~20 s first, grab one frame inside a drop (right = black) and one inside a keep
(both identical), eyeball the labels, then render full length (long; run in background).

## Reference script
`scripts/make_compare.py <edit.json> <source.mp4> <out.mp4> [--filter-only]`
— derives drop spans, writes the filtergraph, renders. Tune `W,H,FPS,FONT` at the top.
