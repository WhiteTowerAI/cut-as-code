# Captions and Shorts Project Protocol V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `video-add-captions` and `video-to-shorts` consume the shared evidence/timeline contracts, participate honestly in the project DAG, emit review/final artifacts in protocol locations, and pass the two specified real-video workflows.

**Architecture:** Add one source-to-program transcript mapper and one explicit image-sequence overlay input to the existing shared protocol. Keep each target skill's proven domain logic, adding canonical plan modes and hash-bound delegated-agent review alongside compatibility behavior.

**Tech Stack:** Python 3 stdlib, Node.js ESM, PowerShell, ffmpeg/ffprobe, Pillow, faster-whisper, HyperFrames, Git.

---

## File Map

- Modify `skills/video-understand/scripts/projectlib.py`: shared transcript mapping and caption-plan/render validation.
- Modify `skills/video-understand/scripts/render_project.py`: explicit RGBA PNG-sequence overlay input.
- Create `skills/video-understand/scripts/check_protocol_extensions.py`: stdlib checks for mapping and render compilation.
- Modify `skills/video-add-captions/scripts/build_captions.py`: canonical program-time plan output while preserving cue-array mode.
- Modify `skills/video-add-captions/scripts/caption_interaction_state.mjs`: human/agent decision-mode validation.
- Modify `skills/video-add-captions/scripts/caption_interaction.mjs`: honest delegated selection/approval commands.
- Modify `skills/video-add-captions/scripts/generate_caption_project.mjs`: plan input, local GSAP, exact FPS, finalized renderer recipe.
- Create `skills/video-add-captions/scripts/build_caption_review.py`: mapped source-backed preview stills.
- Modify `skills/video-add-captions/scripts/composite_caption_overlay.ps1`: protocol-compatible H.264 compatibility output.
- Modify `skills/video-add-captions/scripts/check_caption_style_config.mjs` and `check_structure.ps1`: regression checks.
- Add `skills/video-add-captions/public/gsap.min.js`: frozen local GSAP runtime already required by generated compositions.
- Modify `skills/video-add-captions/SKILL.md` and caption references: canonical workflow and compatibility.
- Modify `skills/video-to-shorts/scripts/transcript_utils.py`: exact word excerpts and protocol path/time helpers.
- Modify `skills/video-to-shorts/scripts/prepare_transcript.py`: canonical transcriber and timeline mapping.
- Modify `skills/video-to-shorts/scripts/candidates.py`: program-time binding.
- Modify `skills/video-to-shorts/scripts/review_gate.py` and `interaction.py`: delegated candidate/vertical approval.
- Modify `skills/video-to-shorts/scripts/plan.py`: canonical V1 plan and user-facing outputs.
- Modify `skills/video-to-shorts/scripts/extract_shorts.py`: seeked-input extraction and final/review paths.
- Modify `skills/video-to-shorts/scripts/vertical_plan.py` and `render_vertical.py`: rational FPS and final/review paths.
- Create `skills/video-to-shorts/scripts/check_project_protocol.py`: stdlib contract checks.
- Modify `skills/video-to-shorts/SKILL.md`, `README.md`, and examples: canonical workflow plus compatibility.
- Modify `AGENTS.md` and `CLAUDE.md` only below their protected Git sections: add caption/short plan contracts.

### Task 1: Shared Program Transcript Mapping

**Files:**
- Create: `skills/video-understand/scripts/check_protocol_extensions.py`
- Modify: `skills/video-understand/scripts/projectlib.py`

- [ ] **Step 1: Write the failing mapping check**

Create a stdlib check using a two-clip fixture with a dropped gap and 2x speed:

```python
mapped = projectlib.map_transcript_to_timeline(transcript, timeline)
assert mapped["timebase"] == "program"
assert [w["word"].strip() for s in mapped["segments"] for w in s["words"]] == ["keep", "fast"]
assert mapped["segments"][1]["words"][0]["program_range"] == {
    "start_s": 2.0,
    "end_s": 2.25,
}
assert mapped["segments"][0]["clip_id"] != mapped["segments"][1]["clip_id"]
```

- [ ] **Step 2: Run it and verify RED**

Run: `python skills/video-understand/scripts/check_protocol_extensions.py`

Expected: failure because `map_transcript_to_timeline` does not exist.

- [ ] **Step 3: Implement the minimum shared mapper**

Add `map_transcript_to_timeline()` to `projectlib.py`. Validate the timeline, reject invalid word ranges, map only midpoint-retained words, preserve source ranges, split by clip, and emit program duration/timebase.

- [ ] **Step 4: Run it and verify GREEN**

Run: `python skills/video-understand/scripts/check_protocol_extensions.py`

Expected: mapping checks pass.

### Task 2: Image-Sequence Overlay Contribution

**Files:**
- Modify: `skills/video-understand/scripts/check_protocol_extensions.py`
- Modify: `skills/video-understand/scripts/projectlib.py`
- Modify: `skills/video-understand/scripts/render_project.py`

- [ ] **Step 1: Add failing compiler/command checks**

Use a temporary project containing `work/cache/captions/overlay-frames/frame_000001.png` and this contribution:

```python
{
    "kind": "overlay",
    "asset": "cache/captions/overlay-frames",
    "asset_type": "image-sequence",
    "pattern": "frame_%06d.png",
    "start_number": 1,
    "fps": {"num": 30000, "den": 1001},
}
```

Assert the compiled asset remains a directory and `build_command()` contains `-framerate 30000/1001`, `-start_number 1`, and the bounded frame pattern.

- [ ] **Step 2: Run and verify RED**

Run: `python skills/video-understand/scripts/check_protocol_extensions.py`

Expected: current compiler rejects the directory as a missing file.

- [ ] **Step 3: Implement explicit sequence validation/input**

Permit a directory only when `asset_type == "image-sequence"`; require a safe basename pattern, first frame, positive start number, and FPS equal to timeline FPS. Add ffmpeg sequence input arguments in `render_project.py`; leave file overlays unchanged.

- [ ] **Step 4: Run and verify GREEN**

Run: `python skills/video-understand/scripts/check_protocol_extensions.py`

Expected: all shared extension checks pass.

- [ ] **Step 5: Commit shared protocol support**

```powershell
git add skills/video-understand/scripts/projectlib.py `
  skills/video-understand/scripts/render_project.py `
  skills/video-understand/scripts/check_protocol_extensions.py
git commit -m "feat(protocol): support timed transcript and caption overlays"
```

### Task 3: Canonical Caption Cue Plan

**Files:**
- Modify: `skills/video-add-captions/scripts/build_captions.py`
- Create: `skills/video-add-captions/scripts/check_project_protocol.py`

- [ ] **Step 1: Write the failing canonical-plan check**

Call the desired API with a source transcript and timeline:

```python
plan = build_captions.build_plan(transcript, timeline, max_chars=20, max_lines=2, max_dur=6, gap=0.6)
assert plan["schema_version"] == 1
assert plan["timebase"] == "program"
assert plan["cues"][0]["program_range"]["start_s"] == plan["cues"][0]["start"]
assert plan["cues"][0]["words"][0]["source_range"]
```

- [ ] **Step 2: Run and verify RED**

Run: `python skills/video-add-captions/scripts/check_project_protocol.py`

Expected: `build_plan` is missing.

- [ ] **Step 3: Implement plan mode without breaking cue arrays**

Factor argument parsing through `argparse`, preserve `build()` and legacy positional output,
add `--timeline`/`--source-transcript`, break cues at `clip_id`, and write the V1 plan object
only when timeline mode is selected.

- [ ] **Step 4: Run and verify GREEN**

Run: `python skills/video-add-captions/scripts/check_project_protocol.py`

Expected: canonical and legacy cue checks pass.

### Task 4: Delegated Caption Review

**Files:**
- Modify: `skills/video-add-captions/scripts/caption_interaction_state.mjs`
- Modify: `skills/video-add-captions/scripts/caption_interaction.mjs`
- Modify: `skills/video-add-captions/scripts/check_caption_style_config.mjs`
- Modify: `skills/video-add-captions/scripts/check_project_protocol.py`

- [ ] **Step 1: Add failing agent-mode checks**

Create temporary source/caption files, then run:

```text
start --decision-mode agent --delegation-note "User delegated choices"
agent-select --choice clean --rationale "Readable conservative choice"
preview-ready ...
agent-confirm --rationale "Four mapped previews are legible"
status
```

Assert `phase=render_approved`, `decisionMode=agent`, no `user_response`, and human `select`/`confirm` are rejected for that receipt.

- [ ] **Step 2: Run and verify RED**

Run: `python skills/video-add-captions/scripts/check_project_protocol.py`

Expected: unknown agent-mode commands/options.

- [ ] **Step 3: Implement explicit human/agent command separation**

Add `decisionMode`, delegation note, selection/approval actor and rationale. Keep existing human phrases unchanged. Require non-empty rationale and preview evidence for agent approval.

- [ ] **Step 4: Run and verify GREEN**

Run both:

```powershell
node skills/video-add-captions/scripts/check_caption_style_config.mjs
python skills/video-add-captions/scripts/check_project_protocol.py
```

Expected: both checks pass.

### Task 5: Reproducible HyperFrames Caption Project

**Files:**
- Add: `skills/video-add-captions/public/gsap.min.js`
- Modify: `skills/video-add-captions/scripts/generate_caption_project.mjs`
- Create: `skills/video-add-captions/scripts/build_caption_review.py`
- Modify: `skills/video-add-captions/scripts/check_structure.ps1`
- Modify: `skills/video-add-captions/scripts/composite_caption_overlay.ps1`
- Modify: `skills/video-add-captions/scripts/check_project_protocol.py`

- [ ] **Step 1: Add failing generator/review checks**

Assert the generated HTML references `assets/gsap.min.js`, contains no `http://` or `https://`, uses the plan FPS/duration, and accepts `{ "cues": [...] }`. Assert mapped review timestamps call `program_to_source()` and output four named stills.

- [ ] **Step 2: Run and verify RED**

Run caption protocol and structure checks. Expected: remote GSAP and plan-input failures.

- [ ] **Step 3: Freeze and copy the existing GSAP dependency**

Acquire the exact GSAP runtime already used by the composition, store it under `public/`, and record version/origin/SHA-256 in the finalized plan. Do not add a package manifest.

- [ ] **Step 4: Implement generator plan mode**

Accept cue arrays or V1 plans, use exact plan FPS metadata, copy local assets, render transparent preview mode, and finalize style/review/renderer recipe only from a matching approved interaction receipt.

- [ ] **Step 5: Implement source-backed preview assembly**

Select early/middle/late cues and a no-caption point, map program to source time, combine transparent snapshots with real source frames via Pillow, and write a compact evidence JSON/summary.

- [ ] **Step 6: Keep standalone composite broadly playable**

Composite PNG/video overlays into H.264 `yuv420p` with source audio copied, preserving input duration/dimensions.

- [ ] **Step 7: Run checks and a tiny HyperFrames snapshot**

Run style, structure, protocol, `hyperframes lint`, `hyperframes check`, and selected transparent snapshots against a synthetic fixture.

- [ ] **Step 8: Update caption spec**

Rewrite `SKILL.md` project workflow first, then retain a concise standalone compatibility section. Keep plan schema, operation record, human/agent gates, review artifacts, rendering, and self-check in sync with scripts.

- [ ] **Step 9: Commit and push captions**

```powershell
git add skills/video-understand skills/video-add-captions
git commit -m "feat(captions): join the project delivery protocol"
git push origin feat/skill-improvements
```

### Task 6: Shorts Program-Time Input and Exact Excerpts

**Files:**
- Modify: `skills/video-to-shorts/scripts/transcript_utils.py`
- Modify: `skills/video-to-shorts/scripts/prepare_transcript.py`
- Modify: `skills/video-to-shorts/scripts/candidates.py`
- Create: `skills/video-to-shorts/scripts/check_project_protocol.py`

- [ ] **Step 1: Write failing mapping/excerpt checks**

Assert a candidate inside one long transcript segment receives only overlapping words, and
`prepare_transcript(... timeline=...)` returns `timebase=program`, timeline ID, and program
duration.

- [ ] **Step 2: Run and verify RED**

Run: `python skills/video-to-shorts/scripts/check_project_protocol.py`

Expected: segment-wide excerpt and missing timeline mode.

- [ ] **Step 3: Implement word-exact excerpts and shared mapping**

Use words when present, retain a segment-text compatibility fallback, import the shared
mapper for `--timeline`, and route fallback transcription directly to
`video-understand/scripts/transcribe.py` with project-local cache.

- [ ] **Step 4: Run and verify GREEN**

Run the shorts protocol check. Expected: mapping/excerpt checks pass.

### Task 7: Delegated Shorts Review

**Files:**
- Modify: `skills/video-to-shorts/scripts/review_gate.py`
- Modify: `skills/video-to-shorts/scripts/interaction.py`
- Modify: `skills/video-to-shorts/scripts/check_project_protocol.py`

- [ ] **Step 1: Add failing candidate/vertical agent checks**

Open an agent review, approve an explicit candidate/delivery mode with rationale, mutate an
artifact and assert validation fails; repeat for vertical preview approval.

- [ ] **Step 2: Run and verify RED**

Expected: agent review functions/commands do not exist.

- [ ] **Step 3: Implement decision-mode-specific gates**

Keep all current human paths. Add agent commands that require agent-mode review, explicit
delivery, non-empty rationale, and current artifact hashes; never populate `user_response`.

- [ ] **Step 4: Run and verify GREEN**

Run: `python skills/video-to-shorts/scripts/check_project_protocol.py`

Expected: human compatibility, agent approval, and stale-hash rejection pass.

### Task 8: Canonical Shorts Plan, Extraction, and Vertical Output

**Files:**
- Modify: `skills/video-to-shorts/scripts/plan.py`
- Modify: `skills/video-to-shorts/scripts/extract_shorts.py`
- Modify: `skills/video-to-shorts/scripts/vertical_plan.py`
- Modify: `skills/video-to-shorts/scripts/render_vertical.py`
- Modify: `skills/video-to-shorts/scripts/check_project_protocol.py`

- [ ] **Step 1: Add failing canonical plan checks**

Assert project mode emits integer schema V1, `program_range`, `source_ranges`, dependency
revisions, `../final/shorts/*.mp4` outputs, and `{num, den}` FPS.

- [ ] **Step 2: Add failing memory-safe extraction check**

Expose/build the ffmpeg command and assert N keep ranges create N seeked `-ss/-t/-i` inputs
rather than N trims from one decoded long input.

- [ ] **Step 3: Run and verify RED**

Expected: legacy plan/output/FPS shape and single-input filter graph.

- [ ] **Step 4: Implement project mode and compatibility normalization**

Emit canonical fields only with project inputs; accept both V1 and v2 on extraction. Resolve
work-relative output paths with `projectlib.resolve_project_path()` and write horizontal and
vertical deliverables under `final/shorts/`.

- [ ] **Step 5: Implement seeked-input extraction**

Reuse the rough-cut concat pattern, preserve exact source FPS, encode audio after cuts, and
write a short-relative transcript/report.

- [ ] **Step 6: Preserve rational FPS through vertical delivery**

Probe `{num, den}`, render with the rational string, validate duration/dimensions/audio, and
separate review previews from final outputs.

- [ ] **Step 7: Run and verify GREEN**

Run the shorts protocol check and a small synthetic ffmpeg integration.

- [ ] **Step 8: Update shorts spec/examples**

Put project workflow and output layout first in `SKILL.md`/`README.md`; retain candidate,
boundary, crop, and standalone compatibility detail. Update examples to match exact excerpt,
timebase, plan schema, output, and FPS fields.

- [ ] **Step 9: Commit and push shorts**

```powershell
git add skills/video-to-shorts
git commit -m "feat(shorts): align derivatives with project protocol"
git push origin feat/skill-improvements
```

### Task 9: Root Contract and Static Verification

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Hash protected Git sections before editing**

Record their exact byte hashes and edit only below the protected section.

- [ ] **Step 2: Add the two plan/output contracts**

Document `work/captions/captions-plan.json`, `work/shorts/shorts-plan.json`, derived-operation
semantics, agent mode, and image-sequence overlay form.

- [ ] **Step 3: Verify protected sections byte-for-byte**

Compare the stored hashes and fail if either changed.

- [ ] **Step 4: Run static checks**

```powershell
python -m py_compile skills/video-understand/scripts/*.py `
  skills/video-add-captions/scripts/*.py skills/video-to-shorts/scripts/*.py
python skills/video-understand/scripts/check_protocol_extensions.py
python skills/video-add-captions/scripts/check_project_protocol.py
node skills/video-add-captions/scripts/check_caption_style_config.mjs
powershell.exe -ExecutionPolicy Bypass -File skills/video-add-captions/scripts/check_structure.ps1
python skills/video-to-shorts/scripts/check_project_protocol.py
git diff --check
```

- [ ] **Step 5: Commit and push root contract**

```powershell
git add AGENTS.md CLAUDE.md
git commit -m "docs(agents): register captions and shorts plans"
git push origin feat/skill-improvements
```

### Task 10: Real-Media Run 20

**Files:**
- Generate only below: `TEST/20-codex-sol/`

- [ ] Initialize a fresh protocol project from the exact `Musk_3min.mp4`.
- [ ] Produce and validate media, transcript, analysis, understanding, SRT, summary, and contact sheet.
- [ ] Author a source-tiling rough-cut plan, inspect boundaries, build precision edit/timeline, and register exact revisions.
- [ ] Build program captions, choose/approve style in agent mode, inspect mapped stills, render the transparent overlay, and register it.
- [ ] Compile and render one shared final delivery.
- [ ] Re-transcribe/check boundaries, frame joins, caption presence/absence, A/V duration, and audio policy.
- [ ] Render and verify `original-vs-final-source-time`.
- [ ] Validate `project.json`, summaries, START-HERE, and all expected user-facing files.
- [ ] If any check fails, add the smallest reproducing check, fix, and rerun this workflow.

### Task 11: Real-Media Run 21

**Files:**
- Generate only below: `TEST/21-codex-sol/`

- [ ] Initialize and complete the same understanding evidence on an identity timeline.
- [ ] Build/approve captions in agent mode and render the main final once.
- [ ] Map the shared transcript to program time and generate only the specified visual context.
- [ ] Author, validate, and agent-approve complete text+visual candidates with `horizontal_and_vertical` delivery.
- [ ] Build the canonical plan and extract at least one horizontal short to `final/shorts/`.
- [ ] Inspect dense short frames, author a deterministic crop plan, render/inspect preview, agent-approve, and render final vertical output.
- [ ] Verify horizontal/vertical duration, dimensions, audio, transcript, and visible caption/crop safety.
- [ ] Register/verify the non-active derived shorts operation.
- [ ] Render and verify the main final source-time comparison.
- [ ] If any check fails, add the smallest reproducing check, fix, and rerun this workflow.

### Task 12: Final Verification and Delivery

- [ ] Re-run every static and skill-local check fresh.
- [ ] Re-run both project validators with media fingerprint checks.
- [ ] Probe every final/compare/short media output and inspect representative stills.
- [ ] Review the design and this plan line by line against actual files.
- [ ] Run `git diff --check`, inspect `git status`, and exclude `.vscode/`, `.worktree/`, and `TEST/` artifacts from commits.
- [ ] Commit any final fixes with a focused Conventional Commit and push.
- [ ] Mark the goal complete only after all evidence is fresh and no required work remains.
