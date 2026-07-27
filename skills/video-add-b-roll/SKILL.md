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
$PexelsRecord = "$ProjectRoot/work/b-roll/pexels-12345-acquired.json"
$PexelsJson = & python "$BrollScripts/pexels.py" download `
  "$ProjectRoot/work/b-roll/pexels-candidate.json" `
  "$ProjectRoot/work/cache/b-roll/candidates/pexels-12345.mp4"
if ($LASTEXITCODE -ne 0) { throw 'Pexels acquisition failed.' }
[IO.File]::WriteAllText($PexelsRecord, ($PexelsJson -join "`n") + "`n", [Text.UTF8Encoding]::new($false))
```

`$PexelsRecord` is the authoritative acquisition record: it contains the final redirected
URL, `path`, protocol-relative `cache_path`, SHA-256, bytes, probe, and synchronized
provenance. Replace the shot's search-result candidate with this complete record, then
revalidate the plan. Never rerun a successfully published download using the unhashed search
record; only the acquired record binds the published bytes.

The downloader owns `.part` recovery. After a transient HTTP or network failure, rerun the
exact `pexels.py download` command with the same candidate and destination and let it validate
Range responses, redirects/hosts, size, media, and hash before atomic publication or cleanup.
Never manually promote, rename, or delete a `.part` file. On downloader-declared validation
failure, honestly skip the shot; do not substitute a generic clip or publish partial bytes.

External generation follows the local import command with `source_type:
"external-generated"` and complete truthful generation provenance. This is import only, not
authorization to call a generation service.

### 4. Publish And Complete Exact-Candidate Review

Set `input_hashes.review_video_sha256` to the actual current review video's SHA-256, revalidate,
then publish the immutable local review:

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

Apply the review checks in `reference/broll-rules.md`. The export must decide every shot
exactly once. The browser downloads `b-roll-review-<UUID>.json`; after exporting, bind the
actual operator-chosen download location rather than assuming it is in the review directory:

```powershell
$ReviewExport = (Resolve-Path -LiteralPath "<browser-download-directory>/b-roll-review-$($ReviewPublication.review_id).json").Path
```

For human mode, present the page and stop. Apply only the JSON the user explicitly exports;
it must contain `explicit_user_action: true`. For Agent mode, proceed only when the user has
explicitly delegated the decision or requested autonomous completion. Inspect the same exact
assets, export truthful decisions under `mode: "agent"`, name the real Agent actor, and give
a non-empty decision rationale. Never create a human-mode receipt from silence or inference.

Apply the exported review and durably bind the interaction receipt:

```powershell
python -c "import sys; from pathlib import Path; root=Path(sys.argv[1]); sys.path.insert(0,sys.argv[2]); import broll_plan,projectlib; path=root/'work/b-roll/broll-plan.json'; plan=projectlib.load_json(path); review=projectlib.load_json(sys.argv[3]); updated=broll_plan.apply_review(plan,review,mode=sys.argv[4],actor=sys.argv[5],rationale=sys.argv[6],interaction_path=root/'work/b-roll/broll-interaction.json'); projectlib.write_json(path,updated)" $ProjectRoot $BrollScripts $ReviewExport agent Codex "Selected literal process footage; skipped candidates that did not match the claim."
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
`grade_match`. Every result must be `true`. Use `mode: "human"` and
`explicit_user_action: true` only after an explicit user action; otherwise use delegated
`mode: "agent"`. Never infer or fabricate a human pass.

Complete the visual review before final registration. This writes the durable receipt and
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
