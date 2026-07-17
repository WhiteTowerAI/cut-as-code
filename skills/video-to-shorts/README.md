# Video To Shorts

`video-to-shorts` selects complete horizontal short-source moments through two required, isolated Agent-first passes. The `text_only` pass uses only the transcript; the separately authored `text_visual` pass uses the transcript plus visual context without reading or copying the text-only output. `candidates.py` validates each mode-specific `shorts_candidates.json`, computes score totals, deduplicates overlaps within that file, and generates its review preview. Approved horizontal shorts can optionally continue through an Agent-planned deterministic vertical delivery workflow.

Candidate evidence mode (`text_only` or `text_visual`) is independent from delivery mode (`horizontal_only` or `horizontal_and_vertical`). Vertical delivery always regenerates dense visual evidence from each extracted short, validates an Agent-authored plan, renders a low-resolution preview for review, and only then permits a formal render.

Current vertical strategies are `STATIC_CROP`, `SCENE_CROP`, `LETTERBOX`, and `REVIEW_REQUIRED`. Planning is scene-first: stable presenter scenes should use fixed crops that keep the head and torso large and complete, while `LETTERBOX` is reserved for specific scenes that require full horizontal information. The validator reports strategy-duration percentages and non-blocking warnings for complete-short LETTERBOX and presenter scenes classified as LETTERBOX. `LETTERBOX` preserves the complete sharp foreground frame over a blurred, darkened background rather than a plain black background. Stable pure-black borders are removed only from the background layer after multi-frame confirmation; uncertain detection falls back to complete-frame blur, and the sharp foreground is never cropped. The workflow does not provide continuous dynamic subject tracking.

## Transcript Input

The recommended entry is an explicitly provided standard transcript:

```powershell
python skills/video-to-shorts/scripts/prepare_transcript.py VIDEO.mp4 `
  --transcript C:\absolute\path\transcript.json `
  --out WORK\shorts
```

If `--transcript` is omitted, the current compatibility fallback extracts audio and invokes `video-rough-cut/scripts/transcribe.py`. The fallback is not the skill's long-term transcription architecture. No transcript files are auto-discovered.

Outputs include `transcript.json`, `transcript_metadata.json`, `transcript_preview.md`, and `transcript_preview.html`. The previews contain objective transcript statistics only and do not recommend candidate ranges.

## Visual Context

```powershell
python skills/video-to-shorts/scripts/prepare_visual_context.py VIDEO.mp4 `
  --out WORK\shorts\visual_context
```

This creates timestamped frames, paged contact sheets, and `visual_manifest.json` for the required `text_visual` candidate pass. Visual evidence never affects candidate scoring.

## Candidate Step

1. Prepare or provide `WORK/shorts/transcript.json`.
2. Independently author the transcript-only pass at `WORK/shorts/preview/text_only/shorts_candidates.json`. Set `selection.evidence_mode` and every candidate `evidence_mode` to `text_only`.
3. Freeze the text-only folder before inspecting visual evidence.
4. Independently author the visual pass at `WORK/shorts/preview/text_visual/shorts_candidates.json`. Set `selection.evidence_mode` and every candidate `evidence_mode` to `text_visual`; do not read or copy the text-only output.
5. Provide a non-empty `metadata.editorial_reason` for every candidate. Do not write candidate total `score`; provide all six `score_breakdown` entries and reasons.
6. Validate each mode into its own preview folder:

```powershell
python skills/video-to-shorts/scripts/candidates.py `
  --out WORK\shorts\preview\text_only `
  --candidates WORK\shorts\preview\text_only\shorts_candidates.json `
  --transcript WORK\shorts\transcript.json

python skills/video-to-shorts/scripts/candidates.py `
  --out WORK\shorts\preview\text_visual `
  --candidates WORK\shorts\preview\text_visual\shorts_candidates.json `
  --transcript WORK\shorts\transcript.json
```

7. Review each mode's normalized JSON and HTML only after both isolated passes are complete. On Windows, prefer ASCII punctuation in Agent-authored metadata and avoid piping Unicode-rich generated source through PowerShell with an unknown pipeline encoding.

Explicit paths are supported:

```powershell
python skills/video-to-shorts/scripts/candidates.py `
  --out WORK\shorts `
  --candidates WORK\drafts\shorts_candidates.json `
  --transcript WORK\shorts\transcript.json
```

Outputs:

- `shorts_candidates.json`: normalized v2 candidates with script-computed totals.
- `shorts_candidates_preview.md`: human-readable contract review.
- `shorts_candidates_preview.html`: visual review including duration, dimensions and reasons, script-generated score, warnings, filler spans, separately labeled visual observations/risks/keyframes, and local keyframe thumbnails when the files exist.

The validator does not call external model services, repair JSON through a provider, or reinterpret the Agent's scores. Each invocation accepts exactly one evidence mode, requires every candidate to match `selection.evidence_mode`, deduplicates only inside that file, and displays visual evidence without changing scoring.

## Mandatory Candidate Interview

After both isolated previews exist, open the machine-enforced interview:

```powershell
python skills/video-to-shorts/scripts/interaction.py candidate-open `
  --out WORK\shorts
```

Show `WORK/shorts/review/candidate_review_question.md` to the user and end the current turn. In a later turn, save the user's verbatim reply and record it:

```powershell
python skills/video-to-shorts/scripts/interaction.py candidate-answer `
  --out WORK\shorts `
  --response-file WORK\shorts\review\user_response.txt
```

The user must choose `horizontal_only` or `horizontal_and_vertical`. Explicit qualified candidate references preserve user order. If the later user response omits candidate IDs or says default/skip, the gate selects the five highest-scoring `text_visual` candidates. Silence, an ambiguous answer, or a modification request cannot advance the workflow.

## Plan Generation

After the candidate review reports `approved`:

```powershell
python skills/video-to-shorts/scripts/plan.py `
  --out WORK\shorts
```

`plan.py` has no candidate-selection bypass. It verifies the current review, both source candidate hashes, the approved candidate file, and the user-selected delivery mode. The planner consumes validated `shorts-candidates.v2`, applies deterministic score, completeness, duration, timeline, excerpt, overlap, and maximum-count filters, then writes:

- `shorts_plan.json`
- `shorts_plan_preview.md`
- `shorts_plan_preview.html`

The planner preserves editorial scores, validates approved word-level `filler_drop_spans`, and derives `keep_spans` plus estimated output duration. It does not infer filler words or use visual fields for ranking.

Extraction applies the existing outer boundary refinement first, then concatenates the derived keep spans in one final ffmpeg encode and remaps the short transcript onto a continuous timeline:

```powershell
python skills/video-to-shorts/scripts/extract_shorts.py `
  --video VIDEO.mp4 `
  --out WORK\shorts
```

Rejected or unsafe filler_drop_spans are reported and are not executed.

## Contract

The complete candidate v2 required fields, types, enums, score ranges, timeline rules, boundary guidance, four scene strategies, and JSON template live in `SKILL.md`. Executable checks live in `scripts/candidates.py`, while the human/Agent contract lives in `SKILL.md`.

## Pipeline Boundary

Planning, short-relative transcript generation, extraction, boundary refinement, vertical reframing, captions, and publishing are later steps or downstream skills. A future independent transcript skill is not implemented or assumed here; it only needs to hand off the standard transcript through `--transcript`.

## Examples

- `examples/example_transcript.json`: compact word-level transcript.
- `examples/example_shorts_candidates.json`: isolated `text_only` candidate v2 input without total scores.
- `examples/example_shorts_candidates_text_visual.json`: separately authored `text_visual` candidate v2 input without total scores.
- `examples/example_shorts_plan.json`: deterministic `shorts-plan.v2` output example.
