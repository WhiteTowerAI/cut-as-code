---
name: video-add-b-roll
description: Use when a talking-head, interview, documentary, or explanatory video needs deliberate transcript-timed visual cutaways from local media or Pexels.
---

# Video Add B-Roll

Add a small number of evidence-backed visual cutaways to an understood canonical Project Protocol
sequence. Read [broll-rules.md](reference/broll-rules.md) before planning or acquiring any
media. Use [example-broll-plan.json](examples/example-broll-plan.json) as the plan-shape
reference.

## Non-Negotiable Contract

Follow every editorial, provenance, still, review, recovery, and delivery rule in
[broll-rules.md](reference/broll-rules.md). Operationally:

- Use the provided scripts for acquisition, validation, normalization, receipt application,
  and verification. Never use a raw download path or substitute another stock source.
- Never fabricate human authority. Agent review requires explicit delegation and a truthful
  Agent receipt.
- Missing, weak, or downloader-rejected media becomes `skipped`; never use random or still
  fallback media.

## Requirements And Inputs

Require Python, `ffmpeg`, `ffprobe`, and Pillow. For Pexels, first use `PEXELS_API_KEY` from
the environment, then look for it in `skills/video-add-b-roll/.env`. If both are missing or
blank, stop and ask the user to add `PEXELS_API_KEY=<key>` to that file, then retry after they
confirm. Ask them to provide the key through the local `.env` file, never through chat. Never
place or print it in a command argument, plan, URL, log, review artifact, or response.

`/video-understand` is a prerequisite. Run it first so B-roll use the validated
word-level transcript and canonical timeline.
Before starting, verify that it is installed. If it is not, warn the user that
this prerequisite is missing and stop before processing media.

Run from the repository root and resolve the separate project root:

```powershell
$RepoRoot = (Resolve-Path '.').Path
$ProjectRoot = (Resolve-Path 'path/to/video-project').Path
$BrollEnv = Join-Path $RepoRoot 'skills/video-add-b-roll/.env'
if ([string]::IsNullOrWhiteSpace($env:PEXELS_API_KEY) -and (Test-Path -LiteralPath $BrollEnv)) {
  $PexelsKeyLine = Get-Content -LiteralPath $BrollEnv | Where-Object { $_ -match '^\s*PEXELS_API_KEY\s*=' } | Select-Object -Last 1
  if ($PexelsKeyLine) { $env:PEXELS_API_KEY = ($PexelsKeyLine -split '=', 2)[1].Trim().Trim('"').Trim("'") }
}
$BrollScripts = Join-Path $RepoRoot 'skills/video-add-b-roll/scripts'
$ProjectLib = Join-Path $RepoRoot 'skills/video-understand/scripts'
$ReviewVideo = & python -c "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[2]); import projectlib; root=Path(sys.argv[1]); project=projectlib.load_json(root/'work/project.json'); assert project.get('render',{}).get('status') == 'verified', 'current upstream delivery is not verified'; path=projectlib.resolve_project_path(root,project['render']['output']); assert path.is_file(), 'current upstream delivery is missing'; print(path)" $ProjectRoot $ProjectLib
if ($LASTEXITCODE -ne 0) { throw 'Complete the active upstream delivery before B-roll review.' }
$ReviewVideo = (Resolve-Path -LiteralPath $ReviewVideo).Path
```

Consume these canonical inputs instead of re-transcribing or re-analyzing:

- `work/project.json`
- `work/timeline.json`
- `work/understand/transcript.json`
- `work/understand/understanding.json`
- a current program-time review video whose pixels include active cut and color-grade work

`$ReviewVideo` is that existing verified upstream delivery, not a filename to invent or a
new B-roll render. It must already match the active timeline duration, dimensions, and FPS.
If it is absent or stale, finish the upstream cut/color-grade delivery first, then resolve and
hash it before continuing.

The operation always depends on `understanding`, plus `cut` and `color-grade` when those
operations are active on the target sequence. Copy their current positive integer revisions
to `based_on`. When color grade is active, record both the grade-plan and selected-LUT hashes;
normalization must receive that exact selected LUT and pre-apply it to every selected B-roll
shot.

The canonical sequence order is:

```text
cut -> color-grade -> b-roll -> captions -> content-cards -> graphic-motion
```

The registered operation must have `changes_video_pixels: true`, add the `b-roll` track, and
leave timeline, geometry, and audio unchanged. `broll_plan.register_operation()` writes this
contract; do not hand-build the operation.

## Durable And Disposable Files

```text
work/b-roll/broll-plan.json                         # durable domain plan
work/b-roll/presentation-decision.json               # durable Agent-chat route decision
work/b-roll/broll-interaction.json                  # durable applied receipt
work/b-roll/broll-selection.json                    # durable approved exact selection and consumed-page binding
work/b-roll/speaker-inset-analysis.json             # durable scene/evidence packet
work/b-roll/speaker-inset-agent-input.json          # durable Agent ROI decisions
work/b-roll/speaker-inset-preview.json              # durable exact preview bindings
work/b-roll/speaker-inset-clearance.json            # durable Agent obstruction check
work/b-roll/broll-revision-request-<UUID>.json      # durable unapproved request bytes
work/b-roll/candidate-search.json                   # durable query and provider order
work/b-roll/candidate-analysis.json                 # durable deterministic evidence
work/b-roll/candidate-ranking.json                  # durable Agent ranking and Top 3
work/cache/b-roll/candidate-analysis/media/         # disposable analysis variants
work/cache/b-roll/candidate-analysis/frames/        # reproducible samples and crops
work/cache/b-roll/candidates/                       # frozen acquired media
work/cache/b-roll/speaker-inset/                    # reproducible evidence and previews
work/cache/b-roll/normalized/                       # reproducible silent overlays
review/03-b-roll/candidate-analysis-<UUID>/          # immutable analysis packet
review/03-b-roll/candidate-analysis-<UUID>.md        # analysis and baseline summary
review/03-b-roll/candidate-analysis-<UUID>/candidate-index.html
review/03-b-roll/b-roll-review-<UUID>.html          # immutable candidate review
review/03-b-roll/b-roll-review.html                 # latest convenience alias
review/03-b-roll/stills/                            # first/middle/last verification frames
review/03-b-roll/contact-sheet.jpg
review/03-b-roll/boundary-reel.mp4
review/03-b-roll/b-roll-summary.md
```

Keep the plan and receipt outside `work/cache/`. Treat candidate and normalized files as
reproducible but hash-bound inputs.

## Workflow

### 1. Establish Current Dependencies

Read the active sequence, operation revisions, timeline, transcript, understanding, active
grade plan, and selected LUT. Confirm that the review video matches the active timeline's
duration, dimensions, and rational FPS. Hash the transcript, timeline, review video, and
active grade inputs into `input_hashes`.

Use `broll_plan.active_dependencies(project)` to derive the exact dependency list. A changed
timeline, transcript, dependency revision, grade plan, LUT, review video, candidate manifest,
or reviewed asset makes downstream work stale; refresh the plan and repeat review rather than
carrying an old receipt forward.

### 2. Author A Dynamic-Social Plan

Hand-author `work/b-roll/broll-plan.json`; scripts perform precision, not editorial judgment.
For each proposed shot:

- choose a positive, half-open, non-overlapping program range in chronological order;
- map it through `work/timeline.json` into exact `source_ranges`;
- preserve at least one exact mapped transcript word with source/program ranges and clip ID;
- state a concrete `editorial_reason` and `visual_intent`;
- set `brief.search_context` with a concrete `topic`, `visual_direction`, and `1-12 unique keywords`;
- set each `semantic_role` to `direct`, `supportive`, or `atmospheric`;
- write two or three layered literal English queries: a `direct subject/action` query, a
  `defensible context/process` query, and, when a third query is useful, a `theme-enhancing variant`;
- begin at `planned`, move to `candidates_ready` after acquisition, or use `skipped` when no
  relevant candidate exists.

Keep `brief.density` equal to `dynamic-social`. Planned coverage begins with a complete A-roll
scan of the mapped transcript and timeline, followed by hand-authored chronological, non-overlapping,
editorially valid ranges. Treat `0.40` to `0.70` as a soft target. Below `0.40`, take one second
pass and only add or extend defensible ranges. Above `0.70`, internally review A-roll concealment.
Never add irrelevant filler or weaken relevance, rights, quality, or another eligibility gate to hit
the target. Generic topical terms such as `tech` or `entertainment` may refine a query only; they
never replace the per-shot visible relationship between the candidate and the transcript claim.
If no moment earns B-roll, an approved all-skipped plan is a valid no-op.

Do not add `speaker_inset_style` while authoring the draft. After candidate acquisition, the
explicit Agent-chat presentation decision selects the ordinary or speaker-inset route. The latter
automatically installs the strict project-level rounded-rectangle style: `width_ratio: 0.39`, gray
border, aspect ratio, corner radius, margins, and subtitle-safe bottom area. Preset and anchor do
not belong to the style. The Agent records `project_layout_strategy` plus one per-shot
`layout_recommendation` after inspecting the exact selected media. Never introduce a face detector,
segmentation model, cross-cut identity tracker, or guessed ROI. Fit speaker ROI pixels into the
window with aspect-preserving cover scaling; never stretch them to the configured aspect ratio.
Center the crop horizontally and anchor it to the top so the complete head and face take priority
over lower-body coverage.

Validate the draft after every material edit:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; plan=projectlib.load_json(root/'work/b-roll/broll-plan.json'); timeline=projectlib.load_json(root/'work/timeline.json'); transcript=projectlib.load_json(root/'work/understand/transcript.json'); project=projectlib.load_json(root/'work/project.json'); errors=broll_plan.validate_plan(plan,timeline,transcript,project=project,project_root=root,verify_files=True); print('\n'.join(errors) if errors else 'B-roll plan valid'); raise SystemExit(bool(errors))" $ProjectRoot $BrollScripts
```

### 3. Analyze, Rank, And Freeze Candidates

Candidate analysis is advisory evidence before `candidates_ready`. It does not select media,
approve a shot, add a receipt, or change the lifecycle. Keep the existing two or three literal
queries for every shot.

For local video, write truthful provenance and import it through the existing acquisition path:

```powershell
python "$BrollScripts/pexels.py" import-local `
  "$ProjectRoot/input/example-owned-footage.mp4" `
  "$ProjectRoot/work/cache/b-roll/candidates/example-owned-footage.mp4" `
  "$ProjectRoot/work/b-roll/example-local-provenance.json"
```

Copy the returned record into the shot's `candidates`. Candidate analysis reads that exact frozen
cache file; it does not copy it into another provider or analysis system. Use `--local-only` when
the plan should not query Pexels.

Collect Pexels results with round-robin query merging, provider-ID deduplication, and a maximum
of eight unique provider videos per shot. Choose the orientation that matches the timeline:

```powershell
$CandidateAnalysis = Join-Path $BrollScripts 'candidate_analysis.py'
python $CandidateAnalysis search `
  $ProjectRoot `
  "$ProjectRoot/work/b-roll/broll-plan.json" `
  "$ProjectRoot/work/b-roll/candidate-search.json" `
  --orientation portrait `
  --per-page 8
```

For local-only analysis, add `--local-only`. The search record preserves every literal query,
its original provider order, the round-robin order, and both Pexels variants. The analysis variant
is the smallest orientation-matched file whose short edge is at least 480 pixels, or the largest
valid matching file when none qualifies. The delivery variant remains the highest-resolution
orientation-matched file.

Download and fully decode only analysis variants, sample them at 10/30/50/70/90 percent, and
write deterministic machine evidence:

```powershell
python $CandidateAnalysis analyze `
  $ProjectRoot `
  "$ProjectRoot/work/b-roll/broll-plan.json" `
  "$ProjectRoot/work/b-roll/candidate-search.json" `
  "$ProjectRoot/work/timeline.json" `
  "$ProjectRoot/work/b-roll/candidate-analysis.json"
```

The analysis contains hard checks, objective warnings, sampled-frame and center-crop hashes,
contact sheets, luma/clipping/edge/motion evidence, and duplicate evidence. It preserves the
shot-local exact rejection and strict perceptual threshold, then adds project-wide exact identity,
strict perceptual groups, and non-suppressing `possible_series` hints. Hard rejection is limited to
the objective failures in `reference/broll-rules.md`.

Inspect the exact transcript evidence, five frames, crop simulations, warnings, and duplicate
evidence. Write `work/cache/b-roll/candidate-ranking-input.json` with this shape:

```json
{
  "schema_version": 1,
  "analysis_sha256": "<canonical SHA-256 of candidate-analysis.json>",
  "mode": "agent",
  "actor": "<real Agent name>",
  "timestamp": "<timezone-aware timestamp>",
  "overall_rationale": "<non-empty rationale>",
  "near_duplicate_groups": [{
    "group_id": "<stable group id>",
    "match_type": "same_series",
    "actor": "<real Agent name>",
    "timestamp": "<timezone-aware timestamp>",
    "members": [
      {"shot_id": "<shot id>", "candidate_id": "<candidate id>"},
      {"shot_id": "<other shot id>", "candidate_id": "<other candidate id>"}
    ],
    "rationale": "<specific visible repetition across the two transcript moments>"
  }],
  "shots": [{
    "shot_id": "<shot id>",
    "candidates": [{
      "candidate_id": "<candidate id>",
      "semantic_fit": 0,
      "context_fit": 0,
      "composition_fit": 0,
      "style_fit": 0,
      "text_logo_risk": "uncertain",
      "avoid_violation": false,
      "primary_subject_visible": true,
      "near_duplicate_group": null,
      "rationale": "<candidate-specific evidence>"
    }]
  }]
}
```

Use integer fit scores from 0 through 4 against visible frozen-frame evidence: 0 is a mismatch or
unusable, 1 is weak, 2 is acceptable with concerns, 3 is strong, and 4 is unusually strong.
`text_logo_risk` is 0 through 4 or `uncertain`; never claim OCR. Both `semantic_fit == 0` and
`context_fit == 0` are retained hard ineligibility protections. `semantic_fit == 0` rejects a
candidate for semantic mismatch; `context_fit == 0` rejects unsupported context. A
`semantic_fit` 1 remains eligible as `weak_semantic_match` when it passes the context and other
independent gates, and ranks below semantic 2-4 matches. Score every analyzable candidate,
preserve the real Agent identity, and do not use
`mode: "human"` for ranking. Confirm a project-wide near-duplicate group only after comparing the
frozen frames, transcript evidence, visual intent, provider identity, creator, and source title.
Do not confirm from creator identity alone. Omit `near_duplicate_groups` when none are confirmed;
the per-candidate `near_duplicate_group` field remains accepted for older shot-local records.

Validate and apply the fixed public ranking rules:

```powershell
python $CandidateAnalysis rank `
  $ProjectRoot `
  "$ProjectRoot/work/b-roll/candidate-analysis.json" `
  "$ProjectRoot/work/cache/b-roll/candidate-ranking-input.json" `
  "$ProjectRoot/work/b-roll/candidate-ranking.json"
```

See [example-candidate-ranking.json](examples/example-candidate-ranking.json) for the durable
ranking shape. Rank eligible candidates in semantic-first lexicographic order: `semantic_fit`, then
`context_fit`, then the combined `composition_fit + style_fit` score, fewer deterministic warnings,
and finally stable provider and candidate IDs. Exact project duplicates and Agent-confirmed near
duplicates are allocated to the shot with the strongest semantic/context evidence, then each
affected shot refills from its next independent eligible candidate. `possible_series` never
suppresses automatically. A shortlist contains at most three candidates; fewer than three is valid
and no eligible result must be `no_eligible_candidates`.

Only after ranking, acquire the full delivery variants and bind their exact bytes plus the active
analysis/ranking hashes into the plan:

```powershell
python $CandidateAnalysis acquire `
  $ProjectRoot `
  "$ProjectRoot/work/b-roll/broll-plan.json" `
  "$ProjectRoot/work/b-roll/candidate-analysis.json" `
  "$ProjectRoot/work/b-roll/candidate-ranking.json"
```

The acquire command moves a shot only to `candidates_ready` or `skipped`. It cannot select a
candidate or approve a plan. The downloader owns `.part` recovery for both analysis and delivery
variants. Never manually promote, rename, or delete a `.part` file.

Publish the immutable analysis packet before exact-candidate review:

```powershell
python $CandidateAnalysis publish `
  $ProjectRoot `
  "$ProjectRoot/work/b-roll/candidate-analysis.json" `
  "$ProjectRoot/work/b-roll/candidate-ranking.json"
```

External generation still follows `import-local` with `source_type: "external-generated"` and
complete truthful provenance. This is import only, not authorization to call a generation service.

### 3a. Choose The Presentation Route In Agent Chat

After acquisition produces `candidates_ready` or `skipped` shots, inspect the exact A-roll and
frozen candidate evidence. In the current Agent chat, present an Agent recommendation for either `ordinary`
full-screen B-roll or `speaker-inset`, with a concrete rationale. Then ask the user for an explicit
route choice in natural language. Do not infer this choice from the original draft, a candidate
selection, or silence.

Record the reply with `broll_plan.record_chat_presentation_decision()`. Its input must preserve the
actual `user_response`, the Agent `presentation_mode` recommendation and rationale, the real user
actor, a UUID and timestamp, `explicit_user_action: true`, and
`rationale_source: "agent_chat_explicit_action"`. It writes the hash-bound
`work/b-roll/presentation-decision.json` receipt and the plan's `presentation` binding. The receipt
binds the review-video, candidate manifest, and pre-review plan hashes. A changed candidate
manifest or review video requires a new chat choice before a review page can be published. A
candidate revision may change shot timing and segment defaults while carrying the original route
binding forward.

Choosing `ordinary` removes any speaker style and continues to the existing one-page exact
candidate review. Choosing `speaker-inset` installs the default rounded-rectangle style while
keeping the first page authoritative for exact B-roll candidate, timing, segment-order, speed, and
skip decisions. That page emits `submission_intent: "approve_selection"` with
`approval_scope: "b-roll-selection"`; applying it keeps selected shots `composite_pending` only
because the new speaker presentation still needs review. The chat response selects a route; it
never substitutes for either webpage's explicit review action.

### 4. Publish And Complete Exact-Candidate Review

Set `input_hashes.review_video_sha256` to the actual current review video's SHA-256, revalidate,
then confirm the current Agent-chat presentation receipt and publish the immutable local review:

```powershell
$ReviewPublication = & python "$BrollScripts/build_review_page.py" `
  "$ProjectRoot/work/b-roll/broll-plan.json" `
  "$ProjectRoot/review/03-b-roll" `
  --video $ReviewVideo `
  --timeline "$ProjectRoot/work/timeline.json" `
  --transcript "$ProjectRoot/work/understand/transcript.json" `
  --project-root "$ProjectRoot" | ConvertFrom-Json

Start-Process (Resolve-Path "$ProjectRoot/review/03-b-roll/b-roll-review.html")
```

Apply the review checks in `reference/broll-rules.md`. The page uses the readable mapped transcript
as the primary A-roll context. It keeps word timing, clip mapping, search queries, and full
provenance in the payload while placing technical details behind collapsed disclosures. Visible
time values use at most two decimal places. Insert start/end move in explicit 0.5-second steps
inside the displayed original-value plus-or-minus-two-second bounds, then snap exported values to
the rational timeline frame grid. Select one to three ordered, unique candidates from the
hash-bound Top 3 for a shot. The page divides a new multi-candidate choice by integer timeline
frames, lets the user reorder segments or adjust an adjacent boundary, and keeps the total shot
range unchanged. Clip start uses a `0.1s` input step. A normal Boundary click moves the nearest
integer-frame equivalent of `0.1s`; `Alt` on Windows/Linux or `Option` on macOS moves exactly one
timeline frame. Choose only `0.5x`, `1x`, `1.5x`, or `2x` playback for each segment. Source end is
read-only and is derived from source start, allocated program frames, frame duration, and playback
rate. The page gives immediate English guidance when source coverage is invalid, including the
shortage, latest legal start, feasible rates, and available Boundary/candidate repairs. These
display-only diagnostics are never included in the review receipt. A visible `Fit to A-roll`
result remains required before export. Copy and Download JSON remain disabled when no legal fit
exists, and their JSON records every ordered segment, range, and playback rate at frame precision.

The route is chosen once in Agent chat before the first candidate page. Candidate, skip,
program/source timing, segment boundary/order/speed, Fit to A-roll, and Ken Burns edits made with
that page's controls do not force revision. Leave `Modification notes` empty and explicitly select
Approve to export the current exact configuration: `submission_intent: approve` for the ordinary
route or `submission_intent: approve_selection` for the speaker-inset route. Python revalidates the
export before applying it directly.

Enter non-empty natural-language `Modification notes` only for requested changes the page controls
cannot express. This selects Request changes and exports `submission_intent: request_revision`;
Empty Request changes is invalid. Only such natural-language requests enter the revision, rebuild,
and new-page flow. The rebuilt proposal preserves the first `ordinary` or `speaker-inset` route;
do not ask the user to choose ordinary or speaker-inset again. The
`presentation-decision.json` receipt remains unchanged; only its existing plan binding is carried
forward with an explicit revision marker. Candidate selection and speaker composite approval remain
separate.
`Copy` is the primary handoff and places the complete JSON in both a readonly textarea and the
clipboard when available. `Download JSON` downloads those same bytes for durable local transfer.
Both preserve the same explicit approval receipt bytes; neither mutates the plan until the Agent
validates and applies the transferred JSON.

After `Download JSON`, bind the actual operator-chosen download location rather than assuming it is
in the review directory:

```powershell
$ReviewExport = (Resolve-Path -LiteralPath "<browser-download-directory>/b-roll-review-$($ReviewPublication.review_id).json").Path
```

For human mode, present the page and stop. Apply only the complete JSON the user explicitly copies
or downloads; preserve copied JSON byte-for-byte in a file before validation. It must contain
`explicit_user_action: true`. For Agent mode, proceed only when the user has
explicitly delegated the decision or requested autonomous completion. Inspect the same exact
assets, record truthful decisions under `mode: "agent"`, name the real Agent actor, and give
a non-empty decision rationale. Never create a human-mode receipt from silence or inference.

Present the candidate-analysis summary and this exact full-candidate page together, then stop.
Do not apply review, normalize, build a render plan, or render delivery until the user explicitly
copies, downloads, or approves exact candidate selections in a later turn. Agent ranking is not
user approval.

After a valid candidate export is applied, treat that UUID page as consumed as immutable evidence.
Keep it on disk, but must not present it again, reopen its convenience alias, or ask the user to
confirm the same B-roll choices. Reopen or republish candidate review only for an invalid or stale
export, an explicit candidate `request_revision`, changed hash-bound inputs, or an explicit user
request. A clipboard/download retry transfers the same receipt; it is not editorial reapproval.

Inspect `submission_intent` before applying anything. For `request_revision`, preserve the exact
export bytes under `work/b-roll`, validate them against the old immutable page, rebuild an
unapproved proposal, and reclassify duration evidence without redownloading or resampling:

```powershell
$Revision = Get-Content -LiteralPath $ReviewExport -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Revision.submission_intent -ne 'request_revision') { throw 'Expected request_revision.' }
$SavedRequest = Join-Path $ProjectRoot "work/b-roll/broll-revision-request-$($Revision.review_id).json"
[IO.File]::Copy($ReviewExport, $SavedRequest, $false)

python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; plan=projectlib.load_json(root/'work/b-roll/broll-plan.json'); request=projectlib.load_json(sys.argv[3]); timeline=projectlib.load_json(root/'work/timeline.json'); transcript=projectlib.load_json(root/'work/understand/transcript.json'); errors=broll_plan.validate_revision_request(plan,request,timeline,transcript); print('\n'.join(errors) if errors else 'Revision request valid'); raise SystemExit(bool(errors))" $ProjectRoot $BrollScripts $SavedRequest

python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; path=root/'work/b-roll/broll-plan.json'; plan=projectlib.load_json(path); request=projectlib.load_json(sys.argv[3]); timeline=projectlib.load_json(root/'work/timeline.json'); transcript=projectlib.load_json(root/'work/understand/transcript.json'); projectlib.write_json(path,broll_plan.rebuild_plan_from_revision(plan,request,timeline,transcript))" $ProjectRoot $BrollScripts $SavedRequest

python "$BrollScripts/candidate_analysis.py" reclassify `
  $ProjectRoot `
  "$ProjectRoot/work/b-roll/broll-plan.json" `
  "$ProjectRoot/work/b-roll/candidate-analysis.json" `
  "$ProjectRoot/work/timeline.json" `
  "$ProjectRoot/work/b-roll/candidate-analysis.json"
```

The rebuilt proposal preserves the original `presentation` decision and, for `speaker-inset`, its
validated style. Do not call `record_chat_presentation_decision()` again after a candidate revision.
The original `presentation-decision.json` receipt remains unchanged and its candidate-manifest and
review-video bindings remain mandatory.

Inspect every `agent_rescore_required` marker. When true, compare the revised transcript evidence
against the same frozen frames and write a truthful Agent score update; never carry a semantic
rationale across changed evidence by inference. Rerun `rank` and `acquire` so the plan binds the new
analysis/ranking hashes. Existing SHA-256-identical analysis and delivery media are reused. Publish
a new UUID review page with `build_review_page.py`, present it, and stop again. Never route a
revision request to `apply_review()` or convert `revision_notes` into a human rationale.

For an `ordinary` chat decision, apply the received one-page approval JSON and durably bind the
interaction receipt:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; path=root/'work/b-roll/broll-plan.json'; plan=projectlib.load_json(path); review=projectlib.load_json(sys.argv[3]); timeline=projectlib.load_json(root/'work/timeline.json'); transcript=projectlib.load_json(root/'work/understand/transcript.json'); updated=broll_plan.apply_review(plan,review,mode=sys.argv[4],actor=sys.argv[5],rationale=review['rationale'],interaction_path=root/'work/b-roll/broll-interaction.json',timeline=timeline,transcript=transcript,project_root=root); projectlib.write_json(path,updated)" $ProjectRoot $BrollScripts $ReviewExport human "Actual user name"
```

Use `human` and the actual human actor only after explicit user export. A new human approve uses
the page's factual `review_ui_explicit_action` rationale; it does not claim to quote a user-authored
reason. Agent mode still requires the real Agent actor and a specific exported Agent rationale.

For a `speaker-inset` chat decision, apply the first-page authoritative selection:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; path=root/'work/b-roll/broll-plan.json'; plan=projectlib.load_json(path); selection=projectlib.load_json(sys.argv[3]); timeline=projectlib.load_json(root/'work/timeline.json'); transcript=projectlib.load_json(root/'work/understand/transcript.json'); updated=broll_plan.approve_selection(plan,selection,mode=sys.argv[4],actor=sys.argv[5],rationale=selection['rationale'],project_root=root,timeline=timeline,transcript=transcript); projectlib.write_json(path,updated)" $ProjectRoot $BrollScripts $ReviewExport human "Actual user name"
```

Then use
`speaker_inset.py` for evidence, Agent ROI, layout recommendation, exact anchor previews, and clearance; follow
`reference/broll-rules.md`. The Agent must assess `focused-panel`, `full-bleed-wash`, and
`corner-pip`, choose a project primary preset, and keep one preset and anchor for each complete
shot. Distant, full-body, side, or back views are not automatically `occluded`: first use temporal
continuity, stage position, clothing, motion, and transcript context to decide whether the current
speaker is confirmed. For every confirmed subshot, try stable full-duration ROI keyframes with the
complete head, chin, and reasonable headroom as a hard constraint; gestures, body, and lectern
context are secondary. Expand to a stable speaking-region ROI before giving up, and never crop the
head merely to make the subject appear larger. Agent input must still use `enabled` for confirmed
speakers so the exact preview exists before any quality fallback. `corner-pip` supports only the
shot-level `top-left` and `top-right` anchors. Publish only the
new hash-bound `review_stage: composite` page. Show the approved B-roll there as read-only,
default-collapsed context; do not render candidate checkboxes, skip/timing/speed controls, or emit
candidate `shots` in its receipt. The user's composite decision covers only ROI, layout,
clearance, continuity, style, and exact composite pixels. Agent recommendation is advisory;
present the exact composite page and stop for user approval.

A candidate revision creates a new candidate UUID page and selection receipt before rebuilding
speaker artifacts while preserving the first selected `ordinary` or `speaker-inset` route. A
composite-only revision creates a new composite UUID page while preserving
the approved `selection_sha256`; it cannot silently change B-roll. After composite approval,
derive candidate decisions from the approved selection and transition `composite_pending` shots
without asking for the same content decision again.

Before accepting `ambiguous`, request dense supplemental evidence inside that subshot and rebuild
the analysis hash. At clearance, inspect entry, middle, exit, and a reasoned motion-risk frame in
the exact final-size preview; record `not_applicable` with a reason when there is no extra
motion-risk point. Use `build_pixel_budget()` to record the actual cover crop, inset pixels, scale,
maximum scale, and `low` (`<=1.5x`), `medium` (`>1.5x` and `<=3.0x`), or `high` (`>3.0x`) warning.
Pixel risk is evidence only and never changes `display_mode`. Require `subject_legibility: pass`
for every displayed subshot. A confirmed speaker that remains unreadable throughout the exact
preview may become `pure_broll` only at clearance with `subject_legibility: fail` and
`clearance_status: subject_illegible`; keep its ROI/keyframes and preview-bound evidence for audit.
Use `no_safe_position` only for B-roll obstruction, with `subject_legibility: not_applicable`.
Split a subshot on a legal frame boundary when only a sustained portion is unreadable; do not
disable a whole shot for one or two blurred frames. Record a shot-level continuity decision. Treat
an enabled run shorter than 1.5 seconds followed by a longer pure-B-roll run as `short_flash`; extend
the independently confirmed ROI, disable the whole shot inset, or record a specific intentional
transition. Never relax the confirmed-speaker rule to hide a continuity problem.

### 5. Normalize Approved Selections

With active color grade, pass the exact selected `.cube` path from the grade plan:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import normalize_broll; normalize_broll.normalize_plan(root/'work/b-roll/broll-plan.json',root/'work/timeline.json',root,lut=Path(sys.argv[3]).resolve())" $ProjectRoot $BrollScripts "$ProjectRoot/final/selected-color-look.cube"
```

Without active color grade, call the same API with `lut=None`. Never omit the LUT when color
grade is active and never apply an unselected look. For an enabled inset without active color
grade, pass the exact hash-bound review video explicitly:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import normalize_broll; normalize_broll.normalize_plan(root/'work/b-roll/broll-plan.json',root/'work/timeline.json',root,lut=None,review_video=Path(sys.argv[3]).resolve())" $ProjectRoot $BrollScripts $ReviewVideo
```

With active color grade and an enabled inset, pass both exact inputs:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import normalize_broll; normalize_broll.normalize_plan(root/'work/b-roll/broll-plan.json',root/'work/timeline.json',root,lut=Path(sys.argv[3]).resolve(),review_video=Path(sys.argv[4]).resolve())" $ProjectRoot $BrollScripts "$ProjectRoot/final/selected-color-look.cube" $ReviewVideo
```

For every canonical one-to-three-segment video selection, the normalizer reads the frozen original
candidates directly and performs trim, playback rate, scale/crop, SAR, rational FPS, exact frame
allocation, optional LUT, and hard concat in one filtergraph and one encoder call. A single segment
maps its chain directly. Do not create, read, or recover per-segment MP4 files or sidecars.

Every new B-roll delivery intermediate uses the fixed
`libx264 / CRF 18 / preset medium / yuv420p / MP4 / +faststart / no audio` profile and records its
complete versioned profile plus source-segment and grade bindings. This applies to ordinary
`broll-NNN.mp4`, speaker `broll-NNN-base.mp4`, and the final speaker composite `broll-NNN.mp4`.
Candidate/context/anchor previews, boundary reels, and the shared final renderer keep their existing
encoding behavior. Legacy component-based records remain read-only compatible and must not be
reported as source-direct or upgraded to the fixed profile.

Each asset is written to `.part.mp4`, checked for probe, full decode, geometry, FPS, duration,
silence, and SHA-256, then published with `os.replace`. The canonical plan is separately written to
`.part.json`; do not claim a cross-file transaction. On failure, leave the current shot `selected`,
remove this attempt's parts and newly published unreferenced shot assets, and preserve completed
shots. Rerun the complete failed shot from the original candidates; do not recover segment state.

### 6. Verify And Pre-Register

Run the verifier against the same current program-time review video:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import check_broll; check_broll.verify_plan(root/'work/b-roll/broll-plan.json',root/'work/timeline.json',root,Path(sys.argv[3]))" $ProjectRoot $BrollScripts $ReviewVideo
```

It revalidates hashes and receipts, probes and decodes normalized clips, marks selected shots
`verified`, and publishes first/middle/last stills, a contact sheet, a short boundary reel,
and the immutable machine summary. The summary deliberately remains `Manual review status:
pending.` Inspect applicable artifacts using `reference/broll-rules.md`. If any check fails,
fix the plan or selection and repeat review, normalization, and verification. Do not edit
hash-bound verification artifacts in place.

Pre-register from the verified plan before building delivery. Selected shots create an
`approved` operation whose check remains pending against the machine summary; this is the
operation the renderer consumes. An all-skipped plan removes any stale B-roll operation and
leaves no empty active operation:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; project_path=root/'work/project.json'; project=projectlib.load_json(project_path); plan=projectlib.load_json(root/'work/b-roll/broll-plan.json'); projectlib.write_json(project_path,broll_plan.register_operation(project,plan))" $ProjectRoot $BrollScripts
```

### 7. Build Delivery, Complete Visual Review, And Finalize

Compile approved active operations and render delivery once:

```powershell
python "$RepoRoot/skills/video-understand/scripts/build_render_plan.py" $ProjectRoot
python "$RepoRoot/skills/video-understand/scripts/render_project.py" `
  "$ProjectRoot/work/render/render-plan.json"
```

Open and inspect the final delivery, contact sheet, boundary reel, and representative
first/middle/last stills:

```powershell
Start-Process "$ProjectRoot/final/final-video.mp4"
$ContactSheet = "$ProjectRoot/review/03-b-roll/contact-sheet.jpg"
$BoundaryReel = "$ProjectRoot/review/03-b-roll/boundary-reel.mp4"
$Stills = "$ProjectRoot/review/03-b-roll/stills"
if (Test-Path -LiteralPath $ContactSheet) { Start-Process $ContactSheet }
if (Test-Path -LiteralPath $BoundaryReel) { Start-Process $BoundaryReel }
if (Test-Path -LiteralPath $Stills) { Get-ChildItem $Stills -File | Select-Object -First 3 | ForEach-Object { Start-Process $_.FullName } }
Get-Content "$ProjectRoot/review/03-b-roll/b-roll-summary.md"
```

After actual inspection, create an Agent- or human-authored JSON export containing the active
`review_id`, the canonical SHA-256 of the verified plan without `visual_review`, a timezone-aware
`timestamp`, `mode`, real `actor`, non-empty `rationale`, and exactly these boolean results:
`semantic_fit`, `unwanted_logos_or_text`, `jump_cuts`, `entry_exit_boundaries`, and
`grade_match`. When the inset is enabled, also require `speaker_layout_fidelity`,
`speaker_legibility`, and `broll_focal_clearance`. Every applicable result must be `true`. Use `mode: "human"` and
`explicit_user_action: true` only after an explicit user action; otherwise use delegated
`mode: "agent"`. Never infer or fabricate a human pass.

Complete the final visual review before final registration. This writes the durable receipt and
completed report, binding the plan UUID/hash, verifier stills, contact sheet, boundary reel,
pending machine summary, and final video by SHA-256:

```powershell
$VisualReviewExport = "$ProjectRoot/work/b-roll/b-roll-visual-review-export.json"
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]).resolve(); sys.path.insert(0,sys.argv[2]); import check_broll,projectlib; check_broll.complete_visual_review(root/'work/b-roll/broll-plan.json',root,projectlib.load_json(sys.argv[3]),root/'final/final-video.mp4')" $ProjectRoot $BrollScripts $VisualReviewExport
```

Run registration again. It finalizes the exact pre-registered operation in place as
`verified`, points `operation.check.report` to `b-roll-visual-review.md`, and preserves its
revision, render contributions, sequence position, and verified delivery status. It does not
request another render:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; project_path=root/'work/project.json'; project=projectlib.load_json(project_path); plan=projectlib.load_json(root/'work/b-roll/broll-plan.json'); projectlib.write_json(project_path,broll_plan.register_operation(project,plan))" $ProjectRoot $BrollScripts
```

For an all-skipped no-op, only the summary and final delivery are required; contact sheets,
boundary reels, and stills do not exist.

For selected B-roll, completion is blocked until the completed visual-review receipt,
final-pixel checks, and registration validation pass. Successful render or machine-verification
commands alone are not a self-check.
