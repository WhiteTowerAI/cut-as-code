---
name: video-color-grade
description: >
  Color-grade any video by writing the grade from scratch as code, then letting a human
  choose the look. First ASSESS the footage (flat LOG/S-Log/HLG vs already-Rec.709, white-
  balance cast, exposure), build ONE corrective base (log->Rec.709, or WB+exposure+contrast
  for normal footage), then generate 5-6 DISTINCT NAMED looks on top (clean_neutral /
  warm_filmic / cool_desat / teal_orange / punchy_vibrant / vintage_faded), rendered on the
  same representative frame and presented as a labeled side-by-side contact sheet + a zoomed
  face/skin strip so the user picks one. After the pick: bake the chosen look to a portable
  .cube LUT and apply it to the full clip (audio copied, duration/fps/dims kept), with verify.
  Skin tone is the quality bar; no preset packs. Use when asked to "color grade / colour
  grade / regrade this", "make some looks and let me choose", "fix the white balance / it
  looks too flat / muted / too warm", "give it a cinematic / teal-orange / film look",
  "convert S-Log/log to Rec.709", "bake a LUT / .cube", 调色, 校色, 给视频做调色/电影感/青橙调色,
  把 log 转 Rec.709, 出几个调色风格让我选, 生成 LUT. NOT for cutting footage (video-rough-cut),
  every-line subtitles (video-to-captions), overlay cards/lower-thirds (video-overlay-cards),
  or motion graphics (video-to-remotion).
---

# Video Color Grade (assess → correct → looks → choose → LUT + apply)

Write the grade from scratch as code, generate several distinct **named looks** on the real
footage, present them side-by-side, let the human **pick one**, then bake a portable `.cube`
LUT and apply it to the full clip. No preset packs.

**Core idea — correct, then style.** Every look is `corrective base + creative layer`:

- **corrective base** makes the footage *honest* — for flat LOG/HLG it's the log→Rec.709
  conversion; for already-Rec.709 footage it's WB neutralize + exposure + mild contrast.
  Every look shares this base, so "neutral" stays meaningful and looks differ by *intent*.
- **creative layer** is the look stacked on top (warm / cool / teal-orange / punchy / faded…).

**Skin is the quality bar.** On people — especially darker skin — `teal_orange` and
`cool_desat` routinely throw a green/grey cast. Judge every look on faces first; keep midtone
warmth, push the tint into shadows/highlights/background, prefer `vibrance` over raw
`saturation`. Don't push the white balance all the way to neutral or skin goes lifeless.

Requirements: `ffmpeg`/`ffprobe` on PATH, Python with `numpy` + `Pillow`.

## Contract
- Every look = `base + creative layer`; the base is shared by all looks.
- All looks render on the **same** representative frame (a fair, controlled comparison),
  labeled, at full resolution.
- The full apply uses **`-c:a copy`** (audio never re-encoded → A/V sync identical) and keeps
  source **duration, fps, dimensions**.
- **Two-phase by design:** present the looks and STOP — never render the full video or bake a
  LUT until the human has chosen.

## Inputs
- The source video.
- A `looks.json` (`base` + named `looks`); start from `looks.example.json` and **retune the
  `base`** from what `assess.py` reports.

## looks.json schema
```jsonc
{
  "base": "<corrective base: log->Rec.709 conversion, OR WB+exposure+contrast for normal footage>",
  "looks": [
    { "name": "clean_neutral", "label": "1 · CLEAN NEUTRAL", "desc": "corrected only", "chain": "eq=contrast=1.02" },
    { "name": "teal_orange",   "label": "4 · TEAL & ORANGE", "desc": "cinematic",      "chain": "colorbalance=...,eq=..." }
    // a look's full ffmpeg filter = base + "," + chain. Set "prepend_base": false to use chain standalone.
  ]
}
```

## Workflow

1. **Assess — never grade blind.**
   ```
   python scripts/assess.py SOURCE.mp4 --out work/
   ```
   Reports log-vs-Rec.709, white-balance cast (signalstats U/V vs 128), exposure (Y), picks a
   representative frame (`work/assess/frame.png`), and suggests base tweaks. **Retune
   `looks.json` `base`** accordingly (e.g. warm cast → add a little blue; log → put the
   log→709 conversion in `base`).
   - **The rep frame is picked by median luma, not by faces.** On a single-shot talking-head
     that usually lands on a good face frame, but on B-roll-heavy / multi-shot footage it can
     pick a faceless frame — and then `face_skin_check.png` is useless (skin is the quality
     bar). Force a known face moment with `--frame-time SECONDS`.
   - The WB/exposure stats come from **one ~10s `signalstats` window at 10% of duration**
     — fine for constant light; for footage whose light changes, move/lengthen it with
     `--win-start SECONDS` / `--win-dur SECONDS`.

2. **Render the looks for choosing.**
   ```
   python scripts/render_looks.py work/assess/frame.png looks.json --out work/looks
   ```
   Produces `work/looks/looks_compare.png` (original + every look, labeled, full-res) and
   `face_skin_check.png` (zoomed skin strip). **LOOK at both.** Skin is the bar — retune or
   drop any look that greys/greens skin, then re-render. Off-center subject? add
   `--face-crop W:H:X:Y`.

3. *(optional)* **Motion previews** of the top 2–3 so they're seen moving (audio kept):
   ```
   python scripts/make_clips.py SOURCE.mp4 looks.json --out work/clips \
     --pick clean_neutral,warm_filmic,teal_orange --with-original --ss 148 --t 8
   ```

4. **Present + STOP.** Show the contact sheet (and clips), name each look, ask the human to
   pick one number. **Do not render the full video yet.**

5. **After the pick — bake the LUT and apply to the full clip.**
   ```
   python scripts/bake_lut.py looks.json --name CHOSEN \
     --out out/CHOSEN.cube --verify-frame work/assess/frame.png
   python scripts/apply_grade.py SOURCE.mp4 --looks looks.json --name CHOSEN --out out/graded.mp4
   #   or apply the baked LUT instead of the chain:  --lut out/CHOSEN.cube
   ```
   `apply_grade.py` verifies duration/audio are kept, prints the WB shift (U/V toward 128),
   and drops a spot frame to eyeball.
   - **The apply re-encodes the video once (lossy); audio is `-c:a copy`.** Quality/time are
     set by `--crf` (default 18) and `--preset` (default `slow`). `slow` is fine for small/
     short clips, but on 1080p/4K hour-long footage it's a large, silent time cost — drop to
     `--preset medium` for delivery (or `veryfast` for a quick preview), `slow` only for final.
   - **Match the delivered video to the delivered LUT:** the chain (`--name`) and the baked
     33³ `.cube` (`--lut`) can differ by up to ~5/255 on steep curves (`bake_lut.py` reports
     this `max|d|`). Invisible for most work, but if you're *shipping the `.cube`* and want the
     rendered video to match it exactly, apply with **`--lut out/CHOSEN.cube`**, not `--name`.

## Design notes / gotchas
- **Grade the CLEAN cut, then composite overlays on top of the graded footage.** If you must
  grade a video that already has burned-in captions/cards, do NOT trust `assess.py`: its WB/
  exposure stats and frame pick are skewed by the graphics (dark top/bottom scrims drag Y down,
  bright caption text / teal accents skew U/V, and the frame pick can land on a caption-heavy
  frame) — you'd be correcting the overlays, not the footage. Reuse a `base` tuned on the clean
  footage, and expect the grade to tint the overlays, so use only a subtle/corrective look
  (`clean_neutral`); `teal_orange`/`vintage_faded` will visibly recolor the text/accents.
- **One look/LUT covers all related clips.** Once you've picked a look, reuse the same
  `looks.json` / `.cube` across every related clip (e.g. clean cut + the overlaid version) —
  do NOT re-run the two-phase pick per clip.
- **Correct, then style.** The base is the generalization of the deck's S-Log3→Rec.709 step.
  For normal footage the base is WB+exposure+contrast; for log footage put the conversion there.
- **Skin first.** `teal_orange`/`cool_desat` are the usual skin offenders on darker subjects —
  keep midtones warm, tint shadows/highlights/bg, use `vibrance`. Don't neutralize U/V fully.
- **Labels are PIL PNGs overlaid by ffmpeg — never `drawtext`.** On Windows the `drawtext`
  `fontfile` path (drive colon) is unreliable. Fonts are set at the top of `gradelib.py`.
- **Drive-colon paths break ffmpeg filtergraph options** that take a path (`lut3d`,
  `metadata=print:file=`). The scripts run ffmpeg with `cwd` = the file's folder and reference
  it by **basename**. Keep this pattern for any new path-taking filter.
- **Outputs land in the `--out` dirs you pass** (durable), not a system temp dir.
- **The face/skin strip uses a fixed centered upper-middle crop, not face detection.** If the
  subject isn't roughly centered, pass `--face-crop W:H:X:Y` to `render_looks.py` or the skin
  strip will show the wrong region.
- **`apply_grade.py`'s verify spot frame is at 20% of duration** — a *different* frame than the
  one the looks were chosen on. If that 20% point is faceless, eyeball skin on another frame
  instead (or pass `--frame-time` to `assess.py` so the chosen frame is a known face moment).
- **The LUT bake is exact**, because every filter here is a per-pixel point op: `bake_lut.py`
  pushes a 33³ identity grid through the real chain and self-checks against it
  (`mean|d|` should be well under 1/255; a few-level `max|d|` is just interpolation).
- **Two-phase, always.** Never bake the full render before the human chooses — that's the
  whole point of "make some examples and let me choose."
