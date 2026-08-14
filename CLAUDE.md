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

cut-as-code is **a stack of agentic video-editing skills**, not an application. Each
directory under `skills/<name>/` is a self-contained skill: a `SKILL.md` (the agent
playbook — read it first), plus `scripts/`, `examples/`, and `reference/`. There is no
root build, package manifest, lint config, or aggregate test suite. Scripts and skill-local
checks run ad hoc. When you change a skill, the SKILL.md *is* the spec; keep it and its
scripts in sync.

Each `SKILL.md` starts with YAML frontmatter (`name:`, `description:`) — the `name` is the
slash-command trigger for that skill.

## Skills

| Skill | Job | Stack |
|---|---|---|
| `video-understand` | Shared media probe, word-level transcript, objective analysis, and evidence-backed semantic understanding | Python · ffprobe · faster-whisper |
| `video-cut` | Raw long video → compact first cut (download, transcribe, diagnose, hand-written JSON cut plan, varispeed, render, self-check) | Python · yt-dlp · ffmpeg · faster-whisper |
| `video-edit-compare` | Original versus actual final pixels projected onto the source clock | Python · ffmpeg · Pillow |
| `video-color-grade` | Assess footage → corrective base + named looks → human picks → bake `.cube` LUT + apply | Python · ffmpeg · numpy · Pillow |
| `video-add-b-roll` | Selective transcript-timed visual cutaways from local media or Pexels, with provenance, review, and normalized overlays | Python · ffmpeg · Pillow · Pexels API |
| `video-add-graphic-motion` | Add selective licensed web-sourced motion graphics as deterministic overlays | HyperFrames · Python · Pillow |
| `video-add-captions` | Preset-driven, word-timed captions with optional karaoke | HyperFrames · ffmpeg |
| `video-add-content-cards` | Add selective transcript-timed titles, lower-thirds, statistics, quotes, and chapter cards | HyperFrames · ffmpeg |
| `video-to-shorts` | Find, review, and render short vertical clips from long-form video | Python · ffmpeg |

## Shared project protocol V1

- Skills are optional and composable; there is no fixed global pipeline. A project can run
  cards directly or cut → color grade → cards.
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
- Domain decisions remain in `work/cut/edit-plan.json`,
  `work/color-grade/grade-plan.json`, `work/b-roll/broll-plan.json`,
  `work/graphic-motion/graphic-motion-plan.json`,
  `work/content-cards/cards-plan.json`, `work/captions/captions-plan.json`, and
  `work/shorts/shorts-plan.json`.
- When several pixel operations are active on one sequence, the canonical order is
  `cut -> color-grade -> b-roll -> captions -> content-cards -> graphic-motion`.
  This relative order applies to every selected pair among captions, content cards,
  and graphic motion. Captions establish a reserved subtitle region that neither
  downstream operation may occupy.
- For content cards and graphic motion, the visible face and head silhouette of every
  primary or foreground person, speaker, presenter, interviewee, or semantically important
  person is a hard exclusion zone throughout the complete cue. An incidental background-only
  person who is not a narrative or visual focus is exempt; when classification is uncertain,
  protect the person. If an overlay intersects a protected face or head, reposition it first,
  then scale or redesign it; skip the cue if no compliant placement exists.
- B-roll adds a `b-roll` track and changes video pixels only; it leaves timeline, geometry,
  and audio untouched. Shots carry real probe/byte/SHA-256/provenance records, are normalized
  to timeline dimensions and exact rational FPS with the selected LUT pre-applied when color
  grade is active, and pass a two-stage gate: exact-candidate review, then a completed
  visual review bound to the final delivery. Missing or weak media becomes `skipped` — an
  approved all-skipped plan is a valid no-op. Never substitute fallback media.
- Caption cues use program time mapped from the canonical source transcript through
  `timeline.json`; they preserve source evidence and contribute a transparent PNG sequence
  overlay at the exact rational timeline FPS. Browser runtime assets must be local and hashed.
- Graphic-motion cues require verified video understanding, exact permissive source licenses,
  frozen local source/port/review hashes, deterministic native HyperFrames time, and transparent
  PNG sequence overlays at the exact rational timeline FPS. The shared compiler revalidates
  the plan and every delivery binding before rendering.
- Shorts consume the verified main delivery plus a program-time transcript. The `shorts`
  operation is present in the DAG but absent from `sequences.main.operations`, so derivative
  media under `final/shorts/` never changes or re-renders the main delivery.
- Human and explicitly delegated Agent decisions are both valid when the domain receipt
  names the decision mode, binds reviewed artifacts by hash, and stores a non-empty rationale.
  Never write a fake human response for an Agent decision.
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
- Image-sequence overlays declare `asset_type`, a basename-only printf `pattern`,
  `start_number`, and rational `fps`; the compiler requires the directory, first frame, and
  FPS match before delivery rendering.

## Architecture that spans skills

These conventions are shared and load-bearing — match them in any new skill:

- **`projectlib.py` is the shared runtime.** `skills/video-understand/scripts/projectlib.py`
  is imported directly (no package install) by every multi-skill script. It owns: project JSON
  validation, revision/staleness checks, `map_transcript_to_timeline`, `build_render_plan`,
  and durable `write_json`. Any new cross-skill script imports it by putting it on `sys.path`
  or running from a directory where it's co-located.

- **The transcript is the shared interchange format.** `skills/video-understand/scripts/transcribe.py`
  is the canonical transcriber (faster-whisper, CPU/int8, VAD, word-level). It emits
  `transcript.json` = `segments[] → words[]` with per-word `start`/`end`. Note it is
  **English-only** (`base.en`, `language="en"`); for other languages the caller swaps the
  model/lang — downstream scripts only consume the resulting JSON.

- **Code is the edit.** No timeline scrubbing. The edit is always text you can read, diff,
  and re-render: a JSON cut plan (`edit_coarse.json`/`edit_final.json`), a `looks.json`, an
  `cards-plan.json`, or caption cues. Beats land on the spoken word by grepping the
  transcript for the phrase and reading its `start` time.

- **Human decides content; scripts do precision.** Editorial calls (what to keep, which
  look, what a card says) are hand-authored; scripts handle boundary alignment, dead-air
  reclaim, varispeed, LUT baking, compositing.

- **`work/` for intermediates, deliverable to project root / `out/`.** Outputs go to the
  passed `--out` dirs (durable), never a system temp dir.

- **API keys come from skill-local `.env`, never from chat or argv.** `video-add-b-roll`
  reads `PEXELS_API_KEY` from the environment first, then
  `skills/video-add-b-roll/.env` (gitignored). If both are blank, stop and ask the user to
  add it to that file. Never put a key in a command argument, plan, URL, log, review
  artifact, or response.

- **Self-check is non-negotiable.** Every skill ends by verifying its own output
  (re-transcribe the cut, screenshot stills, eyeball a card/skin strip) before declaring
  done. Don't skip it.

- **Two render families:**
  - *ffmpeg/Python* standalone operations copy audio when they do not change time. The
    shared delivery renderer encodes audio after cuts, concatenation, varispeed, or an
    audio filter; otherwise it uses `-c:a copy`.
  - *HyperFrames* (`video-add-captions`, `video-add-content-cards`, `video-add-graphic-motion`) renders transparent
    overlays at the source dimensions, then ffmpeg-composites them onto the source.

- **Review before delivery.** Color grade records a human or delegated agent look choice;
  content cards uses interview and candidate-review gates before rendering.

## Windows / ffmpeg gotchas (this repo is developed on Windows)

- **Drive-colon paths break ffmpeg filtergraph options that take a path** (`lut3d`,
  `metadata=print:file=`). The pattern used throughout: run ffmpeg with `cwd` set to the
  file's folder and reference it by **basename**. Keep this for any new path-taking filter.
- **Never use ffmpeg `drawtext` for labels.** The `fontfile` drive-colon path is
  unreliable on Windows. Render text to a PIL PNG and overlay it (see `video-color-grade`).
  Fonts are configured at the top of the relevant script.
- **Bash `grep`/`sed` one-liners in SKILL.md won't run in PowerShell.** Capture ffmpeg
  output to a file and parse with Python instead.

## Common commands

There is no root build, package manifest, or aggregate runner. Pipeline commands live inside
each `SKILL.md`; the checks below are the repo-wide ones. Run everything from the repo root.

Sanity-check tool availability before running a pipeline:
`ffmpeg -version`, `ffprobe -version`, `yt-dlp --version`,
`python -c "import faster_whisper"`, `python -c "import PIL"`, `node --version` (>= 22, for
the HyperFrames `.mjs` scripts in `video-add-captions`).

```bash
# transcribe (the shared step) — produces transcript.json + .srt
ffmpeg -y -i work/source.mp4 -ac 1 -ar 16000 work/audio16k.wav
python skills/video-understand/scripts/transcribe.py work/audio16k.wav work/transcript
```

### Tests and checks

Tests are plain `unittest` modules under `skills/<name>/tests/`; each puts its own
`scripts/` and `video-understand/scripts/` on `sys.path`, so no install or `PYTHONPATH` is
needed. There is no discover root that covers them all — run them per skill:

```bash
python -m unittest skills/video-add-b-roll/tests/test_broll.py          # 155 tests, ~50s
python -m unittest skills/video-add-graphic-motion/tests/test_graphic_motion_plan.py
python -m unittest skills/video-cut/tests/test_inspect_bounds.py
python -m unittest skills/video-edit-compare/tests/test_make_compare.py

# one test case / one test
python -m unittest skills.video-cut.tests.test_inspect_bounds.InspectBoundsTests -v
python -m unittest skills/video-add-b-roll/tests/test_broll.py -k pexels -v
```

`check_*.py` scripts are self-contained regression harnesses with fixtures baked in — they
take no project argument and print a `passed` line per check:

```bash
python skills/video-understand/scripts/check_protocol_extensions.py   # shared protocol
python skills/video-cut/scripts/check_project_protocol.py
python skills/video-add-captions/scripts/check_project_protocol.py
python skills/video-to-shorts/scripts/check_project_protocol.py      # wraps check_review_ui.py
node skills/video-add-captions/scripts/check_caption_style_config.mjs
node skills/video-add-captions/scripts/check_caption_interaction.mjs
```

Some b-roll tests shell out to ffmpeg and print `UnicodeDecodeError` tracebacks from
subprocess reader threads on Windows (non-UTF-8 ffmpeg output). Those are noise — trust the
final `OK`/`FAILED` line. As of this writing `video-to-shorts/scripts/check_review_ui.py`
has 2 pre-existing failures (`fake_render()` missing `video_preset`); everything else above
passes.

Prefer `python -m unittest` over `pytest` — the suites use `unittest` fixtures and
`mock.patch` throughout, and no pytest config exists.

## Repo conventions

- **`CLAUDE.md` and `AGENTS.md` must stay byte-identical.** They were once hardlinked but
  are now separate files; apply every edit to both.
- `work/`, `docs/`, `/tests/`, and `.env` are gitignored — only `skills/` plus the root docs
  are tracked. A video project lives *outside* the repo and is addressed by an explicit
  project root, so scripts take paths, never assume cwd is the project.
- **Never commit `docs/` — including `docs/superpowers/` — under any circumstance.** It is
  local scratch and vendored material. Never stage it, never force-add it (`git add -f`),
  and never remove it from `.gitignore`. If a commit or PR would include anything under
  `docs/`, drop those paths and say so instead of committing them.
- `.github/workflows/clawhub-publish.yml` publishes `skills/` to ClawHub (dry-run on PRs,
  real publish on `main`). A skill directory's `SKILL.md` frontmatter `name` is its published
  slug and slash-command trigger — renaming a directory renames the command.
- Editor UI work under `ui/` must use Playwright with installed Chrome for screenshot-based visual inspection and interaction verification; typecheck/build alone are insufficient.
