---
name: video-add-b-roll
description: Use when a talking-head, interview, documentary, or explanatory video needs selective transcript-timed visual cutaways from local media or Pexels.
---

# Video Add B-Roll

Add a small number of evidence-backed visual cutaways to an understood Project Protocol V1
sequence. Read [broll-rules.md](reference/broll-rules.md) before planning or acquiring any
media. Use [example-broll-plan.json](examples/example-broll-plan.json) as the plan-shape
reference.

## Non-Negotiable Contract

- Use the provided scripts for every acquisition, media validation, normalization, receipt
  application, and verification step. Do not use `curl`, `Invoke-WebRequest`, browser-save,
  or another raw download path.
- V1 accepts project-local media and direct Pexels results through the single
  `scripts/pexels.py` module. Do not add a provider interface, factory, broker, or substitute
  another stock source.
- Never use random, merely topical, or still-image fallback media. A missing or weak result
  becomes an honest `skipped` shot.
- Do not call native paid image or video generation APIs. Externally generated media is
  eligible only after truthful local import with provider/model, prompt or job ID, creator,
  license, retrieval time, and original path provenance.
- Never fabricate a human response or label an Agent decision as human. Human and explicitly
  delegated Agent review are separate receipt modes.
- Keep density `selective`. B-roll must clarify meaning, provide evidence, or hide a necessary
  edit. It is not a coverage quota.
- A still requires an explicit review choice with `ken_burns.direction` set to `zoom-in`,
  `pan-left`, or `pan-right`. Never silently replace a failed video search with a still.

## Requirements And Inputs

Require Python, `ffmpeg`, `ffprobe`, and Pillow. For Pexels, read `PEXELS_API_KEY` from the
environment; never place it in a command argument, plan, URL, log, or review artifact.

Run from the repository root and resolve the separate project root:

```powershell
$RepoRoot = (Resolve-Path '.').Path
$ProjectRoot = (Resolve-Path 'path/to/video-project').Path
$BrollScripts = Join-Path $RepoRoot 'skills/video-add-b-roll/scripts'
```

Consume these canonical inputs instead of re-transcribing or re-analyzing:

- `work/project.json`
- `work/timeline.json`
- `work/understand/transcript.json`
- `work/understand/understanding.json`
- a current program-time review video whose pixels include active cut and color-grade work

The operation always depends on `understanding`, plus `cut` and `color-grade` when those
operations are active on the target sequence. Copy their current positive integer revisions
to `based_on`. When color grade is active, record both the grade-plan and selected-LUT hashes;
normalization must receive that exact selected LUT and pre-apply it to every selected B-roll
shot.

The canonical sequence order is:

```text
cut -> color-grade -> b-roll -> content-cards -> captions
```

The registered operation must have `changes_video_pixels: true`, add the `b-roll` track, and
leave timeline, geometry, and audio unchanged. `broll_plan.register_operation()` writes this
contract; do not hand-build the operation.

## Durable And Disposable Files

```text
work/b-roll/broll-plan.json                         # durable domain plan
work/b-roll/broll-interaction.json                  # durable applied receipt
work/cache/b-roll/candidates/                       # frozen acquired media
work/cache/b-roll/normalized/                       # reproducible silent overlays
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

### 2. Author A Selective Plan

Hand-author `work/b-roll/broll-plan.json`; scripts perform precision, not editorial judgment.
For each proposed shot:

- choose a positive, half-open, non-overlapping program range in chronological order;
- map it through `work/timeline.json` into exact `source_ranges`;
- preserve at least one exact mapped transcript word with source/program ranges and clip ID;
- state a concrete `editorial_reason` and `visual_intent`;
- write two or three literal English queries containing subject, action, and useful setting;
- begin at `planned`, move to `candidates_ready` after acquisition, or use `skipped` when no
  relevant candidate exists.

Keep `brief.density` equal to `selective`. Do not pad the plan to meet a count. If no moment
earns B-roll, an approved all-skipped plan is a valid no-op.

Validate the draft after every material edit:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; plan=projectlib.load_json(root/'work/b-roll/broll-plan.json'); timeline=projectlib.load_json(root/'work/timeline.json'); transcript=projectlib.load_json(root/'work/understand/transcript.json'); project=projectlib.load_json(root/'work/project.json'); errors=broll_plan.validate_plan(plan,timeline,transcript,project=project,project_root=root,verify_files=True); print('\n'.join(errors) if errors else 'B-roll plan valid'); raise SystemExit(bool(errors))" $ProjectRoot $BrollScripts
```

### 3. Acquire And Freeze Candidates

For local video, write a provenance JSON object containing `source_type: "local"`, creator,
license, and a timezone-aware retrieval time, then import it:

```powershell
python "$BrollScripts/pexels.py" import-local `
  "$ProjectRoot/input/example-owned-footage.mp4" `
  "$ProjectRoot/work/cache/b-roll/candidates/example-owned-footage.mp4" `
  "$ProjectRoot/work/b-roll/example-local-provenance.json"
```

Copy the returned acquisition record into the shot candidate, use a protocol-relative
`cache_path` such as `cache/b-roll/candidates/example-owned-footage.mp4`, and retain its real
probe, byte count, SHA-256, and provenance. The current local importer validates video; do
not bypass it to force unsupported media into the plan.

For Pexels, search each of the shot's two or three literal queries through the one direct
module:

```powershell
python "$BrollScripts/pexels.py" search "precision parts factory floor" `
  --orientation landscape --per-page 10
```

Choose only a semantically accurate result. Save that single returned candidate object as
JSON, add its intended protocol-relative `cache_path`, then use the provided downloader:

```powershell
python "$BrollScripts/pexels.py" download `
  "$ProjectRoot/work/b-roll/pexels-candidate.json" `
  "$ProjectRoot/work/cache/b-roll/candidates/pexels-12345.mp4"
```

The downloader constrains hosts and size, validates redirects, probes and decodes media,
hashes it, and publishes atomically. If a transient failure leaves `destination.part`, rerun
the same `pexels.py download` command with the same frozen candidate and destination only
when its configured byte bound and frozen response metadata still make recovery safe. Never
manually promote, rename, or delete a `.part` file. If the partial already exceeds the bound,
the response metadata is stale, or the provided downloader cannot validate the redirect,
range, media, and hash, preserve the partial and honestly skip the shot. Do not substitute a
generic local clip or publish unvalidated bytes.

External generation follows the local import command with `source_type:
"external-generated"` and complete truthful generation provenance. This is import only, not
authorization to call a generation service.

### 4. Publish And Complete Exact-Candidate Review

Set `input_hashes.review_video_sha256` to the actual current review video's SHA-256, revalidate,
then publish the immutable local review:

```powershell
python "$BrollScripts/build_review_page.py" `
  "$ProjectRoot/work/b-roll/broll-plan.json" `
  "$ProjectRoot/review/03-b-roll" `
  --video "$ProjectRoot/final/pre-b-roll-review.mp4" `
  --timeline "$ProjectRoot/work/timeline.json" `
  --transcript "$ProjectRoot/work/understand/transcript.json" `
  --project-root "$ProjectRoot"

Start-Process (Resolve-Path "$ProjectRoot/review/03-b-roll/b-roll-review.html")
```

Review semantic fit, trim boundaries, framing, quality, license/provenance, logos, visible
text, and grade compatibility. Review export must decide every shot exactly once.

For human mode, present the page and stop. Apply only the JSON the user explicitly exports;
it must contain `explicit_user_action: true`. For Agent mode, proceed only when the user has
explicitly delegated the decision or requested autonomous completion. Inspect the same exact
assets, export truthful decisions under `mode: "agent"`, name the real Agent actor, and give
a non-empty decision rationale. Never create a human-mode receipt from silence or inference.

Apply the exported review and durably bind the interaction receipt:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; path=root/'work/b-roll/broll-plan.json'; plan=projectlib.load_json(path); review=projectlib.load_json(sys.argv[3]); updated=broll_plan.apply_review(plan,review,mode=sys.argv[4],actor=sys.argv[5],rationale=sys.argv[6],interaction_path=root/'work/b-roll/broll-interaction.json'); projectlib.write_json(path,updated)" $ProjectRoot $BrollScripts "$ProjectRoot/review/03-b-roll/b-roll-review-export.json" agent Codex "Selected literal process footage; skipped candidates that did not match the claim."
```

Use `human` and the actual human actor only after explicit user export. The command rationale
must exactly match the exported rationale.

### 5. Normalize Approved Selections

With active color grade, pass the exact selected `.cube` path from the grade plan:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import normalize_broll; normalize_broll.normalize_plan(root/'work/b-roll/broll-plan.json',root/'work/timeline.json',root,lut=Path(sys.argv[3]).resolve())" $ProjectRoot $BrollScripts "$ProjectRoot/final/selected-color-look.cube"
```

Without active color grade, call the same API with `lut=None`. Never omit the LUT when color
grade is active and never apply an unselected look. The normalizer produces silent H.264
overlays at timeline dimensions and exact rational FPS, preserves aspect ratio, enforces the
selected trim or Ken Burns direction, and publishes each validated result atomically.

Rerun `normalize_plan()` after interruption. It validates and preserves completed normalized
shots before continuing; do not hand-promote `.part.mp4` or `.part.json` files.

### 6. Verify, Inspect, And Register

Run the verifier against the same current program-time review video:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import check_broll; check_broll.verify_plan(root/'work/b-roll/broll-plan.json',root/'work/timeline.json',root,Path(sys.argv[3]))" $ProjectRoot $BrollScripts "$ProjectRoot/final/pre-b-roll-review.mp4"
```

It revalidates hashes and receipts, probes and decodes normalized clips, marks selected shots
`verified`, and publishes first/middle/last stills, a contact sheet, a short boundary reel,
and the summary. Inspect all of them. Check literal semantic match, entry/exit timing, speaker
context, crop, logos, readable/unwanted text, visible jumps, and grade match. If any check
fails, fix the plan or selection and repeat review, normalization, and verification. Do not
edit hash-bound verification artifacts in place.

After visual inspection passes, register from the verified plan. An all-skipped plan removes
any stale B-roll operation and leaves no empty active operation:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; project_path=root/'work/project.json'; project=projectlib.load_json(project_path); plan=projectlib.load_json(root/'work/b-roll/broll-plan.json'); projectlib.write_json(project_path,broll_plan.register_operation(project,plan))" $ProjectRoot $BrollScripts
```

### 7. Build Delivery And Perform Final Self-Check

Compile approved active operations and render delivery once:

```powershell
python "$RepoRoot/skills/video-understand/scripts/build_render_plan.py" $ProjectRoot
python "$RepoRoot/skills/video-understand/scripts/render_project.py" `
  "$ProjectRoot/work/render/render-plan.json"
```

Generate the required source-time comparison from actual final pixels, not an intermediate:

```powershell
python "$RepoRoot/skills/video-edit-compare/scripts/make_compare.py" `
  "$ProjectRoot/work/timeline.json" `
  "$ProjectRoot/input/original-video.mp4" `
  "$ProjectRoot/final/final-video.mp4" `
  "$ProjectRoot/review/04-edit-compare/original-vs-final-source-time.mp4"
```

Open and inspect the final delivery, source-time comparison, contact sheet, boundary reel,
and representative first/middle/last stills before declaring completion:

```powershell
Start-Process "$ProjectRoot/final/final-video.mp4"
Start-Process "$ProjectRoot/review/04-edit-compare/original-vs-final-source-time.mp4"
Start-Process "$ProjectRoot/review/03-b-roll/contact-sheet.jpg"
Start-Process "$ProjectRoot/review/03-b-roll/boundary-reel.mp4"
Get-Content "$ProjectRoot/review/03-b-roll/b-roll-summary.md"
```

Completion is blocked until these final-pixel and visual checks pass. Successful commands or
machine validation alone are not a self-check.
