# Video Add B-Roll Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested `video-add-b-roll` skill that plans, acquires, reviews, normalizes,
verifies, and compiles selective local/Pexels B-roll under Project Protocol V1.

**Architecture:** Agent-authored editorial JSON remains the edit. Five small Python scripts
perform deterministic validation, acquisition, local review publication, normalization, and
verification. Approved shots reuse existing video `overlay` contributions; a focused
`projectlib.py` validator ensures the durable plan and declared overlays agree.

**Tech Stack:** Python standard library, ffmpeg/ffprobe, Pillow, unittest, local HTML/CSS/JS.

---

## File Map

- Create `skills/video-add-b-roll/scripts/broll_plan.py`: plan validation, hashes, review
  application, dependency discovery, and operation registration.
- Create `skills/video-add-b-roll/scripts/pexels.py`: direct Pexels search and safe,
  resumable candidate download.
- Create `skills/video-add-b-roll/scripts/build_review_page.py`: immutable local review page
  and source-frame publication.
- Create `skills/video-add-b-roll/scripts/normalize_broll.py`: video/still normalization and
  optional selected-grade application.
- Create `skills/video-add-b-roll/scripts/check_broll.py`: media/hash/receipt validation and
  visual review artifacts.
- Create `skills/video-add-b-roll/tests/test_broll.py`: one focused unittest module covering
  all nontrivial behavior.
- Create `skills/video-add-b-roll/assets/broll-review.html`: accessible local candidate board.
- Create `skills/video-add-b-roll/reference/broll-rules.md`: concise editorial and provenance
  rules.
- Create `skills/video-add-b-roll/examples/example-broll-plan.json`: complete valid example.
- Create `skills/video-add-b-roll/SKILL.md`: agent workflow and protocol contract.
- Modify `skills/video-understand/scripts/projectlib.py`: compile-time B-roll plan/render
  consistency check only.
- Modify `skills/video-understand/scripts/check_protocol_extensions.py`: one shared runtime
  regression fixture.
- Create runtime artifacts only below `TEST/28-sol/`; never stage them.

## Task 1: Plan, Receipt, and Operation Contract

**Files:**
- Create: `skills/video-add-b-roll/tests/test_broll.py`
- Create: `skills/video-add-b-roll/scripts/broll_plan.py`

- [ ] **Step 1: Write failing structural and receipt tests**

Add `unittest` cases with temporary project roots for these exact behaviors:

```text
PlanContractTests.test_rejects_overlap_out_of_bounds_and_unmapped_evidence
PlanContractTests.test_review_binds_subject_manifest_and_selected_hashes
PlanContractTests.test_rejects_fake_human_and_blank_agent_rationale
PlanContractTests.test_stale_transcript_timeline_and_dependency_revision_fail
PlanContractTests.test_registers_verified_overlays_after_grade_before_cards
PlanContractTests.test_zero_selected_shots_leaves_sequence_without_broll
```

Use a two-clip timeline, a word-level transcript with source/program evidence, local
candidate bytes, and a project containing verified `understanding`, `cut`, `color-grade`,
`content-cards`, and `captions` operations. Assert exact error substrings and operation
ordering.

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m unittest skills/video-add-b-roll/tests/test_broll.py -v
```

Expected: import failure for missing `broll_plan`.

- [ ] **Step 3: Implement the minimum contract**

Expose these functions and no classes:

```python
errors = broll_plan.validate_plan(
    plan, timeline, transcript, project=project, project_root=root, verify_files=True
)
self.assertEqual([], errors)

approved = broll_plan.apply_review(
    plan, review, mode="agent", actor="Codex",
    rationale="Literal factory footage supports the manufacturing claim."
)
self.assertEqual("approved", approved["review"]["status"])
self.assertEqual(
    broll_plan.canonical_sha256(broll_plan.review_subject(approved)),
    approved["review"]["plan_sha256"],
)

registered = broll_plan.register_operation(project, approved)
self.assertEqual(
    ["cut", "color-grade", "b-roll", "content-cards", "captions"],
    registered["sequences"]["main"]["operations"],
)
```

Validation enforces schema 1, program time, matching timeline ID/duration, current
dependencies/revisions/input hashes, unique IDs, ordered non-overlapping half-open ranges,
mapped word evidence, two or three non-empty queries, complete candidate provenance,
selection membership, honest decision mode, receipt hashes, and valid lifecycle.

`review_subject()` omits the mutable `review`, `normalized`, and `verification` fields so its
hash remains stable after deterministic processing. `apply_review()` requires every shot in
the export exactly once, permits only `human|agent`, requires non-empty actor/rationale, and
requires `explicit_user_action: true` for human mode. It writes selected or skipped states
and a receipt binding the review UUID, subject, candidate manifest, and selected hashes.

`register_operation()` removes any old B-roll operation first. With no selected shots it
leaves the sequence unchanged. Otherwise it requires all selected shots verified and emits
one existing `overlay` contribution per shot, with `changes_video_pixels: true`, no timeline,
geometry, or audio changes, and insertion after grade/cut but before cards/captions.

- [ ] **Step 4: Run GREEN and refactor**

Run the same unittest command. Expected: all Task 1 tests pass. Keep JSON writes delegated
to `projectlib.write_json`; use `copy.deepcopy`, `hashlib`, `json`, and `Path` only.

- [ ] **Step 5: Commit Task 1**

```powershell
git add skills/video-add-b-roll/tests/test_broll.py skills/video-add-b-roll/scripts/broll_plan.py
git commit -m "feat(b-roll): add plan and review contract"
```

## Task 2: Safe Local and Pexels Acquisition

**Files:**
- Modify: `skills/video-add-b-roll/tests/test_broll.py`
- Create: `skills/video-add-b-roll/scripts/pexels.py`

- [ ] **Step 1: Write failing acquisition tests**

Add fake response/opener objects without network access:

```text
AcquisitionTests.test_requires_environment_key_and_https_pexels_hosts
AcquisitionTests.test_parses_and_deduplicates_landscape_video_candidates
AcquisitionTests.test_download_retries_transient_failure_and_atomically_publishes
AcquisitionTests.test_download_rejects_redirect_host_oversize_and_invalid_media
AcquisitionTests.test_existing_matching_hash_resumes_without_network
AcquisitionTests.test_import_local_freezes_bytes_and_provenance_in_cache
```

Patch `probe_media` in download tests only; keep URL, streaming, byte-limit, `.part`, hash,
and atomic rename logic real. Assert no final file survives rejected content.

- [ ] **Step 2: Run RED**

Expected: import failure for missing `pexels`.

- [ ] **Step 3: Implement direct Pexels and local import helpers**

Expose:

```python
self.assertEqual(
    "https://api.pexels.com/videos/search",
    pexels.validate_url(
        "https://api.pexels.com/videos/search", {"api.pexels.com"}
    ),
)
candidates = pexels.search_videos(
    "electric vehicle factory", api_key="test-key", opener=fake_opener
)
self.assertEqual([1234], [item["provider_id"] for item in candidates])
downloaded = pexels.download_candidate(
    candidates[0], root / "work/cache/b-roll/candidates/pexels-1234.mp4",
    opener=fake_opener, max_bytes=1024,
)
self.assertTrue(downloaded["path"].is_file())
self.assertFalse(downloaded["path"].with_suffix(".mp4.part").exists())
```

Use `urllib.request`, the default verified TLS context, `urllib.parse`, `time`, and
`os.replace`. Read `PEXELS_API_KEY` only from the function argument or environment; never
serialize it. Permit API host `api.pexels.com` and media hosts returned by the Pexels API
only after HTTPS validation. A redirect response must still resolve to an allowed host.

Stream bounded chunks to a basename-only path under the caller-provided candidates
directory. Use `destination.with_suffix(destination.suffix + ".part")`, retry only transient
HTTP/URL errors, verify video stream/duration and one decoded frame, calculate SHA-256, then
publish atomically. Existing destination bytes are reusable only when the expected hash
matches. Local imports use the same cache containment, media probe, SHA-256, and atomic
publication.

- [ ] **Step 4: Run GREEN**

Run the full B-roll unittest module. Expected: Task 1 and 2 tests pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add skills/video-add-b-roll/scripts/pexels.py skills/video-add-b-roll/tests/test_broll.py
git commit -m "feat(b-roll): add safe candidate acquisition"
```

## Task 3: Review, Normalize, and Verify

**Files:**
- Modify: `skills/video-add-b-roll/tests/test_broll.py`
- Create: `skills/video-add-b-roll/assets/broll-review.html`
- Create: `skills/video-add-b-roll/scripts/build_review_page.py`
- Create: `skills/video-add-b-roll/scripts/normalize_broll.py`
- Create: `skills/video-add-b-roll/scripts/check_broll.py`

- [ ] **Step 1: Write failing review/media tests**

Add cases:

```text
ReviewPageTests.test_publishes_immutable_uuid_page_local_assets_and_alias
ReviewPageTests.test_template_has_native_controls_and_no_remote_urls
NormalizeAndCheckTests.test_normalizes_video_to_dimensions_fps_duration_and_no_audio
NormalizeAndCheckTests.test_explicit_still_uses_ken_burns_but_no_implicit_fallback
NormalizeAndCheckTests.test_active_lut_is_applied_by_basename_from_lut_cwd
NormalizeAndCheckTests.test_checker_rejects_bad_hash_audio_short_duration_and_stale_receipt
NormalizeAndCheckTests.test_checker_writes_three_stills_contact_sheet_boundary_reel_and_summary
```

Generate tiny color/video/image fixtures with ffmpeg/Pillow under `TemporaryDirectory`.
Mock only subprocess command capture for the Windows LUT basename assertion; use real
ffmpeg/ffprobe for the media contract tests.

- [ ] **Step 2: Run RED**

Expected: imports for the three missing scripts fail.

- [ ] **Step 3: Implement the local review builder and template**

The builder validates the plan before publication, generates a UUID when not supplied,
extracts one source frame per moment, copies no remote assets, base64-embeds the JSON payload,
publishes `b-roll-review-<UUID>.html` without overwriting an existing immutable page, and
updates `b-roll-review.html` atomically as a convenience alias.

The template uses native radio inputs for one candidate or skip, a text rationale, visible
provenance, video/image previews, keyboard-accessible labels, and a JSON download button.
It contains no `http://`, `https://`, external script, remote font, or inline SVG.

- [ ] **Step 4: Implement normalization**

Expose:

```python
output = root / "work/cache/b-roll/normalized/broll-001.mp4"
record = normalize_broll.normalize_shot(
    candidate, shot, timeline, output, lut=selected_lut
)
self.assertEqual(output, record["path"])
self.assertEqual({"num": 30000, "den": 1001}, record["probe"]["fps"])
self.assertFalse(record["probe"]["has_audio"])

updated = normalize_broll.normalize_plan(
    root / "work/b-roll/broll-plan.json",
    root / "work/timeline.json",
    root,
    lut=selected_lut,
)
self.assertEqual("normalized", updated["shots"][0]["status"])
```

For video, use explicit source trim, scale/crop, SAR 1, rational FPS, PTS reset, H.264,
`yuv420p`, exact duration, and `-an -sn -dn`. For images, require an explicit `ken_burns`
object and generate deterministic `zoompan`; never infer it. Stage as `.part.mp4`, probe and
decode before `os.replace`, then store path/hash/probe and set `normalized` lifecycle.

When a selected LUT exists, run ffmpeg with `cwd=lut.parent` and use only `lut.name` in the
filter. Store the grade plan and LUT hashes in the normalized record.

- [ ] **Step 5: Implement verification artifacts**

`check_broll.py` reruns `broll_plan.validate_plan()` with `verify_files=True`, probes each
normalized file, checks frame tolerance/dimensions/FPS/no audio/hash, and decodes first,
middle, and last frames. Pillow assembles a labeled contact sheet. ffmpeg extracts short
windows around B-roll boundaries from the final delivery and concatenates a silent boundary
reel. Write an evidence-rich Markdown summary atomically and update shot status to
`verified` only after all checks pass.

- [ ] **Step 6: Run GREEN and commit**

Run all B-roll tests and `git diff --check`, then:

```powershell
git add skills/video-add-b-roll/assets skills/video-add-b-roll/scripts skills/video-add-b-roll/tests
git commit -m "feat(b-roll): review normalize and verify shots"
```

## Task 4: Shared Compiler Gate and Skill Playbook

**Files:**
- Modify: `skills/video-understand/scripts/projectlib.py`
- Modify: `skills/video-understand/scripts/check_protocol_extensions.py`
- Modify: `skills/video-add-b-roll/tests/test_broll.py`
- Create: `skills/video-add-b-roll/SKILL.md`
- Create: `skills/video-add-b-roll/reference/broll-rules.md`
- Create: `skills/video-add-b-roll/examples/example-broll-plan.json`

- [ ] **Step 1: Write the failing compiler regression**

Extend the shared protocol fixture with an approved B-roll operation and two overlay
contributions. Assert compilation succeeds only when:

```python
assert compiled[0]["operation"] == "b-roll"
assert compiled[0]["start_s"] == plan["shots"][0]["program_range"]["start_s"]
assert compiled[0]["duration_s"] == range_duration
```

Mutate one contribution asset/start/duration, review status, shot lifecycle, and timeline ID
in turn; each must raise a specific B-roll plan mismatch error. Run the shared check and
observe RED because no skill-specific compiler validator exists.

- [ ] **Step 2: Add the focused compiler validator**

Add `_validate_broll_plan(plan, operation, contributions, timeline, errors)` to
`projectlib.py` and call it only for `operation.skill == "video-add-b-roll"` before paths are
compiled. It validates plan approval, timeline/program duration, dependency/based-on parity,
verified non-overlapping selected shots, normalized paths, and exact overlay asset/start/
duration correspondence. It does not duplicate ffprobe or semantic checks.

- [ ] **Step 3: Run shared GREEN**

```powershell
python skills/video-understand/scripts/check_protocol_extensions.py
python skills/video-cut/scripts/check_project_protocol.py
python skills/video-add-captions/scripts/check_project_protocol.py
python -m unittest skills/video-add-b-roll/tests/test_broll.py -v
```

Expected: all commands exit 0. Record the unrelated shorts baseline separately; do not edit
shorts code.

- [ ] **Step 4: Write the minimal skill and references**

`SKILL.md` frontmatter is:

```yaml
---
name: video-add-b-roll
description: Use when a talking-head, interview, documentary, or explanatory video needs selective transcript-timed visual cutaways from local media or Pexels.
---
```

Keep it below 500 lines. It must require reading `reference/broll-rules.md`, use only the
provided scripts for acquisition/validation, spell out human versus delegated Agent review,
forbid raw download commands/random fallback/fake human receipts, explain active cut/grade
dependencies, and finish with build-render-plan, render, and visual self-check commands.

The reference defines selective editorial rules, query construction, provenance minimums,
still-image opt-in, review quality checks, and skip behavior. The example is structurally
complete with one verified local video shot and one skipped shot, using obviously fake
hashes and paths labeled as examples.

- [ ] **Step 5: Run skill GREEN evaluation**

Give a fresh subagent the same primary and interrupted-download scenarios used for the
baseline, now explicitly requiring it to read `skills/video-add-b-roll/SKILL.md`. It must use
the scripts, set `changes_video_pixels: true`, pre-apply active grade, preserve `.part` resume,
produce honest receipts, and skip weak candidates. Close any discovered instruction gap and
rerun once.

- [ ] **Step 6: Commit Task 4**

```powershell
git add skills/video-add-b-roll skills/video-understand/scripts/projectlib.py skills/video-understand/scripts/check_protocol_extensions.py
git commit -m "feat(b-roll): integrate Project Protocol V1 skill"
```

## Task 5: Supplied Video End-to-End

**Files:**
- Runtime only: `TEST/28-sol/input/`, `TEST/28-sol/work/`, `TEST/28-sol/review/`,
  `TEST/28-sol/final/`

- [ ] **Step 1: Initialize without moving the supplied source**

Use a staging project below `TEST/28-sol/`, initialize from `Musk_3min.mp4`, and ensure all
transcript/model/cache/review/final artifacts remain under `TEST/28-sol/`. Never write to the
repository root `work/` for this run.

- [ ] **Step 2: Build verified understanding and identity timeline**

Probe, extract mono audio, transcribe with the locally available faster-whisper cache under
the project, analyze, author evidence-backed understanding, validate, and create the named
understanding summary/SRT/contact sheet. Inspect the contact sheet and transcript.

- [ ] **Step 3: Choose honest local B-roll candidates**

Because `PEXELS_API_KEY` is absent, exercise Pexels missing-key behavior but do not bypass it.
Inspect the supplied program for semantically useful non-talking-head segments. Freeze only
genuinely relevant local segments as candidates. If none exist, create an explicit external
local test asset under the same project using a simple Pillow image that is clearly labeled
as synthetic test media, record that provenance, and select it only for a transcript moment
it literally represents. Use an explicit Ken Burns decision for an image.

- [ ] **Step 4: Review, normalize, verify, and register**

Build the immutable local review, make an Agent decision with a non-empty semantic/visual
rationale, apply it, normalize, inspect candidates and first/middle/last frames, then verify
and register the operation. Produce the contact sheet, boundary reel, and summary.

- [ ] **Step 5: Compile and render once**

Validate project/timeline/plan, compile `work/render/render-plan.json`, inspect exact overlay
entries, render `final/final-video.mp4`, and run the existing source-time edit comparison.

- [ ] **Step 6: Verify final pixels and media contract**

Use ffprobe and hashes to confirm final duration within one frame of 167.973 seconds,
1280x720, 30000/1001 video, audio present, and selected B-roll visible only in its approved
half-open ranges. Inspect the final boundary reel/contact sheet and decode first/middle/last
delivery frames. Keep all artifacts under `TEST/28-sol/`.

## Task 6: Completion Audit

**Files:** all changed files and runtime evidence.

- [ ] **Step 1: Run fresh verification**

Run B-roll unittests, shared protocol checks, cut/captions regressions, Python compile checks,
`git diff --check`, and the real project validators/compiler. Record exact pass counts and
the known unrelated shorts baseline errors.

- [ ] **Step 2: Audit every approved requirement**

Check local+Pexels, external generated import, selective density, human/Agent modes, explicit
Ken Burns, single direct provider, no random fallback, provenance, receipts, staleness,
resume, no-op, grade pre-application, overlay ordering, all review artifacts, and TEST-only
runtime containment.

- [ ] **Step 3: Final code review and implementation commit**

Run spec-compliance then code-quality review. Fix and re-verify all findings. Stage no
`TEST/` or cache artifacts. If review fixes remain, commit them as:

```powershell
git commit -m "fix(b-roll): address verification findings"
```
