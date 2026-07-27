---
name: video-cut
description: >
  End-to-end turn an unedited long-form talking-head / vlog / podcast video into a
  compact "first cut" (rough cut). Use when asked to edit/剪辑 a raw YouTube (or
  local) video into a tighter version: download, word-level transcribe, diagnose
  bad-edit spots (slow intro, fillers, dead air, tangents, rambling), decide cuts
  in a JSON edit plan (each kept/dropped span with in/out + a one-line reason),
  render with ffmpeg, then self-check the result (re-transcribe + frame/black/
  silence checks). Triggers: "剪成第一版", "rough cut", "first cut", "压缩时长",
  "把这条原片剪短", "cut down this video".
---

# Video Cut

Turn one unedited long video into a compact, watchable **first cut** — decisive,
content-aware, and self-verified. Human (you, the model) makes the *editorial*
decision of WHAT to keep; the bundled scripts do the mechanical precision (boundary
alignment, dead-air reclaim, memory-safe render, self-check).

## When to use
- A raw/unedited video (YouTube URL or local file) needs to become a tighter cut.
- The ask is "halve it", "cut the boring parts", "make a first/rough cut".
- NOT for: word-by-word filler micro-surgery, multi-cam B-roll assembly, color/audio
  polish — those are a later P1/P2 polish pass. This skill is P0: validate the
  diagnosis + produce a solid cut.

## Dependencies
`/video-understand` is a prerequisite. Run it first and use its validated media,
transcript, analysis, and timeline instead of recreating them in this skill.
Before starting, verify that it is installed. If it is not, warn the user that
this prerequisite is missing and stop before processing media.

Activate any environment that has these (do NOT assume a specific conda env name):
- `yt-dlp` (download), `ffmpeg`/`ffprobe` (cut/render/probe) on PATH
- Python with `faster-whisper` (CPU works: `device=cpu, compute_type=int8`)
Check first: `yt-dlp --version`, `ffmpeg -version`, `python -c "import faster_whisper"`.

## Project protocol workflow

Use these durable project files:

```text
work/cut/edit-plan.json          # hand-authored keep/drop decisions only
work/timeline.json               # generated precision ranges + source/program mapping
review/01-cut/cut-summary.md
review/01-cut/timeline-map.png
review/01-cut/boundary-review.mp4
review/01-cut/full-proxy.mp4  # optional whole-program pacing review
```

Each canonical decision has a stable `id`, `action` (`keep` or `drop`), `start_s`,
`end_s`, `reason`, and semantic/transcript `evidence_refs`. Keep decisions chronological;
V1 does not support reordered or duplicated source clips.

Reuse the shared evidence layer rather than transcribing or diagnosing again:

```powershell
python skills/video-understand/scripts/transcribe.py work/cache/audio16k.wav work/understand/transcript
python skills/video-understand/scripts/analyze.py work/understand/transcript.json work/understand/analysis.json
```

The existing precision scripts accept the canonical plan. Expand word-safe boundaries,
optionally assign linear varispeed, then generate the shared timeline:

```powershell
python skills/video-cut/scripts/build_edit.py work/cut/edit-plan.json work/understand/transcript.json work/cache/edit-final.json
python skills/video-cut/scripts/assign_speed.py work/cache/edit-final.json work/understand/transcript.json
python skills/video-understand/scripts/build_timeline.py work/cache/edit-final.json work/timeline.json --fps-num SOURCE_FPS_NUM --fps-den SOURCE_FPS_DEN
```

Use the exact rational FPS from `work/understand/media.json`; never round `30000/1001` to
`30/1`. Review `timeline-map.png` and the short `boundary-review.mp4`. Generate
`full-proxy.mp4` only when whole-program pacing must be reviewed. Write the result to
`cut-summary.md` and point the operation check report at that file.

Record the timeline contribution with its required source input, update the operation integer
`revision`, and set `based_on` to the exact understanding revision consumed:

```json
"render": {
  "kind": "timeline-transform",
  "input": "../input/original-video.mp4",
  "plan": "timeline.json"
}
```

The shared delivery renderer encodes the active sequence after all revision checks pass.

## Standalone compatibility workflow

The legacy files and commands below remain supported during migration. `build_edit.py`
accepts both `edit_coarse.json` and canonical `decisions[]`; `cut_render.py` accepts both
`edit_final.json` and `timeline.json`; this skill's `transcribe.py` is a compatibility
wrapper around `../video-understand/scripts/transcribe.py`.

Keep all intermediates under `work/`, deliver to project root:
```
work/source.mp4            # downloaded original
work/audio16k.wav          # 16k mono audio for whisper
work/transcript.json/.srt  # word-level timestamps
work/analysis.json         # diagnosis (silences/fillers/runs)
work/edit_coarse.json      # *** YOUR editorial decision (hand-written) ***
work/edit_final.json       # expanded tight render segments (generated; carries per-segment speed)
work/selfcheck/            # cut re-transcript + join frames
first_cut.mp4              # THE DELIVERABLE
first_cut_report.md        # edit + self-check report
```

## The pipeline (6 steps)

### 1. Download
Highest accessible quality + audio. The default player client often fails
(not-available / DRM / sign-in). The reliable fallback is the **android** client:
```
yt-dlp --extractor-args "youtube:player_client=android" \
       -o work/source.mp4 "<URL>"
```
If only a muxed 360p (format 18) is reachable without login, accept it and document
the constraint — HD DASH is frequently DRM/login-gated. Then extract audio:
```
ffmpeg -y -i work/source.mp4 -ac 1 -ar 16000 work/audio16k.wav
```

### 2. Transcribe (word-level)
```
python scripts/transcribe.py work/audio16k.wav work/transcript [base.en]
```
Produces `work/transcript.json` (segments + per-word start/end) and `.srt`.
faster-whisper, CPU/int8, VAD on, `word_timestamps=True`.
**Non-English:** pass a multilingual model + `--lang`, e.g.
`python scripts/transcribe.py work/audio16k.wav work/transcript medium --lang zh`
(the `.en` models are English-only). Verify the language on a short sample first.
**Note:** Whisper strips most vocalized "um/uh" — they are NOT transcript-measurable,
so filler detection must combine the lexical word-search below with silence-gap
analysis, not rely on the transcript text alone.

### 3. Diagnose ("see" + "read")
```
python scripts/analyze.py work/transcript.json work/analysis.json
```
Surfaces: leading/trailing dead air, inter-word silences ≥0.8s (with the word they
follow), filler counts, wpm, speaking_ratio, near-duplicate repetitions, monologue
runs >40s (ramble candidates).

To **see** the picture, sample a frame every ~2s into a contact sheet and read it
yourself; confirm scene structure / hunt black or junk frames:
```
ffmpeg -y -i work/source.mp4 -vf "fps=1/2,scale=240:-1,tile=10x10" -frames:v 1 work/contact.png
ffmpeg -i work/source.mp4 -vf "blackdetect=d=0.1:pic_th=0.98" -an -f null -
```
For a single static talking-head shot there are no scene cuts — expect this, and
note that the later jump-cuts are normal, not glitches.

### 4. Decide the cut — write `edit_coarse.json` BY HAND
This is the editorial core. Read the transcript + analysis, then write a coarse plan
of **keep-blocks and drop-spans that tile the entire timeline with no gaps/overlaps**,
each with `in`, `out`, and a one-line `reason`. Compress slow preamble to a few
high-value nuggets; keep substance as large blocks; drop clear tangents/rambles.
Preserve chronological order; the canonical V1 timeline rejects reordering.
Aim to roughly halve runtime.
- Format spec + a real worked example: `reference/edit_coarse.schema.md`.
- Align every block boundary to a **sentence/clause end** — never start/stop
  mid-sentence or on a stammer. Use:
  ```
  python scripts/inspect_bounds.py work/edit_coarse.json work/transcript.json
  ```
  It accepts both legacy `keep[]` and canonical `decisions[]` plans and prints the words
  straddling each boundary so you can nudge them onto clean edges.

### 5. Expand → auto-speed → render
Turn coarse blocks into tight, dead-air-free render segments, normalize the speaking
pace, then render:
```
python scripts/build_edit.py   work/edit_coarse.json work/transcript.json work/edit_final.json 1.5
python scripts/assign_speed.py work/edit_final.json   work/transcript.json   # adds per-segment speed
python scripts/cut_render.py    work/edit_final.json   work/source.mp4 first_cut.mp4
```
- `build_edit.py` splits each block at internal pauses > SPLIT_GAP (4th arg, e.g. 1.5s)
  and trims every boundary INTO the silence (LEAD 0.10s / TRAIL 0.30s) so no word is
  clipped and dead air is reclaimed. Lower SPLIT_GAP = tighter but choppier; for a
  slow, deliberate speaker prefer ~1.5, not 0.6 (avoids twitchy micro-cuts).
- `assign_speed.py` (auto varispeed) — groups render segments by `decision_ref`, measures
  the speaking pace of each hand-authored keep decision, and writes one shared `speed`
  factor plus each segment's resulting `out_dur` back into `edit_final.json`. Pace already
  inside the comfortable band stays at 1.0; out-of-band pace moves only to the nearest
  deadband edge. Adjacent decision blocks differ by at most 0.08x to avoid "pumpy" joins.
  It changes pace only — never which content is kept. Read the printed table before rendering:
  - Metric: words/min (English) — auto-switches to **chars/min for CJK** (zh/ja/ko).
  - Defaults are **first-run starting points, not validated constants**: deadband 145–185
    WPM and speed clamped to **1.0–1.3**. This is speed-up-only: slow decision blocks can
    be tightened, while natural-fast delivery remains at 1.0. Short decision blocks
    (<3.5s / <6 words) are too noisy to measure and inherit the global factor.
  - The rate is measured after dead-air reclaim, so it reads higher than gross WPM and is
    closer to articulation rate. **The printed-table review is load-bearing**: eyeball it
    and tune `deadband` to the speaker before rendering, don't trust the defaults blind.
  - Knobs (k=v): `mode=segment|global|off` (default `segment`; `global`=one factor for
    the whole video, `off`=disable), `deadband=lo,hi`, `min_speed=`/`max_speed=`,
    `min_seg=`/`min_words=`, `lang=auto|en|cjk`. To skip the feature entirely, just don't
    run this step — `cut_render.py` treats a missing `speed` as 1.0.
- `cut_render.py` uses **N separate seeked inputs + concat filter, single re-encode**.
  This is mandatory: trimming N times off ONE decoded input makes ffmpeg buffer the
  whole decoded stream (tens of GB for a long video). See `reference/pitfalls.md`.
  When segments carry a `speed`, it re-times each input (`setpts` video / `atempo` audio)
  and normalizes fps/timebase/sample-rate per input before concat so A/V stays locked;
  with no speed it falls back to the exact original graph.
- **Final comparison:** `video-edit-compare` reads the canonical timeline plus the actual
  final delivery. It projects final pixels back to source time, stretches varispeed clips
  to their source duration, and shows dropped ranges as black.

### 6. Self-check — do not declare done until this passes
```
# protocol precision regression check (run from the repository root)
python skills/video-cut/scripts/check_project_protocol.py
# re-transcribe the finished cut
ffmpeg -y -i first_cut.mp4 -ac 1 -ar 16000 work/selfcheck/cut_audio16k.wav
python scripts/transcribe.py work/selfcheck/cut_audio16k.wav work/selfcheck/cut_transcript
# content + filler + boundary check
python scripts/verify_cut.py work/edit_final.json work/transcript.json work/selfcheck/cut_transcript.json
# frame / black / join check (join times use post-speed out_dur, so they stay accurate)
python scripts/selfcheck_frames.py work/edit_final.json first_cut.mp4 work/selfcheck
# A/V sync + no residual dead air
ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 first_cut.mp4
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 first_cut.mp4
ffmpeg -i first_cut.mp4 -af silencedetect=noise=-32dB:d=1.5 -f null -
```
**Pass thresholds:**
| Check | Pass condition |
|---|---|
| Black frames | none |
| Join frames | clean — only natural head-jumps, no black/frozen/torn |
| A/V sync | video vs audio duration within ~1 frame (≈30ms); total ≈ `final_duration_s_after_speed` when varispeed is on |
| Dead air ≥1.5s | 0 (speaking_ratio should rise markedly) |
| Dropped/dup segment | none — all key content present (difflib ~0.90 is OK; lower
  ratio is usually 2nd-pass transcription noise on mumbled speech, not loss — verify
  by keyword presence before blaming the cut) |
| Cut-off half-sentences | none — boundaries land in silence / on sentence ends |

**Honest filler caveat:** paragraph-level cutting will NOT achieve "almost no fillers".
Per-minute density can even *rise* because the retained substance is conversational.
Report this honestly; word-level filler excision belongs to P1/P2 (and would make a
single-shot talking head visibly choppy).

### Finally
Write `first_cut_report.md`: source summary, what was cut & why, the self-check table,
and any honest caveats (quality ceiling from 360p source, filler density, etc.).
If varispeed was applied, disclose it: **how many segments were re-timed and the speed
range** (from `assign_speed.py`'s table / `speed_params`), so the reader knows the cut is
not 1:1 real-time. Note too that `verify_cut.py`'s filler-per-minute figure reads slightly
higher after speed-up (same words, shorter minutes) — a reporting artifact, not added fillers.

## Key principles (the hard-won ones)
- **You decide content; scripts decide frames.** Hand-write `edit_coarse.json`;
  let `build_edit.py` do precision and `assign_speed.py` do pace.
- **Speed touches pace, never content.** Auto-varispeed gives all render segments from
  one `decision_ref` the same speed, moves out-of-band pace only to the nearest deadband
  edge, limits adjacent decisions to a 0.08x delta, and clamps output to 1.0–1.3.
  `atempo` preserves pitch. Review the table; `mode=off` or skip the step to disable.
- **Never clip a word.** Boundaries always fall inside silence.
- **Memory-safe render only** (N seeked inputs + concat). Never multi-trim one input.
- **Be decisive.** Make reasonable calls and proceed; don't over-ask.
- **Self-check is non-negotiable.** Re-transcribe + frame-check before claiming done.
- See `reference/pitfalls.md` for the full list of traps and fixes.
