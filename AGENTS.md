# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git

> **🔒 This section must never be modified.** Leave it byte-for-byte unchanged.

- Prefer small PRs focused on one feature, one bug fix, one chore, or one refactor.
- Use branches:
  - `feat/<short-name>`
  - `fix/<short-name>`
  - `chore/<short-name>`
  - `refactor/<short-name>`
  - `docs/<short-name>`
- Use Conventional Commit style for PR titles:
  - `feat(editor): add marquee selection`
  - `fix(runtime): handle missing tween state`
  - `docs(agents): update collaboration rules`
- PR descriptions must include:
  - What changed
  - Why it changed
  - How it was checked
- Default to squash merge.

## What this repo is

Open-Recut is **a stack of agentic video-editing skills**, not an application. Each
directory under `skills/<name>/` is a self-contained skill: a `SKILL.md` (the agent
playbook — read it first), plus `scripts/`, `examples/`, and `reference/`. There is no
root build, package manifest, or lint config. Protocol and ffmpeg integration checks live
under `tests/` and use Python `unittest`. When you change a skill, the SKILL.md *is* the
spec; keep it, scripts, and tests in sync.

## The nine skills

| Skill | Job | Stack |
|---|---|---|
| `video-understand` | Shared media probe, word-level transcript, objective analysis, and evidence-backed semantic understanding | Python · ffprobe · faster-whisper |
| `video-rough-cut` | Raw long video → compact first cut (download, transcribe, diagnose, hand-written JSON cut plan, varispeed, render, self-check) | Python · yt-dlp · ffmpeg · faster-whisper |
| `video-edit-compare` | Original versus actual final pixels projected onto the source clock | Python · ffmpeg · Pillow |
| `video-color-grade` | Assess footage → corrective base + named looks → human picks → bake `.cube` LUT + apply | Python · ffmpeg · numpy · Pillow |
| `video-overlay-cards(legacy)` | Composite intro/chapter/lower-third/outro cards onto a video (no re-cut) | Python · ffmpeg · Pillow |
| `video-add-captions` | Every-line styled subtitles, optional karaoke | Remotion (React/TS) · ffmpeg · faster-whisper |
| `video-to-remotion(legacy)` | Watch content → auto-generate *selective* motion graphics (lower-thirds, stats, chapter cards) | Remotion (React/TS) · ffmpeg · faster-whisper |
| `video-add-content-cards` | Shared semantic moments → HyperFrames HTML/GSAP overlay contribution | HyperFrames · ffmpeg |
| `design-frames-to-motion(legacy)` | Rebuild designer PNG frames as parametric Remotion components, transcript-synced | Remotion (React/TS) · ffmpeg |

## Shared project protocol V1

- Skills are optional and composable; there is no fixed global pipeline. A project can run
  cards directly or rough cut → color grade → cards.
- `work/project.json` is the only shared manifest. It records operation dependencies,
  statuses, render contributions, integer `revision` values, and `based_on` checks.
- `work/timeline.json` is the custom one-source, chronological source-to-program mapping.
  V1 does not use OpenTimelineIO or support reordered/duplicated clips or nonlinear speed.
- Canonical time values are seconds. All ranges are half-open `[start_s, end_s)` and use
  explicit `source_range` and `program_range` objects.
- Each operation declares a `target` (`sequence` and scope) and `effects` such as timeline,
  pixel, geometry, audio, or added-track changes.
- Render contribution kinds are `timeline-transform`, `video-filter`, `audio-filter`,
  `overlay`, `precomputed-asset`, and `output-constraint`.
- Domain decisions remain in `work/rough-cut/edit-plan.json`,
  `work/color-grade/grade-plan.json`, and `work/content-cards/cards-plan.json`.
- User-facing files live in `input/`, `review/`, and `final/`; `work/cache/` is disposable.
- Compile approved active operations with `build_render_plan.py`, then render delivery once
  with `render_project.py`. Timeline changes require audio filtering/encoding; `-c:a copy`
  is valid only when no active operation cuts, concatenates, retimes, or filters audio.
- `video-edit-compare` runs after final delivery and supports only
  `original-vs-final-source-time`.
- Default review uses stills, contact sheets, boundary reels, and short previews. Render a
  full-length intermediate only when a whole-program pacing decision requires it.
- Preserve compatibility adapters for current edit, looks, and cue formats until every
  documented consumer has migrated.

## Architecture that spans skills

These conventions are shared and load-bearing — match them in any new skill:

- **The transcript is the shared interchange format.** `skills/video-understand/scripts/transcribe.py`
  is the canonical transcriber (faster-whisper, CPU/int8, VAD, word-level). It emits
  `transcript.json` = `segments[] → words[]` with per-word `start`/`end`. The Remotion
  skills (`video-add-captions`, `video-to-remotion`) deliberately reuse it via a relative
  path (`../video-rough-cut/scripts/transcribe.py`) rather than copying. Note it is
  **English-only** (`base.en`, `language="en"`); for other languages the caller swaps the
  model/lang — downstream scripts only consume the resulting JSON.

- **Code is the edit.** No timeline scrubbing. The edit is always text you can read, diff,
  and re-render: a JSON cut plan (`edit_coarse.json`/`edit_final.json`), a `looks.json`, an
  `overlays.json`, or a Remotion cue sheet. Beats land on the spoken word by grepping the
  transcript for the phrase and reading its `start` time.

- **Human decides content; scripts do precision.** Editorial calls (what to keep, which
  look, what a card says) are hand-authored; scripts handle boundary alignment, dead-air
  reclaim, varispeed, LUT baking, compositing.

- **`work/` for intermediates, deliverable to project root / `out/`.** Outputs go to the
  passed `--out` dirs (durable), never a system temp dir.

- **Self-check is non-negotiable.** Every skill ends by verifying its own output
  (re-transcribe the cut, screenshot stills, eyeball a card/skin strip) before declaring
  done. Don't skip it.

- **Two render families:**
  - *ffmpeg/Python* standalone operations copy audio when they do not change time. The
    shared delivery renderer encodes audio after cuts, concatenation, varispeed, or an
    audio filter; otherwise it uses `-c:a copy`.
  - *Remotion/React* (`captions`, `to-remotion`, `design-frames-to-motion`): default to
    rendering a **transparent overlay** (ProRes 4444) at the **source's own resolution**,
    then ffmpeg-composite onto the source (`-c:a copy`). The full-frame `<OffthreadVideo>`
    path is the slow fallback for very short clips only — it decodes the source every frame.

- **`color-grade` and `to-remotion`/`overlay-cards` are two-phase by design:** present
  options (look contact sheet, draft cues) and STOP for the human pick before the full
  render / LUT bake.

## Windows / ffmpeg gotchas (this repo is developed on Windows)

- **Drive-colon paths break ffmpeg filtergraph options that take a path** (`lut3d`,
  `metadata=print:file=`). The pattern used throughout: run ffmpeg with `cwd` set to the
  file's folder and reference it by **basename**. Keep this for any new path-taking filter.
- **Never use ffmpeg `drawtext` for labels.** The `fontfile` drive-colon path is
  unreliable on Windows. Render text to a PIL PNG and overlay it (see `video-color-grade`
  and `video-overlay-cards`). Fonts are configured at the top of the relevant script.
- **Bash `grep`/`sed` one-liners in SKILL.md won't run in PowerShell.** Capture ffmpeg
  output to a file and parse with Python instead (e.g. scene detection in `video-to-remotion`).
- **Remotion:** pin one Remotion 4.x and **`react`/`react-dom` to `18.3.1`** (don't let npm
  pull React 19 against an older Remotion). `OffthreadVideo` resolves `staticFile()` only
  from `public/`, so the source must live at `public/source.mp4`.

## Common commands

There is no aggregate runner; commands live inside each `SKILL.md` pipeline. Canonical ones:

```bash
# transcribe (the shared step) — produces transcript.json + .srt
ffmpeg -y -i work/source.mp4 -ac 1 -ar 16000 work/audio16k.wav
python skills/video-understand/scripts/transcribe.py work/audio16k.wav work/transcript

# Remotion render (overlay path) — run from inside the scaffolded project
npx remotion still src/index.ts <Comp> work/stills/f295.png --frame=295
npx remotion render src/index.ts <Comp>Overlay out/overlay.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
```

Sanity-check tool availability before running a pipeline:
`yt-dlp --version`, `ffmpeg -version`, `python -c "import faster_whisper"`.
