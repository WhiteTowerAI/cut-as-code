# Video Add B-Roll Design

**Date:** 2026-07-23

**Status:** Approved for implementation

**Skill:** `video-add-b-roll`
**Operation:** `b-roll`

## Summary

Add selective B-roll to a Project Protocol V1 sequence using local assets and Pexels. An
Agent proposes editorial moments and concrete search queries, a human or explicitly
delegated Agent approves exact assets, deterministic scripts freeze and normalize those
assets, and the shared delivery renderer composites them as ordinary video overlays.

V1 deliberately avoids a generic provider layer, native paid generation APIs, automatic
coverage quotas, and unrelated fallback media. The smallest complete architecture is one
direct Pexels module plus local import, a durable JSON plan, a local review page, a
normalizer, and a verifier.

## Decisions

| Decision | Considered options | V1 choice | Reason |
| --- | --- | --- | --- |
| Material sources | local; local + Pexels; multiple stock providers + generation | local + Pexels | Covers owned footage and one useful stock source without a broker. |
| Generative media | unsupported; external import; native API | external import | Preserves provenance while avoiding paid-provider credentials and policy surface. |
| Default density | selective; target coverage; full coverage | selective | B-roll must earn its place; missing material is better than irrelevant material. |
| Review authority | mandatory human; human/Agent; autonomous by default | human/Agent | Matches Project Protocol V1 receipts without fabricating human approval. |
| Still images | forbidden; explicit Ken Burns; automatic fallback | explicit Ken Burns | Intentional stills are useful, but an image must never silently replace a failed video search. |
| Provider architecture | direct Pexels file; generic interface; broker | direct Pexels file | One implementation does not justify an interface. Extract only when a second provider ships. |

The approved baseline is Agent editorial judgment plus thin deterministic tools, local and
Pexels sources, selective density, dual human/Agent review, and externally generated media
as an import rather than a native paid generation call.

## Goals

- Identify a small number of semantically useful B-roll moments from the verified
  understanding, program-time transcript, and active timeline.
- Preserve the source transcript evidence behind every proposed moment.
- Search and freeze local or Pexels candidates with complete provenance and hashes.
- Bind the exact reviewed candidates and selected assets to a durable receipt.
- Normalize selected clips to the sequence dimensions, rational FPS, duration, and silent
  video contract.
- Pre-apply the active selected color grade to B-roll so it visually matches the graded
  base video.
- Compile approved shots into existing `overlay` contributions and render delivery once.
- Resume individual failed downloads or normalizations without repeating completed shots.

## Non-Goals

- A multi-provider stock broker or provider plug-in API.
- Native calls to paid image or video generation APIs.
- Automatic full-program coverage or a minimum B-roll quota.
- Reordered, duplicated, or nonlinear timeline clips beyond Protocol V1.
- B-roll audio, ducking, transitions, picture-in-picture, or animated masks.
- Random, merely topical, or visually unrelated fallback assets.
- Automatic conversion of failed video candidates into still-image motion.

## Project Protocol Contract

### Dependencies and order

The operation always depends on `understanding`. It also depends on active upstream `cut`
and `color-grade` operations. `depends_on` and `based_on` must name the same active inputs
and exact integer revisions.

The main sequence order is:

```text
cut -> color-grade -> b-roll -> content-cards -> captions
```

`b-roll` changes video pixels and adds a `b-roll` track, but does not change timeline,
geometry, or audio:

```json
{
  "target": {"sequence": "main", "scope": "b-roll"},
  "effects": {
    "changes_timeline": false,
    "changes_geometry": false,
    "changes_video_pixels": true,
    "changes_audio": false,
    "adds_track": "b-roll"
  }
}
```

Each verified shot becomes an existing video overlay contribution:

```json
{
  "kind": "overlay",
  "asset": "cache/b-roll/normalized/broll-001.mp4",
  "start_s": 12.4,
  "duration_s": 4.2
}
```

No new contribution kind is needed. `render_project.py` already applies base-video color
filters before overlays and composites overlay contributions in active sequence order.
Consequently the normalizer pre-applies the selected grade to B-roll whenever an active
`color-grade` operation exists.

### No-op behavior

If no shot is selected, write a review summary explaining the no-op but do not add an
active empty `b-roll` operation to `sequences.main.operations`. Missing or rejected
candidates become `skipped`; they never trigger unrelated fallback media.

### Staleness

The plan records `dependencies` and `based_on`, its `timeline_id`, program duration,
transcript hash, timeline hash, and selected grade-plan/LUT hashes when applicable. A
changed transcript, timeline, dependency revision, grade choice, reviewed candidate
manifest, or selected asset invalidates normalization and verification.

## Durable Files

```text
work/b-roll/broll-plan.json
work/b-roll/broll-interaction.json
work/cache/b-roll/candidates/
work/cache/b-roll/normalized/
review/03-b-roll/b-roll-review-<UUID>.html
review/03-b-roll/b-roll-review.html
review/03-b-roll/b-roll-summary.md
review/03-b-roll/stills/
review/03-b-roll/contact-sheet.jpg
review/03-b-roll/boundary-reel.mp4
```

The UUID-named review file is immutable evidence. `b-roll-review.html` is a convenience
copy pointing at the latest review state. Review HTML and media are local; it performs no
network requests.

## Plan Schema

`work/b-roll/broll-plan.json` is the domain source of truth:

```json
{
  "schema_version": 1,
  "timeline_id": "main",
  "timebase": "program",
  "program_duration_s": 176.2,
  "dependencies": ["understanding", "cut", "color-grade"],
  "based_on": {"understanding": 1, "cut": 2, "color-grade": 1},
  "input_hashes": {
    "transcript_sha256": "...",
    "timeline_sha256": "...",
    "grade_plan_sha256": "...",
    "selected_lut_sha256": "..."
  },
  "brief": {
    "density": "selective",
    "style": "literal documentary footage",
    "avoid": ["logos", "screens with unreadable text", "unrelated rockets"]
  },
  "decision": {
    "mode": "agent",
    "actor": "Codex",
    "rationale": "Selected literal product and manufacturing visuals for abstract claims."
  },
  "review": {
    "status": "approved",
    "review_id": "...",
    "page": "../review/03-b-roll/b-roll-review-<UUID>.html",
    "plan_sha256": "...",
    "candidate_manifest_sha256": "...",
    "selected_asset_sha256": ["..."]
  },
  "shots": []
}
```

Every shot has a stable ID and these concepts:

- half-open `program_range` and mapped `source_ranges`;
- transcript evidence with exact words and source/program ranges;
- editorial reason, visual intent, and two or three concrete search queries;
- candidate records and one explicit selection;
- provider or local provenance, immutable SHA-256, source trim, normalized output, and
  verification result;
- lifecycle `planned`, `candidates_ready`, `selected`, `normalized`, `verified`, or
  `skipped`.

V1 rejects overlapping B-roll program ranges. Program ranges must be in timeline bounds,
have positive duration, and map to preserved source evidence. Selected assets must belong
to that shot's frozen candidate manifest.

## Editorial Rules

- Prefer literal nouns, actions, locations, products, and processes over generic mood
  footage.
- Use B-roll where it clarifies a claim, hides an unavoidable edit, or provides concrete
  evidence. Do not cover a face merely because stock exists.
- Write two or three narrow English queries per moment. Include subject, action, setting,
  and useful framing; avoid full transcript sentences and abstract adjectives.
- Keep the first and last spoken beat visible when the speaker's expression carries the
  meaning.
- Do not repeat a provider asset or near-identical visual within one sequence.
- Skip a moment when no candidate matches the meaning, quality, license, duration, and
  framing requirements.
- A still image is eligible only when the decision explicitly selects `ken-burns` motion
  and states the crop direction; it is never an automatic fallback.

## Candidate Acquisition and Provenance

### Local assets

Local candidates are imported into the project cache, never referenced by a mutable
external path. The import records original path, media type, byte length, retrieval time,
SHA-256, and user-supplied source/license notes. Externally generated assets use this path
and add generation provider/model, prompt or job reference when available, creator, and
usage rights. V1 does not call generation APIs.

### Pexels

`PEXELS_API_KEY` is read from the environment only and never written to plans, URLs, logs,
or review HTML. Search results record provider ID, creator, Pexels page URL, original media
URL, dimensions, duration, Pexels license/terms URLs, retrieval timestamp, and selected
download variant.

Network and file handling are trust boundaries:

- require HTTPS and expected Pexels hosts for API, page, and media URLs;
- retain TLS certificate verification;
- use finite connect/read timeouts and bounded retries for transient failures;
- limit redirects, declared size, streamed byte count, and accepted response size;
- download to a `.part` file inside `work/cache/b-roll/candidates/`;
- distrust extension and `Content-Type`; run `ffprobe` and decode a frame;
- atomically rename only after media validation and SHA-256 calculation;
- constrain all output paths to the project cache;
- resume per shot and never overwrite a different hash silently.

## Review Receipt

The local review page shows each proposed moment, transcript evidence, source frame,
candidate previews, provenance, query, and select/skip controls. Its export includes every
shot exactly once.

Human review is valid only after an explicit user action. Agent review is valid only when
the user delegated the decision or requested autonomous completion. Both modes require a
non-empty rationale and bind:

- review UUID;
- pre-decision plan hash;
- frozen candidate manifest hash;
- selected asset hashes;
- actor, mode, timestamp, and selected/skip decisions.

Never label an Agent decision as human and never synthesize a fake user response.

## Normalization

Each selected video is converted to a silent H.264 MP4 with the source dimensions,
sequence rational FPS, square pixels, `yuv420p`, exact program duration, and no audio. The
source trim is explicit and must fit within the probed candidate duration. Scale and crop
preserve aspect ratio without stretching.

An explicitly selected still is converted to the same video contract with one deterministic
Ken Burns crop/zoom. The plan stores its motion direction and crop parameters.

When color grade is active, normalization applies the exact selected LUT or canonical grade
chain. Windows LUT paths follow the repository rule: run ffmpeg with the LUT directory as
`cwd` and pass the basename to `lut3d`.

## Verification

The verifier fails unless every selected shot satisfies all of the following:

- dependency revisions and all recorded hashes are current;
- ranges are half-open, ordered, non-overlapping, within the program, and evidenced;
- selected asset is in the frozen candidate manifest with complete provenance;
- source trim is valid and the normalized file hash matches the plan;
- normalized dimensions and rational FPS equal the timeline;
- duration covers the declared overlay range within one frame;
- the normalized file has video, no audio, and decodes first/middle/last frames;
- active grade evidence matches the pre-applied grade;
- review receipt binds the exact plan, manifest, and selected hashes.

Verification produces first/middle/last stills per selected shot, a contact sheet, a short
boundary reel, and `review/03-b-roll/b-roll-summary.md`. The reviewer checks semantic fit,
readability, unwanted logos/text, visible jump cuts, start/end boundaries, and visual match
to the main program. Only then may operation lifecycle become `verified` and
`check.status` become `pass`.

## Implementation Shape

```text
skills/video-add-b-roll/
|-- SKILL.md
|-- assets/broll-review.html
|-- examples/example-broll-plan.json
|-- reference/broll-rules.md
|-- scripts/broll_plan.py
|-- scripts/pexels.py
|-- scripts/build_review_page.py
|-- scripts/normalize_broll.py
|-- scripts/check_broll.py
`-- tests/test_broll.py
```

The scripts import `skills/video-understand/scripts/projectlib.py` directly. There is no
package, provider base class, factory, database, or new dependency. Python standard library,
ffmpeg/ffprobe, and Pillow already used in the repository are sufficient.

The shared runtime receives only focused validation for approved B-roll plans and their
declared overlay contributions. The existing renderer remains unchanged unless a failing
regression proves an actual incompatibility.

## Open-Source Research

Stars were checked through the GitHub API on 2026-07-22. Repository clones and evidence are
kept in ignored `work/cache/`; they are research inputs, not vendored dependencies.

| Repository | Stars | License | Relevant lesson |
| --- | ---: | --- | --- |
| `harry0703/MoneyPrinterTurbo` | 98,565 | MIT | Material search parsing, dedupe, cache, and download validation. |
| `OpenCut-app/OpenCut` | 77,266 | MIT | Default branch is a rewrite skeleton; no reusable B-roll implementation. |
| `calesthio/OpenMontage` | 41,020 | AGPL-3.0 | Design reference only because copyleft is incompatible with copying here. |
| `FujiwaraChoki/MoneyPrinter` | 13,775 | MIT | Simple stock-video acquisition and assembly patterns. |
| `waooAI/waoowaoo` | 13,316 | no explicit license | Design observation only; no code may be copied. |
| `RayVentura/ShortGPT` | 7,716 | MIT | Direct Pexels search and concrete query-writing rules. |
| `nexu-io/html-video` | 4,129 | Apache-2.0 | Content-addressed asset registration; retain SHA-256 in this protocol. |
| `SamurAIGPT/Generative-Media-Skills` | 3,883 | MIT | External generated-media workflow and provenance concepts. |
| `ArcReel/ArcReel` | 3,542 | AGPL-3.0 | Agent project design reference only; no code reuse. |
| `rushindrasinha/youtube-shorts-pipeline` | 2,127 | MIT | Niche/avoid constraints and explicit still-to-motion handling. |
| `digitalsamba/claude-code-video-toolkit` | 1,793 | MIT | Agent-facing video utility organization. |
| `HITsz-TMG/VideoClaw` | 1,630 | MIT | Structured media-agent workflow ideas. |
| `Hao0321/video-autopilot-kit` | 1,490 | MIT | Caption/B-roll matching and duplicate/aspect audits. |
| `Agents365-ai/video-podcast-maker` | 1,477 | CC BY-NC 4.0 | Design-only provider notes; noncommercial license prevents code reuse. |
| `gyoridavid/short-video-maker` | 1,241 | MIT | Retry, timeout, authorization failure, orientation, duration, and excluded-ID handling. |
| `pyang5166/gbro-collage-broll` | 623 | MIT | Job-level recovery and decoded-frame QA. |

Concrete files informing the design are:

- MoneyPrinterTurbo `app/services/material.py` for parsing, dedupe, caching, and validation;
- ShortGPT `shortGPT/api_utils/pexels_api.py` and `editing_generate_videos.yaml` for direct
  Pexels access and query specificity;
- short-video-maker `src/short-creator/libraries/Pexels.ts` for timeout, retry, 401,
  orientation, duration, and excluded-ID behavior;
- video-autopilot-kit `caption_broll_matcher.py` and `broll_audit.py` for matching and
  duplicate/aspect checks;
- youtube-shorts-pipeline `verticals/broll.py` for niche/avoid constraints and explicit
  still-to-motion choices;
- gbro-collage-broll `scripts/generate_video.py` for recovery and frame QA;
- html-video `packages/core/src/asset-store.ts` for content-addressed registration.

No third-party source is copied by this design. If MIT or Apache-2.0 code is later ported,
retain its copyright and license notice. AGPL, CC BY-NC, and unlicensed repositories remain
design-only references.

## Acceptance

Implementation is accepted when focused tests prove plan/range/receipt/provenance validation,
safe download behavior, normalization, staleness, no-op handling, and compiler output; all
existing protocol/render checks still pass; and the supplied `TEST/28-sol/Musk_3min.mp4`
project produces a reviewed, verified final delivery with all artifacts contained under
`TEST/28-sol/`.
