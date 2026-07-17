# Captions and Shorts Project Protocol V1 Design

**Date:** 2026-07-17
**Status:** Approved for autonomous implementation by the user's explicit instruction to make all review decisions and complete both test runs without pausing
**Extends:** `2026-07-14-open-recut-project-protocol-v1-design.md`

## 1. Problem

`video-add-captions` and `video-to-shorts` predate the shared Open-Recut project
protocol. Both have useful domain logic, but neither currently composes with the project
contract:

- captions treat transcript time as finished-video time, so captions drift or disappear after
  a rough cut or linear varispeed;
- captions render and composite a separate final video instead of contributing to the shared
  delivery render;
- captions require simulated human phrases even when the user explicitly delegates decisions;
- shorts copy or regenerate transcripts instead of consuming `video-understand` evidence;
- shorts use an input-relative clock without binding it to `timeline.json`;
- shorts keep deliverables under `work/` and are absent from `project.json`;
- shorts discard exact rational FPS in the vertical plan;
- both skills keep review evidence and durable decisions in layouts that do not distinguish
  user-facing files, plans, and disposable cache assets.

The five reference skills already supply the needed architecture: shared evidence from
`video-understand`, chronological source/program mapping from `video-rough-cut`, delegated
agent selection from `video-color-grade`, reproducible overlay plans from
`video-add-content-cards`, and final-pixel verification from `video-edit-compare`.

## 2. Approaches Considered

### A. Keep both standalone and document ordering constraints

This is the smallest code change, but it cannot caption a cut/retimed sequence correctly,
cannot compile captions into the one delivery render, and leaves shorts outside revision
validation. Rejected.

### B. Rewrite both skills around a new orchestration framework

This could model derivatives and reviews uniformly, but it would duplicate the existing
project DAG and create a second shared manifest. It conflicts with Project Protocol V1 and
adds machinery unrelated to the two skills. Rejected.

### C. Add protocol adapters around the proven domain logic

Keep cue grouping, style resolution, candidate scoring, boundary refinement, extraction, and
vertical rendering. Add one shared transcript mapping primitive, canonical plan modes,
project operation records, agent-delegated review receipts, user-facing review/final outputs,
and one renderer input adapter for transparent PNG sequences. Recommended and selected.

## 3. Shared Decisions

1. `work/project.json` remains the only shared manifest.
2. `work/timeline.json` remains the only source-to-program mapping.
3. The canonical transcript remains `work/understand/transcript.json` in source time.
4. A shared deterministic adapter maps that transcript onto the active program clock. It is
   used by both captions and shorts; neither skill implements its own mapping.
5. Caption and short ranges are half-open and use explicit `source_range`, `program_range`,
   or plural `source_ranges` when a result spans more than one retained clip.
6. Human and delegated-agent decisions are both first-class. Agent mode is legal only when
   explicitly selected and records a non-empty rationale. It never fabricates a human reply.
7. Existing standalone commands and v2 shorts inputs remain supported during migration.
8. Captions are an active-sequence overlay operation. Shorts are a derived operation recorded
   in the DAG but not added to `sequences.main.operations`, because they must not alter the
   main delivery or its comparison.
9. Review numbering already reserves `00` through `04`; the new stable locations are
   `review/05-captions/` and `review/06-shorts/` to avoid renaming mature outputs.

## 4. Shared Program Transcript

`video-understand/scripts/projectlib.py` gains one reusable function:

```python
map_transcript_to_timeline(transcript, timeline) -> dict
```

Behavior:

- validate `timeline.json` before mapping;
- retain a word only when its midpoint is inside a retained source clip;
- map word start/end through that clip's linear speed and clamp them to the clip boundary;
- preserve the original word text and add its explicit `source_range` and `clip_id`;
- split transcript segments at clip boundaries so no segment crosses an edit join;
- set top-level `timebase` to `program`, `timeline_id` to the active timeline ID, and
  `duration` to `program_duration_s`;
- preserve source transcript metadata that is not time-dependent;
- fail on invalid or non-monotonic word timing rather than silently repairing it.

An identity timeline produces equivalent word timing. A rough-cut timeline drops removed
words, closes gaps, and divides word durations by each clip's speed.

## 5. `video-add-captions`

### 5.1 Inputs

- `work/project.json`
- `work/understand/transcript.json`
- `work/timeline.json`
- `work/understand/media.json`
- the source video for source-backed review frames
- optional selected grade revision only when caption contrast was judged against that grade

The skill does not transcribe, cut, grade, reframe, or encode delivery audio.

### 5.2 Durable Plan

`work/captions/captions-plan.json` is the domain plan:

```json
{
  "schema_version": 1,
  "target": "overlay",
  "timeline_id": "main",
  "timebase": "program",
  "source_transcript": "understand/transcript.json",
  "cue_settings": {
    "max_chars": 42,
    "max_lines": 2,
    "max_duration_s": 6.0,
    "gap_s": 0.6
  },
  "style": {
    "selection_mode": "agent",
    "selection_rationale": "Delegated conservative choice for readable talking-head captions.",
    "choice_id": "clean",
    "preset": "clean",
    "highlight_theme": null,
    "background_theme": null,
    "stroke_theme": null,
    "karaoke": false,
    "resolved": {}
  },
  "review": {
    "status": "approved",
    "evidence": ["../review/05-captions/preview-early.png"]
  },
  "cues": [],
  "renderer_recipe": {
    "engine": "hyperframes",
    "composition": "cache/captions/index.html",
    "asset": "cache/captions/overlay-frames",
    "asset_type": "image-sequence",
    "pattern": "frame_%06d.png",
    "start_number": 1,
    "fps": {"num": 30000, "den": 1001},
    "runtime_assets": []
  }
}
```

Each cue retains the compatibility fields `start`, `end`, `text`, `lines`, and `words`.
Those times are program seconds. It also has `program_range` and `source_ranges`; every word
has its own program and source range. Cue creation always breaks at a timeline clip boundary.

The plan stores the complete resolved style and local renderer asset recipe. Generated HTML,
preview snapshots, and overlay frames stay in `work/cache/` and can be regenerated from the
plan after cache deletion.

### 5.3 Review and Approval

Human mode preserves the existing exact style-selection and preview-confirmation gates.

Agent mode adds explicit commands for delegated selection and approval. The interaction
receipt records `decision_mode: agent`, the chosen gallery ID, artifact hashes, preview
evidence, and non-empty rationales. Human commands are rejected in an agent-mode receipt and
agent commands are rejected in a human-mode receipt. This makes autonomous execution honest
without weakening the hash-bound review gate.

Default agent decisions are conservative: `clean`, no Karaoke, unless the destination or
footage clearly calls for another maintained preset. Style is still reviewed on real source
pixels before full overlay rendering.

Review files:

```text
review/05-captions/
|-- captions.srt
|-- preview-early.png
|-- preview-middle.png
|-- preview-late.png
|-- preview-no-caption.png
`-- captions-summary.md
```

Preview stills composite transparent HyperFrames snapshots over source frames mapped from
the sampled program timestamp through `timeline.json`. This avoids a full intermediate proxy
and remains correct after cuts and varispeed.

### 5.4 Render Contribution

HyperFrames renders the approved transparent overlay as RGBA PNG frames at source dimensions,
the exact rational timeline FPS, and program duration. Required JavaScript and fonts are
copied locally; render-time network access is forbidden.

The operation record is:

```json
{
  "id": "captions",
  "skill": "video-add-captions",
  "revision": 1,
  "depends_on": ["understanding", "rough-cut"],
  "based_on": {"understanding": 1, "rough-cut": 1},
  "status": "verified",
  "plan": "captions/captions-plan.json",
  "outputs": ["cache/captions/overlay-frames"],
  "target": {"sequence": "main", "scope": "captions"},
  "effects": {
    "changes_timeline": false,
    "changes_geometry": false,
    "changes_video_pixels": false,
    "changes_audio": false,
    "adds_track": "captions"
  },
  "check": {
    "status": "pass",
    "report": "../review/05-captions/captions-summary.md"
  },
  "render": {
    "kind": "overlay",
    "asset": "cache/captions/overlay-frames",
    "asset_type": "image-sequence",
    "pattern": "frame_%06d.png",
    "start_number": 1,
    "fps": {"num": 30000, "den": 1001}
  }
}
```

With an identity timeline the delivery renderer copies audio. With a rough cut or varispeed,
the existing shared renderer filters and encodes audio. Caption code never makes that choice.

## 6. `video-to-shorts`

### 6.1 Input Boundary

Project mode consumes:

- `final/final-video.mp4`, after the selected main-sequence operations are rendered;
- `work/understand/transcript.json`;
- `work/timeline.json`;
- active operation revisions from `work/project.json`.

`prepare_transcript.py --timeline` writes a program-time transcript using the shared mapper.
Candidate and extraction code continues to consume a simple word-level transcript, but its
timebase is now explicit and matches the actual final video. Standalone mode keeps the
provided-transcript path and uses the canonical `video-understand` transcriber as its
temporary fallback; it no longer routes through `video-rough-cut`.

### 6.2 Candidate and Plan Contracts

Agent-authored candidate files remain `shorts-candidates.v2` compatibility inputs. The
validator fixes two semantics:

- `transcript_excerpt` is derived from overlapping words, not entire overlapping segments;
- project mode requires `timebase: program` and binds the candidate input to the selected
  final video, transcript, and timeline.

The canonical durable output is `work/shorts/shorts-plan.json` with integer
`schema_version: 1`. Each selected short contains:

- stable ID and evidence references;
- explicit `program_range` on the final input clock;
- mapped `source_ranges` for traceability;
- score breakdown, editorial reason, and candidate warnings;
- reviewed filler drops and generated keep ranges in program time;
- horizontal/vertical output paths;
- exact dependency revisions and selection mode/rationale.

Legacy standalone execution may continue emitting/accepting `shorts-plan.v2` fields. The
extractor accepts both shapes during migration.

### 6.3 Review Modes

The existing hash-bound human candidate and vertical-preview gates remain the default.
Delegated runs add an agent mode parallel to captions and color grade:

- the review is opened with `decision_mode: agent`;
- the agent inspects candidates or the rendered vertical preview;
- approval records selected IDs, delivery mode, rationale, and hashes;
- no user-response field or fake human phrase is written.

`horizontal_only` and `horizontal_and_vertical` remain explicit decisions. Agent mode may
choose either when the user delegated the workflow.

### 6.4 Output Layout

```text
work/shorts/
|-- shorts-plan.json
|-- transcript.json
|-- transcript-metadata.json
|-- candidates.json
|-- candidate-review.json
`-- short-001/
    |-- transcript.json
    |-- extraction-report.json
    `-- vertical-plan.json

work/cache/shorts/                 # frames, sheets, previews, temporary media

review/06-shorts/
|-- candidates.html
|-- candidates-summary.md
|-- short-001-horizontal.jpg
|-- short-001-vertical-preview.mp4
|-- short-001-vertical-contact-sheet.jpg
`-- shorts-summary.md

final/shorts/
|-- short-001-horizontal.mp4
`-- short-001-vertical.mp4          # only when selected and approved
```

Extraction reuses the rough-cut renderer's proven pattern: one seeked ffmpeg input per keep
range, then one concat and one encode. It does not decode the complete long source once per
short. Short-relative transcripts exclude removed words and shift later words onto the
continuous output clock.

Vertical plans preserve FPS as `{num, den}`. Crop/letterbox strategy remains Agent-authored
and deterministically validated; Python does not invent subject coordinates. Preview stays
small, final vertical media goes to `final/shorts/`, and review media goes to
`review/06-shorts/`.

### 6.5 Project Operation

The shorts operation is present in `project.json` but absent from
`sequences.main.operations`. It therefore receives DAG/revision validation without becoming
a contribution to `final/final-video.mp4`:

```json
{
  "id": "shorts",
  "skill": "video-to-shorts",
  "revision": 1,
  "depends_on": ["understanding", "captions"],
  "based_on": {"understanding": 1, "captions": 1},
  "status": "verified",
  "plan": "shorts/shorts-plan.json",
  "outputs": ["../final/shorts/short-001-horizontal.mp4"],
  "target": {"sequence": "main", "scope": "derivatives"},
  "effects": {
    "changes_timeline": true,
    "changes_geometry": true,
    "changes_video_pixels": true,
    "changes_audio": true,
    "adds_track": null
  },
  "check": {
    "status": "pass",
    "report": "../review/06-shorts/shorts-summary.md"
  }
}
```

The plan also records the main render path and refuses project-mode extraction unless that
render is verified and still matches the reviewed input artifact.

## 7. Shared Renderer Extension

`overlay` remains the contribution kind. The renderer gains one explicit asset form:

```json
{
  "kind": "overlay",
  "asset": "cache/captions/overlay-frames",
  "asset_type": "image-sequence",
  "pattern": "frame_%06d.png",
  "start_number": 1,
  "fps": {"num": 30000, "den": 1001}
}
```

The compiler requires the directory and first frame, rejects path-escaping patterns, and
requires FPS to match the active timeline. The renderer passes the rational FPS and frame
pattern to ffmpeg, then follows the existing overlay order. File-backed MOV/WebM overlays
remain unchanged for content cards and standalone compatibility.

## 8. Compatibility

- Existing caption cue arrays remain accepted by the generator.
- Existing human caption interaction commands remain valid.
- Existing standalone caption composite accepts PNG directories or video overlays.
- Existing `shorts-candidates.v2`, `shorts-plan.v2`, and `WORK/shorts/short_XX` consumers
  remain accepted when project-mode options are absent.
- Existing content-card MOV overlays and all current contribution kinds keep their behavior.
- No changes are required in rough-cut, color-grade, content-cards, or edit-compare code.

## 9. Validation and Self-Check

Small executable checks are added before implementation and retained with the skills:

1. source transcript mapping drops cut words, retimes kept words, and splits at clip joins;
2. canonical caption cues use program time and preserve source evidence;
3. agent caption review cannot be mistaken for human approval;
4. image-sequence overlays compile and render with alpha at rational FPS;
5. shorts exact excerpts use word ranges;
6. agent candidate and vertical approvals remain hash-bound;
7. canonical shorts plans use program ranges, user-facing outputs, and rational FPS;
8. extraction uses seeked inputs and produces synchronized media/transcript durations.

Repository checks include Python compilation, Node style checks, PowerShell structure checks,
HyperFrames lint/check/snapshots, `git diff --check`, and project validation.

Two real-media acceptance runs are required:

### Run 20

`video-understand -> video-rough-cut -> video-add-captions -> shared delivery -> video-edit-compare`

Required evidence: validated project/timeline/understanding, a materially shorter final,
caption timing at early/middle/late kept moments, no captions for dropped speech, synchronized
audio, source-time comparison with black dropped ranges, and user-facing summaries.

### Run 21

`video-understand -> video-add-captions -> shared delivery -> video-to-shorts -> video-edit-compare`

Required evidence: identity timeline, captioned main final, at least one approved complete
short, horizontal and agent-approved vertical output, short-relative transcript, contact
sheets, synchronized audio, and final-pixel comparison of the unchanged main duration.

All generated files stay below their respective `TEST/20-codex-sol` or
`TEST/21-codex-sol` directories. No unrelated test directory content is inspected.

## 10. Non-Goals

- A second project manifest or workflow scheduler.
- Dynamic subject tracking for vertical crops.
- Automatic semantic candidate generation by deterministic scripts.
- Reordering or duplicating source clips.
- Making shorts part of the main delivery comparison.
- Refactoring mature skills that do not block these contracts.
