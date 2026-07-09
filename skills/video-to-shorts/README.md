# Video To Shorts

Phase 0 defines the contract for turning one existing video into multiple
short-form clip plans. This skill is an orchestration layer for content
selection and future short source extraction; it is not a vertical reframe,
caption, motion graphics, or color grading skill.

## Pipeline Boundary

`video-to-shorts` owns:

- resolving or creating the transcript for the input video;
- selecting candidate short-form moments from the transcript;
- writing reviewable candidate and plan JSON files;
- after human approval, cutting horizontal `short_XX/source.mp4` files and
  writing one `short_XX/transcript.json` per short with a short-relative
  timeline.

`video-to-shorts` does not own:

- subject detection;
- horizontal-to-vertical reframing;
- final 9:16 rendering;
- burned-in captions;
- Remotion graphics;
- color grading;
- final publishing package assembly.

Downstream skills consume the short sources:

```text
short_XX/source.mp4
  -> video-vertical-reframe
  -> tracks.json / reframe_plan.json / crop_path.json / vertical.mp4

vertical.mp4
  -> video-to-captions / video-to-remotion / video-color-grade
  -> final short
```

## Supported Inputs

Preferred rough-cut input:

```text
first_cut.mp4
work/selfcheck/cut_transcript.json
```

Raw or non-rough-cut input with transcript:

```text
source.mp4
transcript.json
```

Raw input without transcript:

```text
source.mp4
```

If no transcript is available, the future implementation should extract
`audio16k.wav` and reuse `skills/video-rough-cut/scripts/transcribe.py` to
produce the same word-level transcript shape used by the existing rough-cut,
captions, and Remotion skills.

If a transcript is explicitly provided, or if a rough-cut self-check transcript
exists at `work/selfcheck/cut_transcript.json`, the implementation should reuse
that JSON and skip Whisper.

## Phase Outputs

Phase 1 output:

```text
work/shorts/shorts_candidates.json
```

This file contains LLM-selected candidate moments. It is a review artifact, not
an execution plan.

Phase 1 transcript preparation output:

```text
work/shorts/transcript.json
work/shorts/transcript_preview.md
work/shorts/transcript_preview.html
```

Prepare transcript artifacts:

```powershell
python skills/video-to-shorts/scripts/prepare_transcript.py VIDEO.mp4 --out work/shorts
```

Use an explicit transcript:

```powershell
python skills/video-to-shorts/scripts/prepare_transcript.py VIDEO.mp4 --transcript TRANSCRIPT.json --out work/shorts
```

If `ffmpeg` is not on PATH and no transcript exists, pass it explicitly:

```powershell
python skills/video-to-shorts/scripts/prepare_transcript.py VIDEO.mp4 --out work/shorts --ffmpeg C:\path\to\ffmpeg.exe
```

Transcript discovery order:

1. explicit `--transcript`;
2. `cut_transcript.json` beside the input video;
3. `work/selfcheck/cut_transcript.json` under the input video's directory;
4. generate a new transcript by extracting `audio16k.wav` and calling
   `skills/video-rough-cut/scripts/transcribe.py`.

Phase 2 extraction input and output:

```text
work/shorts/shorts_plan.json
work/shorts/short_01/source.mp4
work/shorts/short_01/transcript.json
work/shorts/short_02/source.mp4
work/shorts/short_02/transcript.json
```

`shorts_plan.json` is the confirmed plan. Each `short_XX/transcript.json` is
derived from the input transcript and uses a timeline relative to that short's
own `source.mp4`.

## Schemas

- `schemas/shorts_candidates.schema.json` describes the candidate review file.
- `schemas/shorts_plan.schema.json` describes the confirmed execution plan.
- `schemas/short_transcript.schema.json` describes each short-relative
  transcript.

## Candidate Generation

Generate Phase 1 candidate shorts from an already prepared transcript:

```powershell
python skills/video-to-shorts/scripts/candidates.py --video VIDEO.mp4 --out WORK\shorts
```

The command reads `WORK\shorts\transcript.json` and writes:

```text
WORK/shorts/shorts_candidates.json
WORK/shorts/shorts_candidates_preview.md
WORK/shorts/shorts_candidates_preview.html
```

Supported options:

```powershell
python skills/video-to-shorts/scripts/candidates.py `
  --video VIDEO.mp4 `
  --out WORK\shorts `
  --model gpt-5.5 `
  --base-url https://api.openai.com/v1 `
  --max-candidates 12 `
  --min-duration 20 `
  --max-duration 90
```

LLM configuration uses one OpenAI-compatible client. Command-line arguments
override environment variables.

OpenAI / ChatGPT example:

```powershell
$env:LLM_PROVIDER = "openai_compatible"
$env:LLM_BASE_URL = "https://api.openai.com/v1"
$env:LLM_MODEL = "gpt-5.5"
$env:LLM_API_KEY = "<set this in your shell, never commit it>"
```

DeepSeek example:

```powershell
$env:LLM_PROVIDER = "openai_compatible"
$env:LLM_BASE_URL = "https://api.deepseek.com"
$env:LLM_MODEL = "deepseek-chat"
$env:LLM_API_KEY = "<set this in your shell, never commit it>"
```

If `LLM_API_KEY` is missing, the command writes:

```text
WORK/shorts/llm_error.json
WORK/shorts/llm_raw_response.txt
```

and exits with a clear error. It does not fall back to fake candidates.

## Plan Generation

Generate a human-editable `shorts_plan.json` from reviewed candidates:

```powershell
python skills/video-to-shorts/scripts/plan.py --out WORK\shorts
```

The command reads:

```text
WORK/shorts/shorts_candidates.json
WORK/shorts/transcript.json
```

and writes:

```text
WORK/shorts/shorts_plan.json
WORK/shorts/shorts_plan_preview.md
WORK/shorts/shorts_plan_preview.html
```

Options:

```powershell
python skills/video-to-shorts/scripts/plan.py `
  --out WORK\shorts `
  --max-shorts 5 `
  --min-duration 20 `
  --max-duration 90 `
  --min-score 70 `
  --allow-overlap false
```

By default, the plan keeps the highest-scoring candidates that pass duration
and score checks, and removes obvious overlaps. This command does not cut video
and does not call `video-vertical-reframe`.

## Phase 2 Extraction

Extract horizontal short sources from a reviewed `shorts_plan.json`:

```powershell
python skills/video-to-shorts/scripts/extract_shorts.py `
  --video VIDEO.mp4 `
  --out WORK\shorts
```

The command reads:

```text
WORK/shorts/shorts_plan.json
WORK/shorts/transcript.json
```

and writes:

```text
WORK/shorts/short_01/source.mp4
WORK/shorts/short_01/transcript.json
WORK/shorts/short_02/source.mp4
WORK/shorts/short_02/transcript.json
```

Options:

```powershell
python skills/video-to-shorts/scripts/extract_shorts.py `
  --video VIDEO.mp4 `
  --out WORK\shorts `
  --plan WORK\shorts\shorts_plan.json `
  --transcript WORK\shorts\transcript.json `
  --ffmpeg C:\path\to\ffmpeg.exe `
  --ffprobe C:\path\to\ffprobe.exe `
  --min-tail-margin 0.6
```

This command only extracts horizontal source clips and short-relative
transcripts. It does not run subject detection, vertical reframing, captions,
Remotion graphics, color grading, or final publishing.

### Phase 2.5 Boundary Polish

By default, `extract_shorts.py` performs a small cut-boundary polish pass before
writing `short_XX/source.mp4`:

- start/end times are snapped away from word middles using the word-level
  transcript;
- nearby phrase or pause boundaries are preferred when they are close enough;
- incomplete thought endings such as dangling connectors are avoided where a
  nearby complete phrase is available;
- small pre-roll/post-roll handles are added without exceeding transcript
  duration;
- ffmpeg scene detection checks each short for obvious internal scene cuts and
  writes warnings such as `POSSIBLE_JUMP_CUT`.
- output clips are re-encoded for accurate arbitrary-time cuts, and the report
  records the actual ffprobe duration.
- reports include `tail_margin_s`; low tail margin is warned because it can cut
  off the final word.

The command also writes reviewable extraction reports:

```text
WORK/shorts/shorts_extraction_report.json
WORK/shorts/short_01/extraction_report.json
WORK/shorts/short_02/extraction_report.json
```

Use the raw plan boundaries only when debugging:

```powershell
python skills/video-to-shorts/scripts/extract_shorts.py `
  --video VIDEO.mp4 `
  --out WORK\shorts `
  --no-refine-boundaries
```

Boundary polish only improves horizontal short extraction. It does not perform
subject detection, vertical reframing, captions, Remotion graphics, color
grading, or publishing.

## Downstream Vertical Reframe Handoff

Phase 2 outputs are intended to be passed to `video-vertical-reframe` one short
at a time. Keep the vertical reframe work under each short directory:

```text
WORK/shorts/short_01/source.mp4
WORK/shorts/short_01/vertical-reframe/
```

Example handoff:

```powershell
python skills/video-vertical-reframe/scripts/detect_subjects.py `
  WORK\shorts\short_01\source.mp4 `
  --out WORK\shorts\short_01\vertical-reframe

python skills/video-vertical-reframe/scripts/plan_reframe.py `
  WORK\shorts\short_01\source.mp4 `
  --tracks WORK\shorts\short_01\vertical-reframe\tracks.json `
  --out WORK\shorts\short_01\vertical-reframe

python skills/video-vertical-reframe/scripts/render_reframe.py `
  WORK\shorts\short_01\source.mp4 `
  --plan WORK\shorts\short_01\vertical-reframe\reframe_plan.json `
  --crop-path WORK\shorts\short_01\vertical-reframe\crop_path.json `
  --out WORK\shorts\short_01\vertical-reframe\vertical.mp4
```

This is a downstream skill handoff. The vertical reframe implementation remains
inside `video-vertical-reframe`, not `video-to-shorts`.

## Examples

- `examples/example_transcript.json` is a compact word-level transcript that can
  be read directly.
- `examples/example_shorts_candidates.json` shows three candidate moments with
  scores and reasons.
- `examples/example_shorts_plan.json` shows two approved shorts that can be cut
  and then handed to `video-vertical-reframe`.

The examples are intentionally short and human-readable. They are not generated
from real media and should be treated as contract examples only.
