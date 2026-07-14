---
name: video-to-shorts
description: Select complete horizontal short-form moments from a transcript, validate an agent-authored candidate contract, review candidates, then hand approved work to later planning and extraction steps.
---

# Video To Shorts

## Transcript Input Boundary

The long-term responsibility of `video-to-shorts` is to consume a prepared standard word-level transcript. Candidate selection, planning, and extraction depend only on this data contract; they do not depend on a transcription model, device, or provider.

An independent transcript skill may be implemented in the future, but it does not exist today. Do not create or assume its directory, command name, provider framework, or output location. Any future transcription capability should produce the same standard `transcript.json`, and the caller should pass that file explicitly with `--transcript`.

### Recommended Provided Transcript Path

```powershell
python skills/video-to-shorts/scripts/prepare_transcript.py VIDEO.mp4 `
  --transcript C:\absolute\path\transcript.json `
  --out WORK\shorts
```

The script checks that the file exists and parses, validates segments and optional words, normalizes it to `OUT/transcript.json`, and does not call Whisper. Preview metadata records `acquisition_mode=provided` and the absolute `source_transcript` path.

### Temporary Whisper Fallback

When `--transcript` is omitted, the script currently extracts `audio16k.wav` and invokes the existing `skills/video-rough-cut/scripts/transcribe.py`. Metadata records `acquisition_mode=generated_fallback` and `generator=video-rough-cut/transcribe.py`.

This is a compatibility fallback, not a long-term core responsibility and not a future transcript skill. Once an external transcript capability exists, prefer generating the transcript externally and passing it explicitly. The fallback remains intentionally concentrated in `generate_fallback()` so it can later be removed or replaced without changing downstream contracts.

`prepare_transcript.py` never searches adjacent, parent, child, self-check, or similarly named JSON files. Existing transcripts must be selected explicitly with `--transcript`; otherwise the fallback runs.

## Standard Transcript Contract

```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Example sentence.",
      "words": [
        {"start": 0.0, "end": 0.4, "word": "Example"}
      ]
    }
  ]
}
```

- Root `segments` is required and must be an array.
- Every segment requires numeric `start`, numeric `end`, and string `text`.
- Segment time uses the input-video-relative timeline and must satisfy `0 <= start <= end`.
- `words` is optional for basic validation, but the candidate and extraction workflow expects a standard word-level transcript for precise boundaries.
- When `words` is present, each word requires numeric `start`, numeric `end`, and string `word`, using the same input-video-relative timeline.
- Additional root, segment, and word metadata may pass through unchanged; downstream behavior must not depend on generator-specific fields.

## Transcript Preview

`transcript_preview.md` and `.html` display only objective information: acquisition metadata, duration, segment count, word count, speech duration, transcript segments, per-minute words, WPM, and speech density. WPM and speech density remain separate raw statistics; they are not added, weighted, ranked, or converted into candidate recommendations.

## Optional Visual Context

For `text_visual` review, prepare deterministic global evidence separately:

```powershell
python skills/video-to-shorts/scripts/prepare_visual_context.py VIDEO.mp4 `
  --out WORK\shorts\visual_context `
  --interval 60
```

This writes timestamped source frames, paged `contact_sheets/contact_sheet_XX.jpg`, and `visual_manifest.json`. The Agent may inspect global sheets and then individual first/middle/last frames around a potential candidate. These artifacts are review context only and never add to or subtract from candidate scores.

## Boundary

This skill owns transcript-based selection of horizontal short-source moments. It does not own vertical reframing, captions, graphics, color grading, or publishing. Step 1 stops after candidate validation and previews; it does not change planning, transcript preparation, boundary refinement, or extraction behavior.

## Agent-First Candidate Workflow

1. Read `transcript.json` and identify complete, self-contained moments.
2. Optionally inspect visual evidence when it materially helps review risk.
3. Write `shorts_candidates.json` directly using `shorts-candidates.v2`; do not write `score`.
4. Run `candidates.py`, which validates fields, computes the arithmetic score, checks transcript/time evidence, removes overlaps, and writes Markdown/HTML previews.
5. Perform Candidate Artifact Text QA on the normalized JSON and generated previews.
6. Stop for human review before plan generation.

```powershell
python skills/video-to-shorts/scripts/candidates.py --out WORK\shorts
```

The default input is `WORK/shorts/shorts_candidates.json` and the default transcript is `WORK/shorts/transcript.json`. `--candidates` and `--transcript` may point to explicit files. The script never calls a model API and never revises an Agent's dimension scores based on transcript content.

### Candidate Artifact Text QA

Before review, inspect every candidate title, all six score reasons, editorial reason, warnings, and visual observations/risks as standalone text. Correct grammar, missing quotation boundaries, repeated words, incomplete phrases, and unclear references. Deterministic validation does not prove that Agent-authored prose is natural or grammatically correct.

Inspect both generated previews and confirm that candidate IDs, titles, duration, transcript excerpt, score reasons, script-generated score, warnings, `filler_drop_spans`, and the three visual fields render correctly. Suspicious `?` or the Unicode `U+FFFD` replacement character in Agent-authored metadata may indicate encoding damage, but do not remove legitimate question marks from transcript excerpts or intentional questions.

On Windows, prefer ASCII straight quotes, apostrophes, and hyphens in Agent-authored metadata. Do not pipe Unicode-rich generated source through Windows PowerShell when the pipeline encoding is unknown. Save generated scripts as UTF-8 files, use ASCII Unicode escapes in source, or use HTML entities for typographic separators. `preview.py` uses ASCII structural separators and writes UTF-8 Markdown/HTML directly.

## Candidate Judgment Prompt

Select moments for short-form potential, not merely general quality. Prefer a slightly longer complete thought over a shorter fragment.

- **Hook Moments:** the first seconds create curiosity, conflict, a promise, a clear question, or a useful contrast.
- **Emotional Peaks:** surprise, excitement, vulnerability, anger, humor, tension, or explicit stakes are present and understandable.
- **Opinion Bombs:** a clear, counter-intuitive, strong, or controversial claim invites agreement or disagreement.
- **Reversals:** the moment overturns a common belief or produces an outcome opposite to audience expectation.
- **Conflict or Tension:** risk, disagreement, challenge, bottleneck, uncertainty, or a problem-to-solve gives the clip forward motion.
- **Quotable Lines:** a compact statement remains meaningful and shareable outside the source context.
- **Story Peaks:** preserve the payoff, twist, result, reveal, or climax of an anecdote, case, or demonstration.
- **Practical Value:** deliver advice, a method, workflow, explanation, or insight the audience can quickly understand or use.

Use these signals together with the scene strategy and six scoring dimensions. Do not count the same signal twice merely because it fits multiple labels.

## Four Scene Strategies

### Product Launch or Demonstration

- Select clear claims, visible breakthroughs, before/after contrasts, surprising metrics, and demonstrations with an understandable result.
- Keep enough setup at the opening to identify the product, problem, or promised outcome.
- Preserve the demonstrated result and the speaker's conclusion; a setup without the reveal is incomplete.
- Common bad boundaries start after the product subject was named or end before the result/metric lands.
- Reject feature lists without stakes, context-dependent applause lines, and demonstrations whose result is not available in the selected range.

### Conversation or Interview

- Select strong answers, disagreement, personal disclosure, concise expertise, humor, tension, and interviewer questions that unlock a complete response.
- Keep the question when the answer depends on it; omit it only when the answer is independently clear.
- Preserve the answer's conclusion, reversal, or emotional resolution.
- Common bad boundaries begin with pronouns or references to an earlier exchange and end while the speaker is qualifying the claim.
- Reject small talk, repeated agreement, answers requiring missing context, and exchanges with no standalone value.

### Solo Talk

- Select decisive claims, surprising explanations, emotional peaks, practical frameworks, and memorable formulations.
- Keep the premise or subject noun needed to understand the opening sentence.
- Preserve the explanation, evidence, or conclusion that earns the initial hook.
- Common bad boundaries start after the premise or end on a transition into the actual point.
- Reject generic motivation, throat-clearing, repeated restatements, and claims whose support lies outside the range.

### Tutorial or Story

- Select actionable steps, mistakes and fixes, turning points, compact case studies, and stories with a clear result.
- Keep the goal, initial condition, or problem needed to interpret the steps or story.
- Preserve the usable method or narrative payoff, including the final result or lesson.
- Common bad boundaries begin midway through instructions or end before the final step, twist, result, or lesson.
- Reject incomplete procedures, anecdotes without payoff, and setup-only passages.

## Boundary Rules

- Never start or end in the middle of a sentence or thought.
- Every candidate must be complete and self-contained.
- `start_time` is the first word of the complete sentence or thought.
- `end_time` is after the final word of the complete sentence or thought.
- Do not start with a fragment that depends on prior context.
- Do not end on dangling connectors such as `and`, `that`, `our`, `to`, or `of`.
- Prefer a slightly longer complete candidate over a short incomplete one.
- `transcript_excerpt` must exactly equal the transcript words whose timestamps overlap the candidate range.

## Agent Filler Judgment Rules

First establish the complete candidate envelope. Only after the candidate has a valid `start_time`, `end_time`, and complete thought may the Agent inspect its internal words for optional filler_drop_spans. Never shorten the outer candidate boundary merely to remove a filler.

Only mark a word or short hesitation as a filler_drop_span when removing it preserves the sentence's meaning, grammar, emphasis, emotion, and natural flow. Judge the word in its immediate transcript context; matching a common filler spelling is not sufficient by itself.

Common English hesitation tokens that may be eligible include:

- `um`
- `uh`
- `erm`
- `hmm`

Mark one of these tokens only when all of the following are true:

- It appears as an independent hesitation or speech placeholder.
- It contributes no necessary fact, transition, emphasis, emotion, quotation, or speaker intent.
- The words before and after it form a natural grammatical and semantic connection after removal.
- It has reliable word-level `start` and `end` timestamps.
- Its range can be isolated without touching either adjacent valid word.
- Removing it does not create an unnaturally abrupt audio or visual transition.

Example that may be approved:

```text
We, um, built this system last year.
```

The independent `um` may be marked when its word timestamps are isolated and the remaining sentence becomes `We built this system last year.`

Do not automatically mark words such as `ah`, `hmm`, `like`, `so`, `well`, `actually`, or `you know`. They may function as fillers, but they may also carry emotion, disagreement, comparison, transition, emphasis, or necessary meaning. Inspect the complete thought before deciding.

Do not mark a token when any of the following apply:

- It expresses surprise, understanding, doubt, disagreement, humor, frustration, or another meaningful reaction.
- It is grammatically required or changes the meaning, emphasis, pacing, or speaker personality when removed.
- It is quoted, imitated, discussed, or used as an example rather than spoken as a hesitation.
- It is joined to an adjacent word or lacks a safe independent word-level boundary.
- Removal would make the remaining speech sound clipped, rushed, or unnatural.
- The transcript context is insufficient to determine whether it is semantically empty.

Example that must not be removed:

```text
He literally said "um" five times.
```

Here `um` is quoted content and is part of the sentence's meaning.

When uncertain, preserve the word. Do not create an approved filler_drop_span merely to make the clip shorter. The Agent may omit the span or record it with `review_status=rejected` for human review. Prefer retaining a harmless hesitation over deleting valid speech.

For every proposed filler_drop_span, provide a concise `reason` that identifies the token and explains why removal preserves the surrounding thought. Do not use a generic reason such as `remove filler` without checking the local context.

## Six-Dimension Scoring

The Agent supplies each dimension's numeric `score` and a short `reason`. The Agent must not supply total `score`.

| Dimension | Range | Judge |
|---|---:|---|
| `hook` | 0-20 | Opening curiosity, conflict, promise, question, or contrast. |
| `completeness` | 0-20 | Standalone context, complete thought, and retained payoff. |
| `audience_value` | 0-20 | Practical value, insight, relevance, or understandable result. |
| `emotion_tension` | 0-15 | Emotion, stakes, conflict, surprise, or reversal. |
| `quotability` | 0-15 | Memorable, concise, independently shareable language. |
| `pace_editability` | 0-10 | Efficient delivery and ability to remove filler without damaging meaning. |

`candidates.py` requires all six dimensions, validates numeric ranges, and sets total `score` to their pure arithmetic sum. A handwritten top-level candidate `score` is an error and is never trusted. Visual evidence never changes any dimension or total.

## Evidence Mode

- `text_only`: judge only from transcript; visual arrays must be absent or empty.
- `text_visual`: judge from transcript plus optional `visual_observations`, `visual_risks`, and `visual_keyframes`. These fields are review evidence only and never affect scoring.

## Candidate v2 Contract

Top-level fields: `schema_version`, optional `video`, optional `transcript`, optional `producer`, optional `selection`, and required `candidates` array. Output `schema_version` is `shorts-candidates.v2`.

Each candidate requires:

- `candidate_id`: non-empty string.
- `title`: non-empty string.
- `scene_type`: `product_demo`, `conversation_interview`, `solo_talk`, or `tutorial_story`.
- `start_time`, `end_time`: numbers on the input-video-relative timeline; `0 <= start_time < end_time <= transcript duration`.
- `transcript_excerpt`: non-empty exact excerpt for that time range.
- `evidence_mode`: `text_only` or `text_visual`.
- `score_breakdown`: exactly the six dimensions; each contains only numeric `score` and non-empty string `reason`.

Optional candidate fields:

- `warnings`: string array.
- `filler_drop_spans`: Agent-authored array of `{type, start_time, end_time, reason, review_status}` fully inside the candidate range. `type` must be `filler`.
- `visual_observations`, `visual_risks`, `visual_keyframes`: string arrays; non-empty only for `text_visual`.
- `review_status`: string, default `candidate`.
- `metadata`: object.

The validator adds `duration` and computed `score`. Candidates overlapping more than 50% of the shorter candidate are deduplicated after sorting by computed score; the higher-scoring candidate is kept.

### Template

```json
{
  "schema_version": "shorts-candidates.v2",
  "candidates": [{
    "candidate_id": "cand-001",
    "title": "A complete standalone moment",
    "scene_type": "solo_talk",
    "start_time": 12.0,
    "end_time": 42.0,
    "transcript_excerpt": "Exact transcript words in the selected range.",
    "evidence_mode": "text_only",
    "score_breakdown": {
      "hook": {"score": 16, "reason": "Immediate clear promise."},
      "completeness": {"score": 19, "reason": "Premise and payoff are complete."},
      "audience_value": {"score": 18, "reason": "Useful standalone insight."},
      "emotion_tension": {"score": 8, "reason": "Moderate stakes."},
      "quotability": {"score": 12, "reason": "Contains a concise line."},
      "pace_editability": {"score": 8, "reason": "Dense delivery with removable filler."}
    },
    "warnings": [],
    "filler_drop_spans": []
  }]
}
```

## Review Stop

Review transcript/contact-sheet artifacts before authoring candidates, then review `shorts_candidates_preview.md` or `.html` before promoting candidates into the deterministic plan. This workflow does not implement a future transcript skill, short-transcript remapping, filler extraction, boundary refinement changes, or clip extraction changes.

## Shorts Plan v2

After a human reviews the validated candidates, generate a deterministic plan:

```powershell
python skills/video-to-shorts/scripts/plan.py --out WORK\shorts
```

`plan.py` requires `shorts-candidates.v2`. It uses the script-generated candidate `score` and existing `score_breakdown`; it never recalculates editorial dimensions, changes their reasons, reads visual observations for scoring, or calls a model.

### Selection Rules

- `score >= 70`.
- `score_breakdown.completeness.score >= 15`.
- Duration is between 20 and 90 seconds, inclusive.
- `transcript_excerpt` is non-empty.
- Start/end are valid on the transcript's input-video-relative timeline.
- Candidate `duration` matches `end_time - start_time`.
- Candidates are ordered by score descending.
- By default, overlap greater than 50% of the shorter candidate is rejected; the higher-scoring candidate remains.
- At most `--max-shorts` candidates are selected.
- `text_visual` evidence fields have no effect on selection or score.

### Required Short Fields

Every item in `shorts` contains `id`, `short_id`, `candidate_id`, `source_candidate_index`, `order`, `title`, `scene_type`, `evidence_mode`, `start_time`, `end_time`, `duration`, `score_breakdown`, `score`, `hook_sentence`, `editorial_reason`, `transcript_excerpt`, `filler_drop_spans`, `validation`, `outputs`, and `status`.

`hook_sentence` and `editorial_reason` are carried when present and otherwise remain empty; the planner does not invent editorial text.

## Filler Drop Spans and Keep Spans

The Agent judgment rules appear earlier because filler_drop_spans are authored during candidate creation. This section defines only deterministic script behavior: `plan.py` validates the submitted spans and derives keep spans; `extract_shorts.py` executes those keep spans and remaps the transcript. Neither script decides whether a word is semantically a filler.

Plan validation applies these deterministic rules:

- Only `type=filler` is executable.
- `review_status=rejected` is recorded but not executed.
- Each filler_drop_span is at most 1.5 seconds.
- Requested boundaries must match transcript word boundaries within 0.06 seconds; unsafe overlap with a word is rejected.
- Spans must remain within the candidate envelope and must not overlap each other.
- Total approved removal may not exceed 15% of the candidate source duration.
- Derived keep spans must be non-zero and at least 0.15 seconds.
- Rejected spans remain visible with their rejection reason and produce a warning; failures are never silently ignored.

For accepted spans, `plan.py` writes normalized `filler_drop_spans`, `rejected_filler_drop_spans`, `keep_spans`, `source_duration`, `filler_removed_duration`, and `estimated_output_duration`. The 20–90 second selection limit applies to `estimated_output_duration`.

Extraction first performs the existing outer Extraction Boundary Refinement, then adapts the planned keep spans to that refined envelope. ffmpeg trims each keep span, concatenates video and audio in order, and performs one final encode. The short transcript excludes words outside keep spans and shifts later segment/word timestamps forward onto one continuous short-relative timeline beginning at zero.

Extraction reports record original and refined boundaries, requested/executed/rejected filler_drop_spans, keep spans, source/removed/estimated/actual durations, last transcript word, tail margin, transcript/media validation, and warnings.

### Validation

Each selected short has `validation.passed=true`, plus `errors` and `warnings` arrays. Rejected candidates appear in top-level `rejected_candidates` with reasons such as `LOW_SCORE`, `LOW_COMPLETENESS`, `SHORT_DURATION`, `LONG_DURATION`, `INVALID_TIME_RANGE`, `TIME_OUT_OF_RANGE`, `DURATION_MISMATCH`, `EMPTY_EXCERPT`, `OVERLAPS_HIGHER_SCORE`, or `MAX_SHORTS_REACHED`.

### Output Paths

For `short_01`, the expected paths are data only:

- `work/shorts/short_01/`
- `work/shorts/short_01/source.mp4`
- `work/shorts/short_01/transcript.json`
- `work/shorts/short_01/extraction_report.json`

Plan generation does not create these media outputs.

### JSON Template

```json
{
  "schema_version": "shorts-plan.v2",
  "source_candidates": {"path": "work/shorts/shorts_candidates.json", "schema_version": "shorts-candidates.v2"},
  "transcript": {"path": "work/shorts/transcript.json", "timebase": "input_video_relative"},
  "shorts": [{
    "id": "short_01",
    "short_id": "short_01",
    "candidate_id": "cand-001",
    "source_candidate_index": 1,
    "order": 1,
    "title": "Example",
    "scene_type": "solo_talk",
    "evidence_mode": "text_only",
    "start_time": 10.0,
    "end_time": 35.0,
    "duration": 25.0,
    "score_breakdown": {
      "hook": {"score": 16, "reason": "Immediate clear hook."},
      "completeness": {"score": 18, "reason": "Complete standalone thought."},
      "audience_value": {"score": 17, "reason": "Useful audience value."},
      "emotion_tension": {"score": 8, "reason": "Moderate stakes."},
      "quotability": {"score": 12, "reason": "Memorable standalone line."},
      "pace_editability": {"score": 8, "reason": "Compact editable delivery."}
    },
    "score": 80,
    "hook_sentence": "",
    "editorial_reason": "",
    "transcript_excerpt": "Exact candidate excerpt.",
    "filler_drop_spans": [{
      "type": "filler",
      "start_time": 20.0,
      "end_time": 20.4,
      "reason": "Independent filler word.",
      "review_status": "approved"
    }],
    "keep_spans": [
      {"start_time": 10.0, "end_time": 20.0},
      {"start_time": 20.4, "end_time": 35.0}
    ],
    "source_duration": 25.0,
    "filler_removed_duration": 0.4,
    "estimated_output_duration": 24.6,
    "validation": {"passed": true, "errors": [], "warnings": []},
    "outputs": {},
    "status": "planned"
  }],
  "rejected_candidates": []
}
```
