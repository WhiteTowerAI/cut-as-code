# Video To Shorts

`video-to-shorts` selects complete horizontal short-source moments from a transcript. Candidate selection is Agent-first: the Agent reads the transcript, optionally reviews visual evidence, and writes `shorts_candidates.json`; `candidates.py` performs deterministic validation, score summation, overlap dedupe, and preview generation.

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

This creates timestamped frames, paged contact sheets, and `visual_manifest.json` for optional `text_visual` review. Visual evidence never affects candidate scoring.

## Candidate Step

1. Prepare or provide `WORK/shorts/transcript.json`.
2. Follow `SKILL.md` to write `WORK/shorts/shorts_candidates.json` using `shorts-candidates.v2`.
3. Do not write candidate total `score`; provide all six `score_breakdown` entries and reasons.
4. Validate and render previews:

```powershell
python skills/video-to-shorts/scripts/candidates.py --out WORK\shorts
```

5. Review the normalized JSON and both previews for title/reason grammar and encoding damage before plan generation. On Windows, prefer ASCII punctuation in Agent-authored metadata and avoid piping Unicode-rich generated source through PowerShell with an unknown pipeline encoding.

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

The validator does not call external model services, repair JSON through a provider, or reinterpret the Agent's scores. `text_visual` evidence is displayed but never changes scoring.

## Plan Generation

```powershell
python skills/video-to-shorts/scripts/plan.py --out WORK\shorts
```

This consumes validated `shorts-candidates.v2`, applies deterministic score, completeness, duration, timeline, excerpt, overlap, and maximum-count filters, then writes:

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
- `examples/example_shorts_candidates.json`: Agent-authored candidate v2 input without total scores.
- `examples/example_shorts_plan.json`: deterministic `shorts-plan.v2` output example.
