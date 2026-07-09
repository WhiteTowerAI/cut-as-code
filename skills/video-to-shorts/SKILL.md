---
name: video-to-shorts
description: >
  Select short-form clip candidates from an existing video transcript and turn
  reviewed candidates into a shorts_plan.json for later horizontal source clip
  extraction. Use after rough-cut or on a source video with a transcript when
  the user wants multiple reviewable Shorts candidates. This skill does not
  perform vertical reframing, subject detection, captions, Remotion graphics,
  color grading, or final publishing.
---

# Video To Shorts

`video-to-shorts` is the content-selection layer for short-form video. It turns
one video plus a transcript into reviewable candidate moments and then into a
human-editable `shorts_plan.json`.

## Boundary

This skill owns:

- preparing or reusing `work/shorts/transcript.json`;
- generating candidate short moments from that transcript;
- generating `shorts_plan.json` from reviewed candidates;
- extracting horizontal `short_XX/source.mp4` files and short-relative
  `short_XX/transcript.json` files after plan review.

This skill does not own:

- subject detection;
- horizontal-to-vertical reframing or 9:16 rendering;
- captions, Remotion graphics, color grading, or final packaging.

Vertical work belongs to `video-vertical-reframe`.

## Current Flow

1. Prepare transcript:
   `python skills/video-to-shorts/scripts/prepare_transcript.py VIDEO --out work/shorts`
2. Generate candidates:
   `python skills/video-to-shorts/scripts/candidates.py --video VIDEO --out work/shorts`
3. Human reviews `shorts_candidates_preview.html`.
4. Generate plan:
   `python skills/video-to-shorts/scripts/plan.py --out work/shorts`
5. Human reviews/edits `shorts_plan.json`.
6. Extract horizontal shorts:
   `python skills/video-to-shorts/scripts/extract_shorts.py --video VIDEO --out work/shorts`
7. Hand each `short_XX/source.mp4` to `video-vertical-reframe` in that short's
   own `vertical-reframe/` work directory.

## Criteria

The short-form selection criteria live in `scripts/criteria.py`. They
encode what makes a clip promising for Shorts: hook, emotional peak, opinion
bomb, reversal, conflict, quotable line, story peak, and practical value.

Candidates should be selected for short-form propagation potential, not merely
because a segment is generally interesting.

## Review Stop

Stop after candidates or plan generation and let the human review. After Phase
2 extraction, stop again before any vertical reframing or downstream finishing.

## Phase 2.5 Boundary Polish

`extract_shorts.py` performs a small boundary refinement pass before cutting:

- snap start/end away from word middles using `work/shorts/transcript.json`;
- prefer nearby phrase or pause boundaries when available;
- avoid obvious incomplete thought endings such as dangling connectors;
- add small pre-roll/post-roll handles;
- detect obvious internal scene cuts with ffmpeg scene detection and write
  warnings for human review.
- re-encode source clips for accurate arbitrary-time cuts and record ffprobe
  duration in extraction reports.
- record `tail_margin_s` so the reviewer can see whether the final word has
  breathing room before media end.

The refinement writes:

```text
work/shorts/short_XX/extraction_report.json
work/shorts/shorts_extraction_report.json
```

These reports preserve the original plan times plus
`refined_start_time`/`refined_end_time`. They are extraction diagnostics only;
they do not add subject detection or vertical reframing.

## Downstream Handoff

`video-to-shorts` does not implement vertical reframing. To verify or continue
the workflow, call `video-vertical-reframe` directly with each extracted
horizontal source:

```powershell
python skills/video-vertical-reframe/scripts/detect_subjects.py SHORT/source.mp4 --out SHORT/vertical-reframe
python skills/video-vertical-reframe/scripts/plan_reframe.py SHORT/source.mp4 --tracks SHORT/vertical-reframe/tracks.json --out SHORT/vertical-reframe
python skills/video-vertical-reframe/scripts/render_reframe.py SHORT/source.mp4 --plan SHORT/vertical-reframe/reframe_plan.json --crop-path SHORT/vertical-reframe/crop_path.json --out SHORT/vertical-reframe/vertical.mp4
```
