---
name: video-to-shorts
description: Select complete horizontal short-form moments, extract human-approved shorts, and optionally deliver deterministic Agent-planned vertical versions through mandatory, machine-enforced user interviews that cannot be replaced by Agent decisions.
---

# Video To Shorts

## Mandatory Human Interaction Contract

The candidate decision and every vertical-preview decision are mandatory user interviews. They are not optional recommendations. At each review gate, the Agent must:

1. Generate the review JSON and fixed Markdown question with `interaction.py` or `render_vertical.py --mode preview`.
2. Show the generated question and review artifact paths to the user.
3. End the current turn immediately. Do not call the next-stage script in the same turn.
4. In a later turn, record the user's verbatim response with `interaction.py`.
5. Continue only when the gate reports `approved`.

The Agent must not invent, infer, or silently substitute a user response. A user who replies without a candidate selection receives the defined default `text_visual` top-five selection, but that later user response is still required. Complete silence cannot advance an asynchronous Agent turn.

The scripts bind approvals to artifact hashes. Regenerating or editing reviewed candidates, plans, source media, or previews invalidates the approval. `plan.py`, `extract_shorts.py`, `vertical_plan.py`, and final vertical rendering reject missing, stale, skipped, or change-requested reviews.

## Transcript Input Boundary

The long-term responsibility of `video-to-shorts` is to consume a prepared standard word-level transcript. Candidate selection, planning, and extraction depend only on this data contract; they do not depend on a transcription model, device, or provider.

If an independent transcription skill is discovered, use it directly. If none is found, do not create or assume its directory, command name, provider framework, or output location. Any future transcription capability should produce the same standard `transcript.json`, and the caller should pass that file explicitly with `--transcript`.

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

## Required Candidate Evidence

Candidate evidence mode and delivery mode remain independent. Candidate selection uses the transcript plus visual review context through the single required `text_visual` evidence mode.

Store the required review artifacts here:

```text
WORK/shorts/preview/
  text_visual/
    shorts_candidates.json
    shorts_candidates_preview.html
```

The `shorts_candidates.json` file contains only `text_visual` candidates.

**Delivery mode:**

- `horizontal_only`: stop after approved horizontal shorts are extracted.
- `horizontal_and_vertical`: continue each approved horizontal short through Optional Vertical Delivery.

`text_visual` determines how the Agent selects content worth cutting. It does not determine vertical crop decisions. For every requested vertical delivery, the Agent must generate and inspect new dense visual evidence from that extracted short. Do not reuse sparse long-video candidate contact sheets as the basis for vertical cropping.

## Boundary

This skill owns transcript-based selection and extraction of horizontal short-source moments plus the formal optional vertical delivery workflow defined below. It does not own captions, graphics, color grading, or publishing. Vertical delivery currently supports fixed crops, scene-bounded fixed crops, and letterboxing; it does not claim continuous dynamic subject tracking.

## Optional Vertical Delivery

Vertical delivery begins only after a horizontal short has been extracted and approved. Required inputs are `short_XX/source.mp4` and `short_XX/transcript.json`.

Do not plan all vertical crops directly from the original long video. Each approved short has its own short-relative timeline, dense visual evidence, Agent-authored plan, preview, review decision, and final output under `short_XX/vertical-agent/`.

### Required Workflow

1. Create `short_XX/vertical-agent/`.
2. Generate dense visual context from `short_XX/source.mp4`. Sample every `1` second by default; use `0.5` seconds when subject or key-content movement is visually significant.
3. Inspect every paged contact sheet. Inspect individual original frames when a sheet is insufficient to judge a crop boundary or key content.
4. Choose exactly one top-level strategy: `STATIC_CROP`, `SCENE_CROP`, `LETTERBOX`, or `REVIEW_REQUIRED`.
5. Write `short_XX/vertical-agent/agent_vertical_plan.json` using the Vertical Plan Contract.
6. Run `vertical_plan.py` to probe the real media, validate the Agent's choices, and write normalized plan and preview documents.
7. Run `render_vertical.py --mode preview` before any formal render.
8. Inspect `preview/vertical_preview.mp4`, `preview/preview_contact_sheet.jpg`, and `preview/preview_summary.md`.
9. `render_vertical.py --mode preview` writes `review/vertical_review.json` and `review/vertical_review_question.md`. Show the fixed question and end the current turn.
10. In a later turn, record the verbatim user response with `interaction.py vertical-answer`.
11. Run `render_vertical.py --mode final` only when the review status is `approved`. `revise`, `skip`, silence, and ambiguous answers remain blocked.

```powershell
python skills/video-to-shorts/scripts/prepare_visual_context.py SHORT\source.mp4 `
  --out SHORT\vertical-agent\visual `
  --interval 1
```

The resulting `visual_manifest.json`, contact-sheet pages, and original frames are vertical planning evidence only. `visual_evidence` entries do not participate in candidate scoring.

### Composition Decision Order

Plan vertical delivery scene by scene. Do not choose one conservative strategy for the complete short merely because some scenes require full horizontal context.

Apply these priorities in order:

1. In presenter-led scenes, keep the speaker's head and torso complete, stable, and large enough for vertical viewing. Partial hand or forearm clipping is less severe than reducing the speaker to a small LETTERBOX foreground.
2. Preserve essential slides, diagrams, products, multiple subjects, and other information that would become incomplete or misleading when cropped.
3. Prefer `STATIC_CROP` or scene-bounded fixed crops for stable presenter and product scenes.
4. Use `LETTERBOX` only for the specific scenes where no safe fixed 9:16 crop preserves the essential horizontal information.
5. Use `REVIEW_REQUIRED` when safe composition would require continuous dynamic tracking or the evidence does not support a stable scene crop.

For a presenter-led or mixed short, first attempt a `SCENE_CROP` plan that uses fixed crops for stable presenter scenes and `LETTERBOX` only for wide-information scenes. The existence of one wide slide or product shot is not sufficient reason to LETTERBOX the complete short.

If the Agent chooses top-level `LETTERBOX`, its segment reason and visual evidence must explain why each stable presenter or product scene cannot use a safe fixed crop. The Agent must explicitly compare the full-LETTERBOX choice against a scene-bounded alternative.

### Vertical Strategies

#### STATIC_CROP

Use one fixed crop for the entire short when a single person remains in a small area, the camera is fixed, or all key content stays in the same region.

#### SCENE_CROP

Use different fixed crops for different time ranges when the short alternates between a speaker and slides, product and presenter, or multiple stable camera setups. Crop changes should occur at scene boundaries. Do not create frequent left-right jumps inside one continuous shot.

#### LETTERBOX

Scale the complete horizontal image into the vertical canvas and place it over a blurred, darkened full-canvas version of the same frame. Use it as a scene-level fallback for distant groups, wide slides, horizontally distributed products, or any case where a forced 9:16 crop would remove essential information. Do not use LETTERBOX only to preserve peripheral background or every part of a presenter's widest hand gesture. The complete foreground frame must remain sharp, centered, and fully visible; do not use a plain black background for LETTERBOX delivery. The renderer samples multiple frames to identify only stable pure-black borders. When stable borders are found, only the blurred background layer uses the complete active-picture area; when detection is unstable, the background safely falls back to the complete source frame. The sharp foreground is never cropped by this process.

#### REVIEW_REQUIRED

Use this when the subject moves continuously, people cross frequently, key content changes position too much, a safe crop needs continuous dynamic tracking, or none of the other strategies is safe. `REVIEW_REQUIRED` is a valid review outcome, not a failed run. Its plan and preview summary may be generated, but formal rendering is prohibited.

### Vertical Preview Review

Review both information safety and vertical viewing quality:

- Confirm that heads and torsos remain inside every presenter crop.
- Confirm that presenter-led scenes are not unnecessarily reduced to a small LETTERBOX foreground.
- Confirm that wide slides, products, and diagrams retain their essential information.
- Confirm that LETTERBOX is limited to the scenes that require complete horizontal context.
- Confirm that crop and LETTERBOX changes occur at real scene boundaries rather than inside a continuous shot.
- Review the strategy-duration percentages and every validator warning before approving the plan.

### Vertical Plan Contract

Write the Agent-authored input directly as JSON; do not create a separate schemas directory.

```json
{
  "source_video": "short_01/source.mp4",
  "target_aspect_ratio": "9:16",
  "source_width": 1280,
  "source_height": 720,
  "output_width": 406,
  "output_height": 720,
  "strategy": "STATIC_CROP",
  "segments": [
    {
      "start_time": 0.0,
      "end_time": 42.5,
      "strategy": "STATIC_CROP",
      "content_type": "PRESENTER",
      "crop_x": 420,
      "crop_y": 0,
      "crop_width": 406,
      "crop_height": 720,
      "reason": "The main speaker remains inside this crop across all sampled frames."
    }
  ],
  "visual_evidence": [
    {
      "timestamp_s": 0.0,
      "frame_path": "visual/visual_frames/frame_0001_000000s.jpg",
      "observation": "Speaker is centered."
    }
  ],
  "warnings": []
}
```

Contract rules:

- All times use the extracted short-relative timeline.
- `segments` must be sorted, non-overlapping, and fully cover the short duration.
- Every segment requires a non-empty Agent-authored `reason`.
- Every newly authored segment requires `content_type`: `PRESENTER`, `WIDE_INFORMATION`, `PRODUCT`, `MULTI_SUBJECT`, or `OTHER`. This is an Agent-authored visual classification, not model detection. The validator accepts omitted values as `UNSPECIFIED` only for compatibility and emits a warning.
- `STATIC_CROP` uses exactly one `STATIC_CROP` segment.
- `SCENE_CROP` may contain multiple scene-bounded fixed-crop segments and may use `LETTERBOX` for a scene that cannot be safely cropped.
- `PRESENTER` scenes should prefer a fixed crop when sampled evidence keeps the head and torso safe. Cropping part of a wide gesture is not by itself sufficient reason to use LETTERBOX.
- `WIDE_INFORMATION`, `PRODUCT`, or `MULTI_SUBJECT` scenes may use LETTERBOX when a fixed crop would remove essential information.
- `LETTERBOX` segments do not use crop fields. A full-duration LETTERBOX plan must explain why scene-bounded crops are unsafe for every stable scene.
- Crop rectangles must stay inside the real source dimensions and match `9:16` within integer-pixel tolerance.
- `vertical_plan.py` obtains source width, height, FPS, and duration with `ffprobe`; Agent-provided media metadata is not authoritative.
- Formal output keeps the source height by default. Output width is `round(source_height * 9 / 16)`, adjusted upward to an even integer.
- `REVIEW_REQUIRED` segments contain no crop fields and cannot be formally rendered.
- `visual_evidence` documents reviewed frames and observations; it never changes candidate score.
- The normalized plan includes deterministic strategy durations, percentages, and non-blocking validator warnings for full-duration LETTERBOX, presenter scenes using LETTERBOX, and missing `content_type`.
- Python validates the Agent's choices but never moves, generates, or replaces a crop.

### Vertical Commands

```powershell
python skills/video-to-shorts/scripts/vertical_plan.py `
  --video SHORT\source.mp4 `
  --input SHORT\vertical-agent\agent_vertical_plan.json `
  --out SHORT\vertical-agent

python skills/video-to-shorts/scripts/render_vertical.py `
  --video SHORT\source.mp4 `
  --plan SHORT\vertical-agent\vertical_plan.json `
  --out SHORT\vertical-agent `
  --mode preview

# STOP HERE. Show review/vertical_review_question.md and end the turn.

python skills/video-to-shorts/scripts/interaction.py vertical-answer `
  --out SHORT\vertical-agent `
  --response-file SHORT\vertical-agent\review\user_response.txt

python skills/video-to-shorts/scripts/render_vertical.py `
  --video SHORT\source.mp4 `
  --plan SHORT\vertical-agent\vertical_plan.json `
  --out SHORT\vertical-agent `
  --mode final
```

`vertical_plan.py` writes `vertical_plan.json`, `vertical_plan_preview.md`, and `vertical_plan_preview.html`. It does not detect subjects, call models, generate crops, or alter Agent-authored crop coordinates.

`render_vertical.py` consumes only a validated plan. It deterministically renders fixed crops, scene-bounded fixed crops, and letterboxing; preserves segment order and continuous short-relative audio; never overwrites `source.mp4`; writes media probes, contact sheets, and summaries; and refuses formal `REVIEW_REQUIRED` rendering.

### Vertical Output Layout

```text
short_XX/
  source.mp4
  transcript.json
  vertical-agent/
    agent_vertical_plan.json
    vertical_plan.json
    vertical_plan_preview.md
    vertical_plan_preview.html
    visual/
      visual_manifest.json
      visual_frames/
      contact_sheets/
    preview/
      vertical_preview.mp4
      preview_contact_sheet.jpg
      preview_summary.md
      media_probe.json
    out/
      vertical.mp4
      final_contact_sheet.jpg
      final_summary.md
      media_probe.json
```

## Agent-First Candidate Workflow

1. Create `WORK/shorts/preview/text_visual/`.
2. Read the prepared transcript and inspect the visual context.
3. Author `preview/text_visual/shorts_candidates.json`; every candidate must use `evidence_mode=text_visual`. Do not write `score`.
4. Validate the text-visual file and write `preview/text_visual/shorts_candidates_preview.html`.
5. Complete Candidate Artifact Text QA for the JSON and HTML.
6. Run `interaction.py candidate-open`, show the generated fixed question, and end the current turn before plan generation.

```powershell
python skills/video-to-shorts/scripts/candidates.py `
  --out WORK\shorts\preview\text_visual `
  --candidates WORK\shorts\preview\text_visual\shorts_candidates.json `
  --transcript WORK\shorts\transcript.json
```

Use explicit `--candidates` and `--transcript` paths. The script never calls a model API and never revises an Agent's dimension scores based on transcript content.

### Candidate Artifact Text QA

Before review, inspect every candidate title, all six score reasons, editorial reason, warnings, and visual observations/risks as standalone text. `metadata.editorial_reason` is required and must explain why the exact moment is worth promoting as a short; it must not repeat only the title or a generic phrase such as `good candidate`. Correct grammar, missing quotation boundaries, repeated words, incomplete phrases, and unclear references. Deterministic validation does not prove that Agent-authored prose is natural or grammatically correct.

Inspect the `text_visual` JSON and HTML and confirm that candidate IDs, titles, duration, transcript excerpt, score reasons, script-generated score, warnings, `filler_drop_spans`, and the three visual fields render correctly. Suspicious `?` or the Unicode `U+FFFD` replacement character in Agent-authored metadata may indicate encoding damage, but do not remove legitimate question marks from transcript excerpts or intentional questions.

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

### World Cup Scenario

- Select decisive goals, critical saves, costly mistakes and recoveries, momentum shifts, turning points, compact match narratives, and moments with a clear outcome.
- Keep the teams, scoreline, match stage, prior event, or stakes needed to interpret the moment.
- Preserve the competitive payoff, including the decisive play, reversal, final result, or consequence.
- Common bad boundaries begin after the necessary match setup or end before the decisive action, reversal, result, or consequence.
- Reject incomplete sequences, context-free highlights, match setup without payoff, and passages that end before the outcome is clear.

## Boundary Rules

- Never start or end in the middle of a sentence or thought.
- Every candidate must be complete and self-contained.
- `start_time` is the first word of the complete sentence or thought.
- `end_time` is after the final word of the complete sentence or thought.
- Any extraction pre-roll must remain outside the previous word's release tail; never include audible residue from the preceding sentence.
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

- `text_visual`: judge from transcript plus optional `visual_observations`, `visual_risks`, and `visual_keyframes`. These fields are review evidence only and never affect scoring.

## Candidate v2 Contract

Top-level fields: `schema_version`, optional `video`, optional `transcript`, optional `producer`, required `selection`, and required `candidates` array. The candidate file must set `selection.evidence_mode` to `text_visual`. Output `schema_version` is `shorts-candidates.v2`.

Each candidate requires:

- `candidate_id`: non-empty string.
- `title`: non-empty string.
- `scene_type`: `product_demo`, `conversation_interview`, `solo_talk`, or `world_cup`.
- `start_time`, `end_time`: numbers on the input-video-relative timeline; `0 <= start_time < end_time <= transcript duration`.
- `transcript_excerpt`: non-empty exact excerpt for that time range.
- `evidence_mode`: `text_visual`.
- `score_breakdown`: exactly the six dimensions; each contains only numeric `score` and non-empty string `reason`.
- `metadata`: object containing non-empty string `editorial_reason`.

Optional candidate fields:

- `warnings`: string array.
- `filler_drop_spans`: Agent-authored array of `{type, start_time, end_time, reason, review_status}` fully inside the candidate range. `type` must be `filler`.
- `visual_observations`, `visual_risks`, `visual_keyframes`: string arrays; non-empty only for `text_visual`.
- `review_status`: string, default `candidate`.
- Additional `metadata` fields such as `boundary_risk` or comparison notes.

The validator adds `duration` and computed `score`. Candidates overlapping more than 50% of the shorter candidate are deduplicated within the `text_visual` candidate file before human review.

### Template

```json
{
  "schema_version": "shorts-candidates.v2",
  "selection": {"evidence_mode": "text_visual"},
  "candidates": [{
    "candidate_id": "cand-001",
    "title": "A complete standalone moment",
    "scene_type": "solo_talk",
    "start_time": 12.0,
    "end_time": 42.0,
    "transcript_excerpt": "Exact transcript words in the selected range.",
    "evidence_mode": "text_visual",
    "score_breakdown": {
      "hook": {"score": 16, "reason": "Immediate clear promise."},
      "completeness": {"score": 19, "reason": "Premise and payoff are complete."},
      "audience_value": {"score": 18, "reason": "Useful standalone insight."},
      "emotion_tension": {"score": 8, "reason": "Moderate stakes."},
      "quotability": {"score": 12, "reason": "Contains a concise line."},
      "pace_editability": {"score": 8, "reason": "Dense delivery with removable filler."}
    },
    "metadata": {"editorial_reason": "The claim and adoption evidence form a complete, useful short."},
    "warnings": [],
    "filler_drop_spans": []
  }]
}
```

Set `selection.evidence_mode` and every candidate `evidence_mode` to `text_visual`, then include the optional visual evidence fields.

## Review Stop

Review `preview/text_visual/shorts_candidates.json` with `preview/text_visual/shorts_candidates_preview.html`.

Open the mandatory interview:

```powershell
python skills/video-to-shorts/scripts/interaction.py candidate-open `
  --out WORK\shorts
```

This writes `review/candidate_review.json` and `review/candidate_review_question.md`. Show the generated question verbatim and end the current turn. Do not create a plan, extract media, or record an answer in the same turn.

The fixed interview asks for:

- Optional `候选:` selection using the qualified references listed in the question.
- Required `交付:` selection: `horizontal_only` or `horizontal_and_vertical`.
- Optional `修改:` request, which keeps the workflow blocked.

Candidate behavior is deterministic:

- Explicit candidate references select only those candidates and preserve the user's order.
- An omitted `候选:` line, `候选: 默认`, or `候选: 跳过` selects the five highest-scoring `text_visual` candidates.
- The default is allowed only after a later user response. User silence cannot be recorded and cannot advance the workflow.
- A missing delivery mode, an unknown candidate, an ambiguous duplicate ID, or a change request keeps plan generation blocked.

In the later user-response turn, preserve the response verbatim and record it:

```powershell
python skills/video-to-shorts/scripts/interaction.py candidate-answer `
  --out WORK\shorts `
  --response-file WORK\shorts\review\user_response.txt
```

Continue only when the command reports `candidate review status: approved`. The approval is bound to the `text_visual` candidate file and the generated `review/approved_candidates.json` by SHA-256.

## Shorts Plan v2

After the mandatory candidate interview is approved, generate a deterministic plan:

```powershell
python skills/video-to-shorts/scripts/plan.py `
  --out WORK\shorts
```

`plan.py` has no `--candidates` or `--use-default-selection` bypass. It reads only the current approved review gate, verifies candidate hashes, and consumes `review/approved_candidates.json`. `extract_shorts.py` revalidates the same gate and rejects a plan containing an unapproved candidate. The planner requires `shorts-candidates.v2`, uses the script-generated candidate `score` and existing `score_breakdown`, and never recalculates editorial dimensions, changes their reasons, reads visual observations for scoring, or calls a model.

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

`editorial_reason` is required at candidate `metadata.editorial_reason` and is carried into the plan. `hook_sentence` remains optional and empty when absent; the planner does not invent editorial text.

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
    "evidence_mode": "text_visual",
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
